# objsize

Calculates an object deep size.

This module uses python internal GC implementation
to traverse all decedent objects.
It ignores type objects (`isinstance(o, type)`)
such as classes and modules as they are common among all objects.
It is implemented without recursive calls
for best performance.


# Install
`pip install objsize`


# Usage
```python
from objsize import get_deep_size

my_data = (list(range(5)), list(range(10)))

class MyClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.d = {'x': x, 'y': y, 'self': self}

my_obj = MyClass(*my_data)

# Calculates my_obj deep size, including its stored data.
print(get_deep_size(my_obj))
# 1012

# Calculates my_obj deep size, ignoring non exclusive
# objects such as the ones stores in my_data.
print(get_deep_size(my_obj, only_exclusive=True))
# 408
```

# License
[GPL](LICENSE.txt)
