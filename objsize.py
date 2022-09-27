"""
Traversal over Python's objects subtree and calculating
the total size of the subtree (deep size).

Author: Liran Funaro <liran.funaro@gmail.com>

Copyright (c) 2006-2022, Liran Funaro.
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
from typing import Any, Iterable, Optional, Set

__version__ = "0.6.0"

# Common type: a set of objects' ID
MarkedSet = Set[int]

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


def safe_is_instance(o: Any, type_tuple) -> bool:
    """
    Return whether an object is an instance of a class or of a subclass thereof.
    See `isinstance()` for more information.

    Catches `ReferenceError` because applying `isinstance()` on `weakref.proxy`
    objects attempts to dereference the proxy objects, which may yield an exception.
    """
    try:
        return isinstance(o, type_tuple)
    except ReferenceError:
        return False


def shared_object_or_function_filter(o: Any) -> bool:
    """Filters objects that are likely to be shared among many objects."""
    return not safe_is_instance(o, SharedObjectOrFunctionType)


def shared_object_filter(o: Any) -> bool:
    """Filters objects that are likely to be shared among many objects, but includes functions and lambdas."""
    return not safe_is_instance(o, SharedObjectType)


# See https://docs.python.org/3/library/gc.html#gc.get_referents
default_get_referents = gc.get_referents
# See https://docs.python.org/3/library/sys.html#sys.getsizeof
default_get_size = sys.getsizeof
# By default, we filter shared objects, i.e., types, modules, functions, and lambdas
default_object_filter = shared_object_or_function_filter


def get_exclude_set(
    exclude: Optional[Iterable] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
) -> Optional[set]:
    if exclude_set is None:
        exclude_set = set()
    if exclude is None:
        return exclude_set
    it = traverse_bfs(
        *exclude,
        marked_set=exclude_set,
        exclude_set=exclude_set,
        get_referents_func=get_referents_func,
        filter_func=filter_func,
    )
    collections.deque(it, maxlen=0)
    return exclude_set


def traverse_bfs(
    *objs,
    exclude: Optional[Iterable] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
) -> Iterable[Any]:
    """
    Traverse all the arguments' subtree.
    By default, this excludes shared objects, i.e., types, modules, functions, and lambdas.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        Objects that will be excluded from this calculation, as well as their subtrees.
    marked_set : set, optional
        An existing set of marked objects' ID, i.e., `id(obj)`.
        Objects that their ID is in this set will not be traversed.
        If a set is given, it will be updated with all the traversed objects' ID.
    exclude_set : set, optional
        Similar to the marked set, but contains excluded objects' ID.
    get_referents_func : callable
        Receives any number of objects and returns iterable over the objects that are referred by these objects.
        Default: `gc.get_referents()`.
        See: https://docs.python.org/3/library/gc.html#gc.get_referents
    filter_func : callable
        Receives an objects and return `True` if the object---and its subtree---should be traversed.
        Default: `objsize.shared_object_filter`.

    Yields
    ------
    object
        The traversed objects, one by one.
    """
    if marked_set is None:
        marked_set = set()
    if exclude_set is None:
        exclude_set = set()

    # None shouldn't be included in size calculations because it is a singleton
    exclude_set.add(id(None))
    # Modules' "globals" should not be included as they are shared
    exclude_set.update(id(vars(m)) for m in list(sys.modules.values()))

    exclude_set = get_exclude_set(
        exclude,
        exclude_set=exclude_set,
        get_referents_func=get_referents_func,
        filter_func=filter_func,
    )

    while objs:
        # Get the object's ids
        objs = ((id(o), o) for o in objs)

        # Filter:
        #  - Object that are already marked/excluded (using the marked-set/exclude-set).
        #  - Objects that are filtered by the given filter function (see above).
        #  - Repeated objects (using dict notation).
        objs = {
            o_id: o
            for o_id, o in objs
            if o_id not in marked_set and o_id not in exclude_set and filter_func(o)
        }

        # We stop when there are no new valid objects to traverse.
        if not objs:
            break

        # Update the marked set with the ids, so we will not traverse them again.
        marked_set.update(objs.keys())

        # Yield traversed objects
        yield from objs.values()

        # Lookup all the object referred to by the object from the current round.
        objs = get_referents_func(*objs.values())


def traverse_exclusive_bfs(
    *objs,
    exclude: Optional[Iterable] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
) -> Iterable[Any]:
    """
    Traverse all the arguments' subtree, excluding non-exclusive objects.
    That is, objects that are referenced by objects that are not in this subtree.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `traverse_bfs()`.
    marked_set : set, optional
        See `traverse_bfs()`.
    exclude_set : set, optional
        See `traverse_bfs()`.
    get_referents_func : callable
        See `traverse_bfs()`.
    filter_func : callable
        See `traverse_bfs()`.

    Yields
    ------
    object
        The traversed objects, one by one.

    See Also
    --------
    traverse_bfs : to understand which objects are traversed.
    """
    if marked_set is None:
        marked_set = set()
    if exclude_set is None:
        exclude_set = set()

    # The arguments are considered the root objects, which we include
    # regardless of their exclusiveness.
    root_obj_ids = set(map(id, objs))

    # We have to complete the entire traverse, so we will have
    # a complete marked set.
    subtree = tuple(
        traverse_bfs(
            *objs,
            exclude=exclude,
            marked_set=marked_set,
            exclude_set=exclude_set,
            get_referents_func=get_referents_func,
            filter_func=filter_func,
        )
    )

    # We keep the current frame and `subtree` objects in addition to the marked-set because they refer to objects
    # in our subtree which may cause them to appear non-exclusive.
    # `objs` should not be added as it only refers to the root objects.
    frame_set = marked_set | {id(inspect.currentframe()), id(subtree)}

    # We first make sure that any "old" objects that may refer to our subtree were collected.
    gc.collect()

    # Test for each object that all the object that refer to it is in the marked-set, frame-set, or is a root
    # See: https://docs.python.org/3.7/library/gc.html#gc.get_referrers
    for o in subtree:
        if id(o) in root_obj_ids or frame_set.issuperset(map(id, gc.get_referrers(o))):
            yield o


def get_deep_size(
    *objs,
    exclude: Optional[Iterable] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_size_func=default_get_size,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
) -> int:
    """
    Calculates the deep size of all the arguments.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        Objects that will be excluded from this calculation, as well as their subtrees.
    marked_set : set, optional
        See `traverse_bfs()`.
    exclude_set : set, optional
        See `traverse_bfs()`.
    get_size_func : function, optional
        A function that determines the object size.
        Default: `sys.getsizeof()`
    get_referents_func : callable
        See `traverse_bfs()`.
    filter_func : callable
        See `traverse_bfs()`.

    Returns
    -------
    int
        The objects' deep size in bytes.

    See Also
    --------
    traverse_bfs : to understand which objects are traversed.
    """
    it = traverse_bfs(
        *objs,
        exclude=exclude,
        marked_set=marked_set,
        exclude_set=exclude_set,
        get_referents_func=get_referents_func,
        filter_func=filter_func,
    )
    return sum(map(get_size_func, it))


def get_exclusive_deep_size(
    *objs,
    exclude: Optional[Iterable] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_size_func=default_get_size,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
) -> int:
    """
    Calculates the deep size of all the arguments, excluding non-exclusive objects.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `get_deep_size()`.
    marked_set : set, optional
        See `traverse_bfs()`.
    exclude_set : set, optional
        See `traverse_bfs()`.
    get_size_func : function, optional
        See `get_deep_size()`.
    get_referents_func : callable
        See `traverse_bfs()`.
    filter_func : callable
        See `traverse_bfs()`.

    Returns
    -------
    int
        The objects' deep size in bytes.

    See Also
    --------
    traverse_exclusive_bfs : to understand which objects are traversed.
    """
    it = traverse_exclusive_bfs(
        *objs,
        exclude=exclude,
        marked_set=marked_set,
        exclude_set=exclude_set,
        get_referents_func=get_referents_func,
        filter_func=filter_func,
    )
    return sum(map(get_size_func, it))
