# objsize

Traversal over Python's objects sub-tree and calculating
the total size of the sub-tree (deep size).

This module uses python internal GC implementation
to traverse all decedent objects.
It ignores type objects (`isinstance(o, type)`)
such as classes and modules, as they are common among all objects.
It is implemented without recursive calls for best performance.


# Install

```bash
pip install objsize
```


# Usage

```python
my_data = (list(range(5)), list(range(10)))

class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.d = {'x': x, 'y': y, 'self': self}
        
    def __repr__(self):
        return "MyClass"

my_obj = MyClass(*my_data)

from objsize import get_deep_size
# Calculates my_obj deep size, including its stored data.
print(get_deep_size(my_obj))
# 1012

from objsize import get_exclusive_deep_size
# Calculates my_obj deep size, ignoring non exclusive
# objects such as the ones stored in my_data.
print(get_exclusive_deep_size(my_obj))
# 408

from objsize import traverse_bfs
# Traverse all the objects in my_obj sub tree.
for o in traverse_bfs(my_obj):
    print(o)
# {'x': [0, 1, 2, 3, 4], 'y': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'd': {'x': [0, 1, 2, 3, 4], 'y': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'self': MyClass}}
# [0, 1, 2, 3, 4]
# [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
# {'x': [0, 1, 2, 3, 4], 'y': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'self': MyClass}
# 4
# 3
# 2
# 1
# 0
# 9
# 8
# 7
# 6
# 5

from objsize import traverse_exclusive_bfs
# Traverse all the objects in my_obj sub tree, ignoring non exclusive ones.
for o in traverse_exclusive_bfs(my_obj):
    print(o)
# {'x': [0, 1, 2, 3, 4], 'y': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'd': {'x': [0, 1, 2, 3, 4], 'y': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'self': MyClass}}
# {'x': [0, 1, 2, 3, 4], 'y': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'self': MyClass}
```

# License
[GPL](LICENSE.txt)
