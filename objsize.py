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
from typing import Any, Iterable, Optional, Set

__version__ = "0.5.2"


def default_object_filter(o: Any) -> bool:
    return not isinstance(o, type)


def traverse_bfs(
    *objs,
    marked: Optional[Set[int]] = None,
    get_referents_func=gc.get_referents,
    filter_func=default_object_filter
) -> Iterable[Any]:
    """
    Traverse all the arguments' subtree.
    By default, this excludes `type` objects, i.e., where `isinstance(o, type)` is True.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    marked : set, optional
        An existing set of marked objects.
        Objects that are in this set will not be traversed.
        If a set is given, it will be updated with all the traversed objects.
    get_referents_func : callable
        Receives any number of objects and returns iterable over the objects that are referred by these objects.
        Default: `gc.get_referents()`.
        See: https://docs.python.org/3/library/gc.html#gc.get_referents
    filter_func : callable
        Receives an objects and return `True` if the object---and its subtree---should be traversed.
        Default: `lambda o: not isinstance(o, type)`.

    Yields
    ------
    object
        The traversed objects, one by one.
    """
    if marked is None:
        marked = set()

    # None shouldn't be included in size calculations because it's a singleton
    marked.add(id(None))

    while objs:
        # Get the object's ids
        objs = ((id(o), o) for o in objs)

        # Filter:
        #  - Object that are already marked (using the marked set).
        #  - Type objects such as a class or a module as they are common among all objects.
        #  - Repeated objects (using dict notation).
        objs = {o_id: o for o_id, o in objs if o_id not in marked and filter_func(o)}

        # We stop when there are no new valid objects to traverse.
        if not objs:
            break

        # Update the marked set with the ids, so we will not traverse them again.
        marked.update(objs.keys())

        # Yield traversed objects
        yield from objs.values()

        # Lookup all the object referred to by the object from the current round.
        objs = get_referents_func(*objs.values())


def traverse_exclusive_bfs(
    *objs,
    marked: Optional[Set[int]] = None,
    get_referents_func=gc.get_referents,
    filter_func=default_object_filter
) -> Iterable[Any]:
    """
    Traverse all the arguments' subtree, excluding non-exclusive objects.
    That is, objects that are referenced by objects that are not in this subtree.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    marked : set, optional
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
    if marked is None:
        marked = set()

    # The arguments are considered the root objects, which we include
    # regardless of their exclusiveness.
    root_obj_ids = set(map(id, objs))

    # We have to complete the entire traverse, so we will have
    # a complete marked set.
    subtree = tuple(
        traverse_bfs(
            *objs,
            marked=marked,
            get_referents_func=get_referents_func,
            filter_func=filter_func
        )
    )

    # We add the current frame and `subtree` objects to the marked set.
    # They refer to objects in our subtree which may cause them to
    # appear non-exclusive.
    # `objs` should not be added as it only refers to the root objects.
    roots = {id(inspect.currentframe()), id(subtree)}
    marked.update(roots)

    # Return true if a given object is in our root objects or was marked.
    # We add the predicate frame to the marked set, as it refers to the input object.
    def predicate(o):
        if id(o) in root_obj_ids:
            return True

        cur_frame_id = id(inspect.currentframe())
        roots.add(cur_frame_id)
        marked.add(cur_frame_id)
        return marked.issuperset(map(id, gc.get_referrers(o)))

    # We first make sure that any "old" objects that may refer to our subtree were collected.
    gc.collect()

    # Test for each object that all the object that refer to it is in the marked set or is a root
    # See: https://docs.python.org/3.7/library/gc.html#gc.get_referrers
    yield from filter(predicate, subtree)

    # Remove the "frame" objects from the marked set,
    # so that inner structures will not reflect to the user.
    marked.difference_update(roots)


def __get_exclude_marked_set(exclude: Optional[Iterable] = None):
    if exclude is None:
        return None

    marked = set()
    it = traverse_bfs(*exclude, marked=marked)
    collections.deque(it, maxlen=0)
    return marked


def get_deep_size(
    *objs,
    exclude: Optional[Iterable] = None,
    get_size_func=sys.getsizeof,
    get_referents_func=gc.get_referents,
    filter_func=default_object_filter
) -> int:
    """
    Calculates the deep size of all the arguments.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        Iterable of objects to exclude from this size calculation.
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
    marked = __get_exclude_marked_set(exclude)
    it = traverse_bfs(
        *objs,
        marked=marked,
        get_referents_func=get_referents_func,
        filter_func=filter_func
    )
    return sum(map(get_size_func, it))


def get_exclusive_deep_size(
    *objs,
    exclude: Optional[Iterable] = None,
    get_size_func=sys.getsizeof,
    get_referents_func=gc.get_referents,
    filter_func=default_object_filter
) -> int:
    """
    Calculates the deep size of all the arguments, excluding non-exclusive objects.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `get_deep_size()`.
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
    marked = __get_exclude_marked_set(exclude)
    it = traverse_exclusive_bfs(
        *objs,
        marked=marked,
        get_referents_func=get_referents_func,
        filter_func=filter_func
    )
    return sum(map(get_size_func, it))
