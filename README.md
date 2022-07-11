# objsize

[![Coverage Status](https://coveralls.io/repos/github/liran-funaro/objsize/badge.svg?branch=master)](https://coveralls.io/github/liran-funaro/objsize?branch=master)

Traversal over Python's objects subtree and calculate the total size of the subtree in bytes (deep size).

This module traverses all child objects using Python's internal GC implementation.
It attempts to ignore singletons (e.g., `None`) and type objects (i.e., classes and modules), as they are common among all objects.
It is implemented without recursive calls for high performance.


# Features

- Traverse objects' subtree
- Calculate objects' (deep) size in bytes
- Exclude non-exclusive objects
- Exclude specified objects
- Allow the user to specify unique handlers for:
  - Object's size calculation
  - Object's referents (i.e., its children)
  - Object filter (skip specific objects)


[Pympler](https://pythonhosted.org/Pympler/) also supports determining an object deep size via `pympler.asizeof()`.
There are two main differences between `objsize` and `pympler`.

1. `objsize` has additional features:
   * Traversing the object subtree: iterating all the object's descendants one by one.
   * Excluding non-exclusive objects. That is, objects that are also referenced from somewhere else in the program. This is true for calculating the object's deep size and for traversing its descendants.
2. `objsize` has a simple and robust implementation with significantly fewer lines of code, compared to `pympler`.
   The Pympler implementation uses recursion, and thus have to use a maximal depth argument to avoid reaching Python's max depth.
   `objsize`, however, uses BFS which is more efficient and simple to follow.
   Moreover, the Pympler implementation carefully takes care of any object type.
   `objsize` archives the same goal with a simple and generic implementation, which has fewer lines of code.


# Install

```bash
pip install objsize=0.5.1
```

# Basic Usage

Calculate the size of the object including all its members in bytes.

```python
>>> import objsize
>>> objsize.get_deep_size(dict(arg1='hello', arg2='world'))
340
```

It is possible to calculate the deep size of multiple objects by passing multiple arguments:

```python
>>> objsize.get_deep_size(['hello', 'world'], dict(arg1='hello', arg2='world'), {'hello', 'world'})
628
```

# Complex Data

`objsize` can calculate the size of an object's entire subtree in bytes regardless of the type of objects in it, and its depth.

Here is a complex data structure, for example, that include a self reference:

```python
my_data = (list(range(3)), list(range(3,6)))

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

```python
>>> objsize.get_deep_size(my_obj)
708
```

We might want to ignore non-exclusive objects such as the ones stored in `my_data`.

```python
>>> objsize.get_exclusive_deep_size(my_obj)
384
```

Or simply let `objsize` know which objects to exclude:
```python
>>> objsize.get_deep_size(my_obj, exclude=[my_data])
384
```


# Special Cases
Some objects handle their data in a way that prevents Python's GC from detecting it.
The user can supply a special way to calculate the actual size of these objects.
For example, using a simple calculation of the object size won't work for `torch.Tensor`.

```python
>>> import torch
>>> objsize.get_deep_size(torch.rand(200))
72
```

So the user can define its own size calculation handler for such cases:
```python
import sys
import torch

def get_size_of_torch(o):
    if isinstance(o, torch.Tensor):
        return sys.getsizeof(o.storage())
    else:
        return sys.getsizeof(o)
```

Then use it as follows:
```python
>>> import torch
>>> objsize.get_deep_size(
...   torch.rand(200),
...   get_size_func=get_size_of_torch
... )
848
```

However, this neglects the object's internal structure.
The user can help `objsize` to find the object's hidden storage by supplying it with its own referent and filter functions:
```python
import gc
import torch

def get_referents_torch(*objs):
    # Yield all native referents
    yield from gc.get_referents(*objs)
    
    for o in objs:
        # If the object is a torch tensor, then also yield its storage
        if isinstance(o, torch.Tensor):
            yield o.storage()

def filter_func(o):
    # Torch storage points to another meta storage that is
    # already included in the outer storage calculation, 
    # so we need to filter it.
    # Also, `torch.dtype` is a common object like Python's types.
    return not isinstance(o, (type, torch.storage._UntypedStorage, torch.dtype))
```


Then use these as follows:
```python
>>> import torch
>>> objsize.get_deep_size(
...   torch.rand(200),
...   get_referents_func=get_referents_torch, 
...   filter_func=filter_func
... )
1024
```

# Traversal

A user can implement its own function over the entire subtree using the traversal method, which traverses all the objects in the subtree.

```python
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

```python
>>> for o in objsize.traverse_exclusive_bfs(my_obj):
...     print(o)
... 
MyClass
{'x': [0, 1, 2], 'y': [3, 4, 5], 'd': {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}}
{'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}
```

# License
[GPL](LICENSE)
