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
import sys
from dataclasses import dataclass
from typing import Any, Callable, Optional

from objsize.traverse import MarkedSet, TraversalSettings

SizeFunc = Callable[[Any], int]

# See https://docs.python.org/3/library/sys.html#sys.getsizeof
default_get_size = sys.getsizeof


@dataclass(frozen=True)
class ObjSizeSettings(TraversalSettings):
    """
    Object size settings.

    Attributes
    ----------
    get_size_func : callable
        A function that determines the object size.
        Default: `sys.getsizeof()`.
        See: https://docs.python.org/3/library/sys.html#sys.getsizeof

    See Also
    --------
    TraversalSettings : for the rest of the attributes.
    """

    get_size_func: SizeFunc = default_get_size

    def get_deep_size(
        self, *objs: Any, marked_set: Optional[MarkedSet] = None, exclude_set: Optional[MarkedSet] = None
    ):
        """
        Calculates the deep size of all the arguments.

        Parameters
        ----------
        objs : object(s)
            One or more object(s).
        marked_set: set, optional
            See `TraversalContext`.
        exclude_set: set, optional
            See `TraversalContext`.

        Returns
        -------
        int
            The objects' deep size in bytes.

        See Also
        --------
        traverse_bfs : to understand which objects are traversed.
        """
        return sum(map(self.get_size_func, self.traverse_bfs(*objs, marked_set=marked_set, exclude_set=exclude_set)))

    def get_exclusive_deep_size(
        self, *objs: Any, marked_set: Optional[MarkedSet] = None, exclude_set: Optional[MarkedSet] = None
    ):
        """
        Calculates the deep size of all the arguments, excluding non-exclusive objects.

        Parameters
        ----------
        objs : object(s)
            One or more object(s).
        marked_set: set, optional
            See `TraversalContext`.
        exclude_set: set, optional
            See `TraversalContext`.

        Returns
        -------
        int
            The objects' deep size in bytes.

        See Also
        --------
        traverse_exclusive_bfs : to understand which objects are traversed.
        """
        return sum(
            map(self.get_size_func, self.traverse_exclusive_bfs(*objs, marked_set=marked_set, exclude_set=exclude_set))
        )
