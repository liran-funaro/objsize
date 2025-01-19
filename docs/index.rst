objsize
=======

|Coverage Status| |Downloads|

The ``objsize`` Python package allows for the exploration and
measurement of an object’s complete memory usage in bytes, including its
child objects. This process, often referred to as deep size calculation,
is achieved through Python’s internal Garbage Collection (GC) mechanism.

The ``objsize`` package is designed to ignore shared objects, such as
``None``, types, modules, classes, functions, and lambdas, because they
are shared across many instances. One of the key performance features of
``objsize`` is that it avoids recursive calls, ensuring a faster and
safer execution.

Key Features
------------

* Traverse objects’ subtree
* Calculates the size of objects, including nested objects (deep size), in bytes
* Exclude non-exclusive objects
* Exclude specified objects subtree
* Provides flexibility by allowing users to define custom handlers for:

  -  Object’s size calculation
  -  Object’s referents (i.e., its children)
  -  Object filter (skip specific objects)

Documentation
-------------
.. autosummary::
   :toctree: library
   :template: custom-module-template.rst
   :recursive:

   objsize


Install
=======

.. code:: bash

   pip install objsize==0.7.1

Basic Usage
===========

Calculate the size of the object including all its members in bytes.

.. code:: pycon

   >>> import objsize
   >>> objsize.get_deep_size(dict(arg1='hello', arg2='world'))
   340

It is possible to calculate the deep size of multiple objects by passing
multiple arguments:

.. code:: pycon

   >>> objsize.get_deep_size(['hello', 'world'], dict(arg1='hello', arg2='world'), {'hello', 'world'})
   628

Complex Data
============

``objsize`` can calculate the size of an object’s entire subtree in
bytes regardless of the type of objects in it, and its depth.

Here is a complex data structure, for example, that include a self
reference:

.. code:: python

   my_data = list(range(3)), list(range(3, 6))

   class MyClass:
       def __init__(self, x, y):
           self.x = x
           self.y = y
           self.d = {'x': x, 'y': y, 'self': self}

       def __repr__(self):
           return f"{self.__class__.__name__}()"

   my_obj = MyClass(*my_data)

We can calculate ``my_obj`` deep size, including its stored data.

.. code:: pycon

   >>> objsize.get_deep_size(my_obj)
   724

We might want to ignore non-exclusive objects such as the ones stored in
``my_data``.

.. code:: pycon

   >>> objsize.get_deep_size(my_obj, exclude=[my_data])
   384

Or simply let ``objsize`` detect that automatically:

.. code:: pycon

   >>> objsize.get_exclusive_deep_size(my_obj)
   384

Non Shared Functions or Classes
===============================

``objsize`` filters functions, lambdas, and classes by default since
they are usually shared among many objects. For example:

.. code:: pycon

   >>> method_dict = {"identity": lambda x: x, "double": lambda x: x*2}
   >>> objsize.get_deep_size(method_dict)
   232

Some objects, however, as illustrated in the above example, have unique
functions not shared by other objects. Due to this, it may be useful to
count their sizes. You can achieve this by providing an alternative
filter function.

.. code:: pycon

   >>> objsize.get_deep_size(method_dict, filter_func=objsize.shared_object_filter)
   986

Notes:

*  The default filter function is
   :py:func:`objsize.traverse.shared_object_or_function_filter`.
*  When using :py:func:`objsize.traverse.shared_object_filter`, shared functions and
   lambdas are also counted, but builtin functions are still excluded.

Special Cases
=============

Some objects handle their data in a way that prevents Python’s GC from
detecting it. The user can supply a special way to calculate the actual
size of these objects.

Case 1: :py:mod:`torch`
-----------------------

Using a simple calculation of the object size won’t work for
:py:class:`torch.Tensor`.

.. code:: pycon

   >>> import torch
   >>> objsize.get_deep_size(torch.rand(200))
   72

So the user can define its own size calculation handler for such cases:

.. code:: python

   import objsize
   import sys
   import torch

   def get_size_of_torch(o):
       # `objsize.safe_is_instance` catches `ReferenceError` caused by `weakref` objects
       if objsize.safe_is_instance(o, torch.Tensor):
           return sys.getsizeof(o) + (o.element_size() * o.nelement())
       else:
           return sys.getsizeof(o)

Then use it as follows:

.. code:: pycon

   >>> objsize.get_deep_size(
   ...   torch.rand(200),
   ...   get_size_func=get_size_of_torch
   ... )
   872

The above approach may neglect the object’s internal structure. The user
can help ``objsize`` to find the object’s hidden storage by supplying it
with its own referent and filter functions:

