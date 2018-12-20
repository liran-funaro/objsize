# objsize

Traversal over Python's objects sub-tree and calculating
the total size of the sub-tree (deep size).

This module uses python internal GC implementation
to traverse all decedent objects.
It ignores type objects (i.e., `isinstance(o, type)`)
such as classes and modules, as they are common among all objects.
It is implemented without recursive calls for best performance.


# Features

- Calculate single/multiple object(s) deep size.
- Exclude non exclusive objects.
- Traverse single/multiple objects(s) sub tree.


# Install

```bash
pip install objsize
```


# Basic Usage

Calculate an object size including all its members.

```python
>>> import objsize
>>> objsize.get_deep_size(dict(arg1='hello', arg2='world'))
348
```

It is possible to calculate the deep size of multiple objects by passing multiple arguments:

```python
>>> objsize.get_deep_size(['hello', 'world'], dict(arg1='hello', arg2='world'), {'hello', 'world'})
652
```

# Complex Data

`objsize` can calculate the size of an object's entire sub-tree
regardless of the type of objects in it, and its depth.

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
796
```

We might want to ignore non exclusive objects such as the ones stored in `my_data`.

```python
>>> objsize.get_exclusive_deep_size(my_obj)
408
```

# Traversal

A user can implement its own function over the entire sub tree
using the traversal method, which traverse all the objects in the sub tree.

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

Similirarly to before, non exclusive objects can be ignored.

```python
>>> for o in objsize.traverse_exclusive_bfs(my_obj):
...     print(o)
... 
MyClass
{'x': [0, 1, 2], 'y': [3, 4, 5], 'd': {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}}
{'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass}
```

# License
[GPL](LICENSE.txt)
