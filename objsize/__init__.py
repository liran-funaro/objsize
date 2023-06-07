"""
Traversal over Python's objects subtree and calculating
the total size of the subtree (deep size).

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
import warnings
from typing import Any, Iterable, Iterator, Optional

from objsize.size import ObjSizeSettings, SizeFunc, default_get_size
from objsize.traverse import (
    FilterFunc,
    GetReferentsFunc,
    MarkedSet,
    SharedObjectOrFunctionType,
    SharedObjectType,
    TraversalContext,
    TraversalSettings,
    default_get_referents,
    default_object_filter,
    safe_is_instance,
    shared_object_filter,
    shared_object_or_function_filter,
)

__version__ = "0.6.1"


def traverse_bfs(
    *objs,
    exclude: Optional[Iterable[Any]] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_referents_func: GetReferentsFunc = default_get_referents,
    filter_func: FilterFunc = default_object_filter,
    exclude_modules_globals: bool = True,
) -> Iterator[Any]:
    """
    Traverse all the arguments' subtree.
    By default, this excludes shared objects, i.e., types, modules, functions, and lambdas.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `TraversalSettings`.
    marked_set : set, optional
        See `TraversalContext`.
    exclude_set : set, optional
        See `TraversalContext`.
    get_referents_func : callable
        See `TraversalSettings`.
    filter_func : callable
        See `TraversalSettings`.
    exclude_modules_globals : bool
        See `TraversalSettings`.

    Yields
    ------
    object
        The traversed objects, one by one.
    """
    settings = TraversalSettings(get_referents_func, filter_func, exclude, exclude_modules_globals)
    yield from settings.traverse_bfs(*objs, marked_set=marked_set, exclude_set=exclude_set)


def traverse_exclusive_bfs(
    *objs,
    exclude: Optional[Iterable[Any]] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_referents_func: GetReferentsFunc = default_get_referents,
    filter_func: FilterFunc = default_object_filter,
    exclude_modules_globals: bool = True,
) -> Iterator[Any]:
    """
    Traverse all the arguments' subtree, excluding non-exclusive objects.
    That is, objects that are referenced by objects that are not in this subtree.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `TraversalSettings`.
    marked_set : set, optional
        See `TraversalContext`.
    exclude_set : set, optional
        See `TraversalContext`.
    get_referents_func : callable
        See `TraversalSettings`.
    filter_func : callable
        See `TraversalSettings`.
    exclude_modules_globals : bool
        See `TraversalSettings`.

    Yields
    ------
    object
        The traversed objects, one by one.

    See Also
    --------
    traverse_bfs : to understand which objects are traversed.
    """
    settings = TraversalSettings(get_referents_func, filter_func, exclude, exclude_modules_globals)
    yield from settings.traverse_exclusive_bfs(*objs, marked_set=marked_set, exclude_set=exclude_set)


def get_deep_size(
    *objs,
    exclude: Optional[Iterable] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_size_func=default_get_size,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
    exclude_modules_globals: bool = True,
) -> int:
    """
    Calculates the deep size of all the arguments.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `TraversalSettings`.
    marked_set : set, optional
        See `TraversalContext`.
    exclude_set : set, optional
        See `TraversalContext`.
    get_size_func : function, optional
        See `ObjSizeSettings`.
    get_referents_func : callable
        See `TraversalSettings`.
    filter_func : callable
        See `TraversalSettings`.
    exclude_modules_globals : bool
        See `TraversalSettings`.

    Returns
    -------
    int
        The objects' deep size in bytes.

    See Also
    --------
    traverse_bfs : to understand which objects are traversed.
    """
    settings = ObjSizeSettings(get_referents_func, filter_func, exclude, exclude_modules_globals, get_size_func)
    return settings.get_deep_size(*objs, marked_set=marked_set, exclude_set=exclude_set)


def get_exclusive_deep_size(
    *objs,
    exclude: Optional[Iterable] = None,
    marked_set: Optional[MarkedSet] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_size_func=default_get_size,
    get_referents_func=default_get_referents,
    filter_func=default_object_filter,
    exclude_modules_globals: bool = True,
) -> int:
    """
    Calculates the deep size of all the arguments, excluding non-exclusive objects.

    Parameters
    ----------
    objs : object(s)
        One or more object(s).
    exclude : iterable, optional
        See `TraversalSettings`.
    marked_set : set, optional
        See `TraversalContext`.
    exclude_set : set, optional
        See `TraversalContext`.
    get_size_func : function, optional
        See `ObjSizeSettings`.
    get_referents_func : callable
        See `TraversalSettings`.
    filter_func : callable
        See `TraversalSettings`.
    exclude_modules_globals : bool
        See `TraversalSettings`.

    Returns
    -------
    int
        The objects' deep size in bytes.

    See Also
    --------
    traverse_exclusive_bfs : to understand which objects are traversed.
    """
    settings = ObjSizeSettings(get_referents_func, filter_func, exclude, exclude_modules_globals, get_size_func)
    return settings.get_exclusive_deep_size(*objs, marked_set=marked_set, exclude_set=exclude_set)


def get_exclude_set(
    exclude: Optional[Iterable[Any]] = None,
    exclude_set: Optional[MarkedSet] = None,
    get_referents_func: GetReferentsFunc = default_get_referents,
    filter_func: FilterFunc = default_object_filter,
    exclude_modules_globals: bool = False,
) -> Optional[set]:
    """
    objsize.get_exclude_set() is deprecated. It will be removed on version 1.0.0.

    Traverse all the arguments' subtree without ingesting the result, just to update the `exclude_set`.
    See `traverse_bfs()` for more information.

    Parameters
    ----------
    exclude : iterable, optional
        One or more object(s).
    exclude_set : set, optional
        See `ObjectFilter`.
    get_referents_func : callable
        See `ObjectIterSettings`.
    filter_func : callable
        See `ObjectIterSettings`.
    exclude_modules_globals : bool
        See `ObjectIterSettings`.

    Returns
    -------
    The updated exclude-set.
    """
    warnings.warn("objsize.get_exclude_set() is deprecated. It will be removed on version 1.0.0.", DeprecationWarning)
    settings = TraversalSettings(get_referents_func, filter_func, exclude, exclude_modules_globals)
    return settings.new_context(exclude_set=exclude_set).exclude_set
