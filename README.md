<!---
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
--->

# objsize

[![Coverage Status](https://coveralls.io/repos/github/liran-funaro/objsize/badge.svg?branch=master)](https://coveralls.io/github/liran-funaro/objsize?branch=master)
[![Downloads](https://static.pepy.tech/badge/objsize)](https://pepy.tech/project/objsize)

Traversal over Python's objects subtree and calculate the total size of the subtree in bytes (deep size).

This module traverses all child objects using Python's internal GC implementation.
It attempts to ignore shared objects (i.e., `None`, types, modules, classes, functions, lambdas), as they are common
among all objects.
It is implemented without recursive calls for high performance.

# Features

- Traverse objects' subtree
- Calculate objects' (deep) size in bytes
- Exclude non-exclusive objects
- Exclude specified objects subtree
- Allow the user to specify unique handlers for:
    - Object's size calculation
    - Object's referents (i.e., its children)
    - Object filter (skip specific objects)

[Pympler](https://pythonhosted.org/Pympler/) also supports determining an object deep size via `pympler.asizeof()`.
There are two main differences between `objsize` and `pympler`.

1. `objsize` has additional features:
    * Traversing the object subtree: iterating all the object's descendants one by one.
    * Excluding non-exclusive objects. That is, objects that are also referenced from somewhere else in the program.
      This is true for calculating the object's deep size and for traversing its descendants.
2. `objsize` has a simple and robust implementation with significantly fewer lines of code, compared to `pympler`.
   The Pympler implementation uses recursion, and thus have to use a maximal depth argument to avoid reaching Python's
   max depth.
   `objsize`, however, uses BFS which is more efficient and simple to follow.
   Moreover, the Pympler implementation carefully takes care of any object type.
   `objsize` archives the same goal with a simple and generic implementation, which has fewer lines of code.

# Install

```bash
pip install objsize==0.6.1
```

# Basic Usage

Calculate the size of the object including all its members in bytes.

```pycon
>>> import objsize
>>> objsize.get_deep_size(dict(arg1='hello', arg2='world'))
340
```

It is possible to calculate the deep size of multiple objects by passing multiple arguments:

```pycon
>>> objsize.get_deep_size(['hello', 'world'], dict(arg1='hello', arg2='world'), {'hello', 'world'})
628
```

# Complex Data

`objsize` can calculate the size of an object's entire subtree in bytes regardless of the type of objects in it, and its
depth.

Here is a complex data structure, for example, that include a self reference:

```python
my_data = (list(range(3)), list(range(3, 6)))


class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.d = {'x': x, 'y': y, 'self': self}

    def __repr__(self):
        return "MyClass"


my_obj = MyClass(*my_data)
```

We can calculate `my_obj` deep size, including its stored data.

```pycon
>>> objsize.get_deep_size(my_obj)
708
```

We might want to ignore non-exclusive objects such as the ones stored in `my_data`.

```pycon
>>> objsize.get_deep_size(my_obj, exclude=[my_data])
384
```

Or simply let `objsize` detect that automatically:

```pycon
>>> objsize.get_exclusive_deep_size(my_obj)
384
```

# Non Shared Functions or Classes

`objsize` filters functions, lambdas, and classes by default since they are usually shared among many objects.
For example:

```pycon
>>> method_dict = {"identity": lambda x: x, "double": lambda x: x*2}
>>> objsize.get_deep_size(method_dict)
232
```

Some objects, however, as illustrated in the above example, have unique functions not shared by other objects.
Due to this, it may be useful to count their sizes.
You can achieve this by providing an alternative filter function.

```pycon
>>> objsize.get_deep_size(method_dict, filter_func=objsize.shared_object_filter)
986
```

Notes:

* The default filter function is `objsize.shared_object_or_function_filter`.
* When using `objsize.shared_object_filter`, shared functions and lambdas are also counted, but builtin functions are
  still excluded.

# Special Cases

Some objects handle their data in a way that prevents Python's GC from detecting it.
The user can supply a special way to calculate the actual size of these objects.

## Case 1: `torch`

Using a simple calculation of the object size won't work for `torch.Tensor`.

```pycon
>>> import torch
>>> objsize.get_deep_size(torch.rand(200))
72
```

So the user can define its own size calculation handler for such cases:

```python
import objsize
import sys
import torch


def get_size_of_torch(o):
    # `objsize.safe_is_instance` catches `ReferenceError` caused by `weakref` objects
    if objsize.safe_is_instance(o, torch.Tensor):
        return sys.getsizeof(o.storage())
    else:
        return sys.getsizeof(o)
```

Then use it as follows:

```pycon
>>> import torch
>>> objsize.get_deep_size(
...   torch.rand(200),
...   get_size_func=get_size_of_torch
... )
848
```

However, this neglects the object's internal structure.
The user can help `objsize` to find the object's hidden storage by supplying it with its own referent and filter
functions:

```python
import objsize
import gc
import torch


def get_referents_torch(*objs):
    # Yield all native referents
    yield from gc.get_referents(*objs)

    for o in objs:
        # If the object is a torch tensor, then also yield its storage
        if type(o) == torch.Tensor:
            yield o.storage()


def filter_func(o):
    # Torch storage points to another meta storage that is
    # already included in the outer storage calculation, 
    # so we need to filter it.
    # Also, `torch.dtype` is a common object like Python's types.
    return not objsize.safe_is_instance(o, (
        *objsize.SharedObjectOrFunctionType, torch.storage._UntypedStorage, torch.dtype
    ))
```

Then use these as follows:

```pycon
>>> import torch
>>> objsize.get_deep_size(
...   torch.rand(200),
...   get_referents_func=get_referents_torch, 
...   filter_func=filter_func
... )
1024
```

## Case 2: `weakref`

Using a simple calculation of the object size won't work for `weakref.proxy`.

```pycon
>>> import weakref
>>> class Foo(list):
...     pass
... 
>>> o = Foo([0]*100)
>>> objsize.get_deep_size(o)
896
>>> o_ref = weakref.proxy(o)
>>> objsize.get_deep_size(o_ref)
72
```

To mitigate this, you can provide a method that attempts to fetch the proxy's referents:

```python
import weakref
import gc


def get_weakref_referents(*objs):
    yield from gc.get_referents(*objs)

    for o in objs:
        if type(o) in weakref.ProxyTypes:
            try:
                yield o.__repr__.__self__
            except ReferenceError:
                pass
```

Then use it as follows:

```pycon
>>> objsize.get_deep_size(o_ref, get_referents_func=get_weakref_referents)
968
```

After the referenced object will be collected, then the size of the proxy object will be reduced.

```pycon
>>> del o
>>> gc.collect()
>>> # Wait for the object to be collected 
>>> objsize.get_deep_size(o_ref, get_referents_func=get_weakref_referents)
72
```

# Traversal

A user can implement its own function over the entire subtree using the traversal method, which traverses all the
objects in the subtree.

```pycon
>>> for o in objsize.traverse_bfs(my_obj):
...     print(o)
... 
MyClass
{'x': [0, 1, 2], 'y': [3, 4, 5], 'd': {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}}
[0, 1, 2]
[3, 4, 5]
{'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}
2
1
0
5
4
3
```

Similar to before, non-exclusive objects can be ignored.

```pycon
>>> for o in objsize.traverse_exclusive_bfs(my_obj):
...     print(o)
... 
MyClass
{'x': [0, 1, 2], 'y': [3, 4, 5], 'd': {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}}
{'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}
```

# License

[BSD-3](LICENSE)
