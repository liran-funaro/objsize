# objsize

Calculates an object deep size.

This module uses python internal GC implementation
to traverse all decedent objects.
It ignores type objects (`isinstance(o, type)`)
such as classes and modules as they are common among all objects.
It is implemented without recursive calls
for best performance.


# Usage
```python
import numpy as np
from objsize import get_deep_obj_size

x = np.random.rand(1024).astype(np.float64)
y = np.random.rand(1024).astype(np.float64)
d = {'x': x, 'y': y}

class MyClass:
    def __init__(self, xx, yy, dd):
        self.x = xx
        self.y = yy
        self.d = dd

my_obj = MyClass(x, y, d)
get_deep_obj_size(my_obj)
# 16984
```


# Install (beta)
`python setup.py develop --user`


# License
[GPL](LICENSE)
