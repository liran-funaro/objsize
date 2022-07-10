"""
Unittests for `objsize`.

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
import sys
import unittest
from collections import namedtuple

import objsize


def calc_class_obj_sz(obj, *field_names):
    sz = sys.getsizeof(obj) + sys.getsizeof(obj.__dict__)
    if sys.version_info[0] < 3:
        # python 2 classes include extra string for each member.
        sz += sum(map(sys.getsizeof, field_names))
    return sz


class FakeClass:
    def __init__(self, a):
        self._a = a

    @staticmethod
    def sizeof(o):
        return calc_class_obj_sz(o)


class TestDeepObjSize(unittest.TestCase):

    def test_exclusive(self):
        import uuid
        import gc
        obj = [str(uuid.uuid4()) for _ in range(5)]
        expected_sz = sys.getsizeof(obj) + sum(map(sys.getsizeof, obj))

        self.assertEqual(expected_sz, objsize.get_deep_size(obj))

        gc.collect()
        self.assertEqual(expected_sz, objsize.get_exclusive_deep_size(obj))

        fake_holder = [obj[2]]
        expected_sz -= sys.getsizeof(fake_holder[0])

        gc.collect()
        self.assertEqual(expected_sz, objsize.get_exclusive_deep_size(obj))

    def test_exclude(self):
        import uuid
        obj = [str(uuid.uuid4()) for _ in range(5)]
        expected_sz = sys.getsizeof(obj) + sum(map(sys.getsizeof, obj))

        self.assertEqual(expected_sz, objsize.get_deep_size(obj))

        exclude = [obj[2]]
        expected_sz -= sys.getsizeof(exclude[0])

        self.assertEqual(expected_sz, objsize.get_deep_size(obj, exclude=exclude))

    def test_exclusive_exclude(self):
        import uuid
        import gc
        obj = [str(uuid.uuid4()) for _ in range(5)]
        expected_sz = sys.getsizeof(obj) + sum(map(sys.getsizeof, obj))

        self.assertEqual(expected_sz, objsize.get_deep_size(obj))

        gc.collect()
        self.assertEqual(expected_sz, objsize.get_exclusive_deep_size(obj))

        fake_holder = [obj[2]]
        expected_sz -= sys.getsizeof(fake_holder[0])

        exclude = [obj[1]]
        expected_sz -= sys.getsizeof(exclude[0])

        gc.collect()
        self.assertEqual(expected_sz, objsize.get_exclusive_deep_size(obj, exclude=exclude))

    def test_size_func(self):
        import uuid
        obj = [str(uuid.uuid4()) for _ in range(5)]
        expected_sz = sys.getsizeof(obj) + sum(map(sys.getsizeof, obj))
        obj.append("test")

        def size_func(o):
            if o == "test":
                return 0
            else:
                return sys.getsizeof(o)

        self.assertEqual(expected_sz, objsize.get_deep_size(obj, get_size_func=size_func))

    def test_class_with_None(self):
        # None doesn't occupy extra space because it is a singleton
        obj = FakeClass(None)
        self.assertEqual(
            FakeClass.sizeof(obj),
            objsize.get_deep_size(obj))

    def test_class_with_string(self):
        runtime_int = 15
        string = '=' * runtime_int

        # the string does occupy space
        obj = FakeClass(string)
        self.assertEqual(
            FakeClass.sizeof(obj) + sys.getsizeof(string),
            objsize.get_deep_size(obj))

    """
    Thanks to bosswissam for the following list of tests.
    Taken from: https://github.com/bosswissam/pysize

    The following tests are under MIT license.

    MIT License

    Copyright (c) [2018] [Wissam Jarjoui]

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    """

    def test_empty_list(self):
        empty_list = []
        self.assertEqual(sys.getsizeof(empty_list),
                         objsize.get_deep_size(empty_list))

    def test_list_of_collections(self):
        collection_list = [[], {}, ()]
        empty_list_size = sys.getsizeof([])
        empty_tuple_size = sys.getsizeof(())
        empty_dict_size = sys.getsizeof({})
        expected_size = sys.getsizeof(collection_list) + empty_list_size + empty_tuple_size + empty_dict_size

        self.assertEqual(expected_size, objsize.get_deep_size(collection_list))

    def test_no_double_counting(self):
        rep = ["test1"]
        obj = [rep, rep]
        obj2 = [rep]
        expected_sz = objsize.get_deep_size(obj2) - sys.getsizeof(obj2) + sys.getsizeof(obj)
        self.assertEqual(expected_sz, objsize.get_deep_size(obj))

    def test_gracefully_handles_self_referential_objects(self):
        class MyClass(object):
            pass

        obj = MyClass()
        obj.prop = obj
        self.assertEqual(objsize.get_deep_size(obj), objsize.get_deep_size(obj.prop))

    def test_string(self):
        test_string = "abc"
        self.assertEqual(sys.getsizeof(test_string), objsize.get_deep_size(test_string))

    def test_custom_class(self):
        class MyClass(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        point = MyClass(3, 4)
        expected_size = (calc_class_obj_sz(point, 'x', 'y') +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))
        self.assertEqual(expected_size, objsize.get_deep_size(point))

    def test_namedtuple(self):
        Point = namedtuple('Point', ['x', 'y'])
        point = Point(3, 4)
        expected_size = (sys.getsizeof(point) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))
        self.assertEqual(expected_size, objsize.get_deep_size(point))

    def test_subclass_of_namedtuple(self):
        class MyPoint(namedtuple('MyPoint', ['x', 'y'])):
            pass

        point = MyPoint(3, 4)
        # namedtuple does not contains a dict.
        # It is created on request and is not cached for later calls:
        # >>> point = MyPoint(3, 4)
        # >>> all_obj = {id(o) for o in gc.get_objects()}
        # >>> id(point.__dict__) in all_obj
        # False
        # >>> all_obj = {id(o) for o in gc.get_objects()}
        # >>> id(point.__dict__) in all_obj
        # False
        expected_size = (sys.getsizeof(point) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))
        self.assertEqual(expected_size, objsize.get_deep_size(point))

    def test_subclass_of_namedtuple_with_slots(self):
        class MyPoint(namedtuple('MyPoint', ['x', 'y'])):
            __slots__ = ()

        point = MyPoint(3, 4)
        expected_size = (sys.getsizeof(point) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))
        self.assertEqual(expected_size, objsize.get_deep_size(point))

    def test_slots(self):
        class MySlots1(object):
            __slots__ = ["number1"]

            def __init__(self, number1):
                self.number1 = number1

        class MySlots2(object):
            __slots__ = ["number1", "number2"]

            def __init__(self, number1, number2):
                self.number1 = number1
                self.number2 = number2

        class MySlots3(object):
            __slots__ = ["number1", "number2", "number3"]

            def __init__(self, number1, number2, number3):
                self.number1 = number1
                self.number2 = number2
                self.number3 = number3

        s1 = MySlots1(7)
        s2 = MySlots2(3, 4)
        s3 = MySlots3(4, 5, 6)

        s1_sz = sys.getsizeof(s1) + sys.getsizeof(7)
        s2_sz = sys.getsizeof(s2) + sys.getsizeof(3) + sys.getsizeof(4)
        s3_sz = sys.getsizeof(s3) + sys.getsizeof(4) + sys.getsizeof(5) + sys.getsizeof(6)

        self.assertEqual(s1_sz, objsize.get_deep_size(s1))
        self.assertEqual(s2_sz, objsize.get_deep_size(s2))
        self.assertEqual(s3_sz, objsize.get_deep_size(s3))

    def test_multi_obj(self):
        class MyClass(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        strs = 'hello world', 'foo bar', 'something else'
        objs = MyClass(strs[0], strs[1]), MyClass(strs[0], strs[2]), MyClass(strs[1], strs[2])
        expected_sz = sum(map(sys.getsizeof, strs))

        expected_sz += sum(calc_class_obj_sz(o, 'x', 'y') for o in objs)

        self.assertEqual(expected_sz, objsize.get_deep_size(*objs))
        self.assertEqual(expected_sz, objsize.get_deep_size(*objs, *objs))
