"""
Author: Liran Funaro <liran.funaro@gmail.com>

Copyright (c) 2006-2023, Liran Funaro.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
import collections
import gc
import inspect
import sys
import types
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, Optional, Set, Tuple

# Common type: a set of objects' ID
MarkedSet = Set[int]
FilterFunc = Callable[[Any], bool]
GetReferentsFunc = Callable[..., Iterable[Any]]

SharedObjectType = (
    type,
    types.ModuleType,
    types.FrameType,
    types.BuiltinFunctionType,
)

SharedObjectOrFunctionType = (
    *SharedObjectType,
    types.FunctionType,
    types.LambdaType,
)


def safe_is_instance(obj: Any, type_tuple) -> bool:
    """
    Return whether an object is an instance of a class or of a subclass thereof.
    See `isinstance()` for more information.

    Catches `ReferenceError` because applying `isinstance()` on `weakref.proxy`
    objects attempts to dereference the proxy objects, which may yield an exception.
    """
    try:
        return isinstance(obj, type_tuple)
    except ReferenceError:
        return False


def shared_object_or_function_filter(obj: Any) -> bool:
    """Filters objects that are likely to be shared among many objects."""
    return not safe_is_instance(obj, SharedObjectOrFunctionType)


def shared_object_filter(obj: Any) -> bool:
    """Filters objects that are likely to be shared among many objects, but includes functions and lambdas."""
    return not safe_is_instance(obj, SharedObjectType)


# See https://docs.python.org/3/library/gc.html#gc.get_referents
default_get_referents = gc.get_referents
# By default, we filter shared objects, i.e., types, modules, functions, and lambdas
default_object_filter = shared_object_or_function_filter


def _iter_modules_globals():
    modules = list(sys.modules.values())
    for mod in modules:
        try:
            yield vars(mod)
        except TypeError:
            pass


@dataclass(frozen=True)
class TraversalSettings:
    """
    Object traversal settings.

    Attributes
    ----------
    filter_func : callable
        Receives an objects and return `True` if the object---and its subtree---should be traversed.
        Default: `objsize.shared_object_filter`.
        By default, this excludes shared objects, i.e., types, modules, functions, and lambdas.
    get_referents_func : callable
        Receives any number of objects and returns iterable over the objects that are referred by these objects.
        Default: `gc.get_referents()`.
        See: https://docs.python.org/3/library/gc.html#gc.get_referents
    exclude : iterable, optional
        Objects that will be excluded from this calculation, as well as their subtrees.
    exclude_modules_globals : bool
        If True (default), loaded modules globals will be added to the `exclude_set`.
    """

    get_referents_func: GetReferentsFunc = default_get_referents
    filter_func: FilterFunc = default_object_filter
    exclude: Optional[Iterable] = None
    exclude_modules_globals: bool = True

    def new_context(self, *, marked_set: Optional[MarkedSet] = None, exclude_set: Optional[MarkedSet] = None):
        """See `TraversalContext`"""
        return TraversalContext(self, marked_set, exclude_set)

    def traverse_bfs(
        self, objs: Iterable[Any], *, marked_set: Optional[MarkedSet] = None, exclude_set: Optional[MarkedSet] = None
    ) -> Iterator[Any]:
        """See `TraversalContext.traverse_bfs()`"""
        yield from self.new_context(marked_set=marked_set, exclude_set=exclude_set).traverse_bfs(objs)

    def traverse_exclusive_bfs(
        self, objs: Iterable[Any], *, marked_set: Optional[MarkedSet] = None, exclude_set: Optional[MarkedSet] = None
    ) -> Iterator[Any]:
        """See `TraversalContext.traverse_exclusive_bfs()`"""
        yield from self.new_context(marked_set=marked_set, exclude_set=exclude_set).traverse_exclusive_bfs(objs)


class TraversalContext:
    """
    Object traversal context.

    Attributes
    ----------
    settings : ObjectIterSettings, optional
        See `ObjectIterSettings`
    marked_set : set, optional
        An existing set of marked objects' ID, i.e., `id(obj)`.
        Objects that their ID is in this set will not be traversed.
        If a set is given, it will be updated with all the traversed objects' ID.
    exclude_set : set, optional
        Similar to the marked set, but contains excluded objects' ID.
    """

    def __init__(
        self,
        settings: Optional[TraversalSettings] = None,
        marked_set: Optional[MarkedSet] = None,
        exclude_set: Optional[MarkedSet] = None,
    ):
        self.settings = settings if settings is not None else TraversalSettings()
        self.marked_set = marked_set if marked_set is not None else set()
        self.exclude_set = exclude_set if exclude_set is not None else set()
        self._update_exclude_set()

    def _update_exclude_set(self):
        """
        Traverse all the excluded subtree without ingesting the result, just to update the `exclude_set`.
        See `traverse_bfs()` for more information.
        """
        # None shouldn't be included in size calculations because it is a singleton
        self.exclude_set.add(id(None))

        if self.settings.exclude_modules_globals:
            # Modules' "globals" should not be included as they are shared
            self.exclude_set.update(map(id, _iter_modules_globals()))

        if self.settings.exclude is not None:
            collections.deque(self.traverse_bfs(self.settings.exclude, exclude=True), maxlen=0)

    def obj_filter_iterator(self, obj_it: Iterable[Any]) -> Iterator[Tuple[int, Any]]:
        """
        Filters the input. Only yields objects such that:
         - Object ID was not already marked/excluded (using the marked-set/exclude-set).
         - Object pass the given filter function (see above).

        Parameters
        ----------
        obj_it: iterable

        Yields
        -------
        A tuple (obj-id, obj) which is a subset of the input.
        """
        for obj in obj_it:
            obj_id = id(obj)
            if obj_id not in self.marked_set and obj_id not in self.exclude_set and self.settings.filter_func(obj):
                yield obj_id, obj

    def filter(self, obj_it: Iterable[Any]) -> Dict[int, Any]:
        """Apply filter, and screen repeated objects (using dict notation)."""
        return dict(self.obj_filter_iterator(obj_it))

    def traverse_bfs(self, objs: Iterable[Any], exclude=False) -> Iterator[Any]:
        """
        Traverse all the arguments' subtree.

        Parameters
        ----------
        objs : object(s)
            One or more object(s).
        exclude: bool
            If true, all objects will be added to the exclude set.

        Yields
        ------
        object
            The traversed objects, one by one.
        """
        if not exclude:
            marked_set = self.marked_set
        else:
            marked_set = self.exclude_set

        while objs:
            # Apply filter, and screen repeated objects.
            objs_map = self.filter(objs)

            # We stop when there are no new valid objects to traverse.
            if not objs_map:
                break

            # Update the marked set with the ids, so we will not traverse them again.
            marked_set.update(objs_map.keys())

            # Yield traversed objects
            yield from objs_map.values()

            # Lookup all the object referred to by the object from the current round.
            objs = self.settings.get_referents_func(*objs_map.values())

    def traverse_exclusive_bfs(self, objs: Iterable[Any]) -> Iterator[Any]:
        """
        Traverse all the arguments' subtree, excluding non-exclusive objects.
        That is, objects that are referenced by objects that are not in this subtree.

        Parameters
        ----------
        objs : object(s)
            One or more object(s).

        Yields
        ------
        object
            The traversed objects, one by one.

        See Also
        --------
        traverse_bfs : to understand which objects are traversed.
        """
        # The arguments are considered the root objects, which we include regardless of their exclusiveness.
        root_obj_ids = set(map(id, objs))

        # We have to complete the entire traverse, so we will have a complete marked set.
        subtree = tuple(self.traverse_bfs(objs))

        # We keep the current frame and `subtree` objects in addition to the marked-set because they refer to objects
        # in our subtree which may cause them to appear non-exclusive.
        # `objs` should not be added as it only refers to the root objects.
        frame_set = self.marked_set | {id(inspect.currentframe()), id(subtree)}

        # We first make sure that any "old" objects that may refer to our subtree were collected.
        gc.collect()

        # Test for each object that all the object that refer to it is in the marked-set, frame-set, or is a root
        # See: https://docs.python.org/3.7/library/gc.html#gc.get_referrers
        for obj in subtree:
            if id(obj) in root_obj_ids or frame_set.issuperset(map(id, gc.get_referrers(obj))):
                yield obj
