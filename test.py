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
import sys
import unittest
from collections import namedtuple

import objsize

tested_method = objsize.get_deep_obj_size


class TestDeepObjSize(unittest.TestCase):
    """
    Thanks to bosswissam for the following list of tests.
    Taken from: https://github.com/bosswissam/pysize
    """

    def test_empty_list(self):
        empty_list = []
        self.assertEqual(sys.getsizeof(empty_list),
                         tested_method(empty_list))

    def test_list_of_collections(self):
        collection_list = [[], {}, ()]
        pointer_byte_size = 8 * len(collection_list)
        empty_list_size = sys.getsizeof([])
        empty_tuple_size = sys.getsizeof(())
        empty_dict_size = sys.getsizeof({})
        expected_size = empty_list_size * 2 + empty_tuple_size + empty_dict_size + pointer_byte_size

        self.assertEqual(expected_size,
                         tested_method(collection_list))

    def test_no_double_counting(self):
        rep = ["test1"]
        obj = [rep, rep]
        obj2 = [rep]
        self.assertEqual(tested_method(obj), tested_method(obj2) + 8)

    def test_gracefully_handles_self_referential_objects(self):
        class MyClass(object):
            pass

        obj = MyClass()
        obj.prop = obj
        self.assertEqual(tested_method(obj), tested_method(obj.prop))

    def test_string(self):
        test_string = "abc"
        self.assertEqual(sys.getsizeof(test_string), tested_method(test_string))

    def test_custom_class(self):
        class MyClass(object):
            def __init__(self, x, y):
                self.x = x
                self.y = y

        point = MyClass(3, 4)
        expected_size = (sys.getsizeof(point) +
                         sys.getsizeof(point.__dict__) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))
        if sys.version_info[0] < 3:
            # python 2 classes include extra string for each member.
            expected_size += sys.getsizeof('x') + sys.getsizeof('y')
        self.assertEqual(tested_method(point), expected_size)

    def test_namedtuple(self):
        Point = namedtuple('Point', ['x', 'y'])
        point = Point(3, 4)
        self.assertEqual(tested_method(point),
                         sys.getsizeof(point) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))

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
        self.assertEqual(tested_method(point),
                         sys.getsizeof(point) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))

    def test_subclass_of_namedtuple_with_slots(self):
        class MyPoint(namedtuple('MyPoint', ['x', 'y'])):
            __slots__ = ()

        point = MyPoint(3, 4)
        self.assertEqual(tested_method(point),
                         sys.getsizeof(point) +
                         sys.getsizeof(3) +
                         sys.getsizeof(4))

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

        version_addition = 0

        if hasattr(sys.version_info, 'major') and sys.version_info.major == 3:
            version_addition = 4

        # base 40 for the class, 28 per integer, +8 per element
        self.assertEqual(tested_method(s2), tested_method(s1) + 28 + 4 + version_addition)
        self.assertEqual(tested_method(s3), tested_method(s2) + 28 + 4 + version_addition)
        self.assertEqual(tested_method(s3), tested_method(s1) + 56 + 8 + version_addition * 2)
        # *2 for the num of variables in difference