.. code:: python

   import objsize
   import gc
   import torch

   def get_referents_torch(*objs):
       # Yield all native referents
       yield from gc.get_referents(*objs)
       for o in objs:
           # If the object is a torch tensor, then also yield its storage
           if type(o) == torch.Tensor:
               yield o.untyped_storage()

   # `torch.dtype` is a common object like Python's types.
   MySharedObjects = (*objsize.SharedObjectOrFunctionType, torch.dtype)

   def filter_func(o):
       return not objsize.safe_is_instance(o, MySharedObjects)

Then use these as follows:

.. code:: pycon

   >>> objsize.get_deep_size(
   ...   torch.rand(200),
   ...   get_referents_func=get_referents_torch,
   ...   filter_func=filter_func
   ... )
   928

Case 2: :py:mod:`weakref`
-------------------------

Using a simple calculation of the object size won’t work for
``weakref.proxy``.

.. code:: pycon

   >>> from collections import UserList
   >>> o = UserList([0]*100)
   >>> objsize.get_deep_size(o)
   1032
   >>> import weakref
   >>> o_ref = weakref.proxy(o)
   >>> objsize.get_deep_size(o_ref)
   72

To mitigate this, you can provide a method that attempts to fetch the
proxy’s referents:

.. code:: python

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

Then use it as follows:

.. code:: pycon

   >>> objsize.get_deep_size(o_ref, get_referents_func=get_weakref_referents)
   1104

After the referenced object will be collected, then the size of the
proxy object will be reduced.

.. code:: pycon

   >>> del o
   >>> gc.collect()
   >>> # Wait for the object to be collected
   >>> objsize.get_deep_size(o_ref, get_referents_func=get_weakref_referents)
   72

Object Size Settings
====================

To avoid repeating the input settings when handling the special cases
above, you can use the :py:class:`~objsize.traverse.ObjSizeSettings` class.

.. code:: pycon

   >>> torch_objsize = objsize.ObjSizeSettings(
   ...   get_referents_func=get_referents_torch,
   ...   filter_func=filter_func,
   ... )
   >>> torch_objsize.get_deep_size(torch.rand(200))
   928
   >>> torch_objsize.get_deep_size(torch.rand(300))
   1328

See :py:class:`~objsize.traverse.ObjSizeSettings` for the
list of configurable parameters.

Traversal
=========

A user can implement its own function over the entire subtree using the
traversal method, which traverses all the objects in the subtree.

.. code:: pycon

   >>> for o in objsize.traverse_bfs(my_obj):
   ...     print(o)
   ...
   MyClass()
   {'x': [0, 1, 2], 'y': [3, 4, 5], 'd': {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass()}}
   [0, 1, 2]
   [3, 4, 5]
   {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass()}
   2
   1
   0
   5
   4
   3

Similar to before, non-exclusive objects can be ignored.

.. code:: pycon

   >>> for o in objsize.traverse_exclusive_bfs(my_obj):
   ...     print(o)
   ...
   MyClass()
   {'x': [0, 1, 2], 'y': [3, 4, 5], 'd': {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass()}}
   {'x': [0, 1, 2], 'y': [3, 4, 5], 'self': MyClass()}

Alternative
===========

`Pympler <https://pythonhosted.org/Pympler/>`__ also supports
determining an object deep size via ``pympler.asizeof()``. There are two
main differences between ``objsize`` and ``pympler``.

#. ``objsize`` has additional features:

   *  Traversing the object subtree: iterating all the object’s
      descendants one by one.
   *  Excluding non-exclusive objects. That is, objects that are also
      referenced from somewhere else in the program. This is true for
      calculating the object’s deep size and for traversing its
      descendants.

#. ``objsize`` has a simple and robust implementation with significantly
   fewer lines of code, compared to ``pympler``. The Pympler
   implementation uses recursion, and thus have to use a maximal depth
   argument to avoid reaching Python’s max depth. ``objsize``, however,
   uses BFS which is more efficient and simple to follow. Moreover, the
   Pympler implementation carefully takes care of any object type.
   ``objsize`` archives the same goal with a simple and generic
   implementation, which has fewer lines of code.

License: BSD-3
==============

.. include:: ../LICENSE
   :parser: myst_parser.sphinx_

.. |Coverage Status| image:: https://coveralls.io/repos/github/liran-funaro/objsize/badge.svg?branch=master
   :target: https://coveralls.io/github/liran-funaro/objsize?branch=master
.. |Downloads| image:: https://static.pepy.tech/badge/objsize
   :target: https://pepy.tech/project/objsize

