"""
Traversal over Python's objects subtree and calculating
the total size of the subtree (deep size).

Author: Liran Funaro <liran.funaro@gmail.com>

Copyright (C) 2006-2018 Liran Funaro

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import gc
import inspect
import sys
from typing import Optional, Iterable, Any, Set


def traverse_bfs(*objs, marked: Optional[Set[int]] = None) -> Iterable[Any]:
    """
    Traverse all the arguments' subtree.
    This excludes `type` objects, i.e., where `isinstance(o, type)` is True.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    marked : set, optional
        An existing set of marked objects.
        Objects that are in this set will not be traversed.
        If a set is given, it will be updated with all the traversed objects.

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
        objs = {o_id: o for o_id, o in objs if o_id not in marked and not isinstance(o, type)}

        # Update the marked set with the ids, so we will not traverse them again.
        marked.update(objs.keys())

        # Yield traversed objects
        yield from objs.values()

        # Lookup all the object referred to by the object from the current round.
        # See: https://docs.python.org/3.7/library/gc.html#gc.get_referents
        objs = gc.get_referents(*objs.values())


def traverse_exclusive_bfs(*objs, marked: Optional[Set[int]] = None) -> Iterable[Any]:
    """
    Traverse all the arguments' subtree, excluding non-exclusive objects.
    That is, objects that are referenced by objects that are not in this subtree.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    marked : set, optional
        An existing set of marked objects.
        Objects that are in this set will not be traversed.
        If a set is given, it will be updated with all the traversed objects.

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
    subtree = tuple(traverse_bfs(*objs, marked=marked))

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


def get_deep_size(*objs, exclude: Optional[Iterable] = None, get_size_func=sys.getsizeof) -> int:
    """
    Calculates the deep size of all the arguments.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        Iterable of objects to exclude from this size calculation.
    get_size_func : function, optional
        A function that determines the object size (default: `sys.getsizeof()`)

    Returns
    -------
    int
        The objects' deep size in bytes.

    See Also
    --------
    traverse_bfs : to understand which objects are traversed.
    """
    if exclude is not None:
        marked = set(map(id, traverse_bfs(*exclude)))
    else:
        marked = None
    return sum(map(get_size_func, traverse_bfs(*objs, marked=marked)))


def get_exclusive_deep_size(*objs, exclude: Optional[Iterable] = None, get_size_func=sys.getsizeof) -> int:
    """
    Calculates the deep size of all the arguments, excluding non-exclusive objects.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        Iterable of objects to exclude from this size calculation.
    get_size_func : function, optional
        A function that determines the object size (default: `sys.getsizeof()`)

    Returns
    -------
    int
        The objects' deep size in bytes.

    See Also
    --------
    traverse_exclusive_bfs : to understand which objects are traversed.
    """
    if exclude is not None:
        marked = set(map(id, traverse_bfs(*exclude)))
    else:
        marked = None
    return sum(map(get_size_func, traverse_exclusive_bfs(*objs, marked=marked)))
