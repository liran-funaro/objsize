"""
Unittests for `objsize`.
"""

import gc
import random
import sys
import threading
import uuid
import weakref
from collections import namedtuple
from typing import Any, List, Iterator

import pytest

import objsize
import objsize.traverse

##################################################################
# Helpers
##################################################################


def get_unique_strings(size=5) -> List[Any]:
    return [str(uuid.uuid4()) for _ in range(size)]


def get_flat_list_expected_size(lst):
    return sys.getsizeof(lst) + sum(map(sys.getsizeof, lst))


def calc_class_obj_sz(obj):
    return sys.getsizeof(obj) + sys.getsizeof(obj.__dict__)


class FakeClass:
    def __init__(self, a):
        self._a = a

    @staticmethod
    def sizeof(o):
        return calc_class_obj_sz(o)


def _test_all_update_techniques(**kwargs) -> Iterator[objsize.ObjSizeSettings]:
    yield objsize.ObjSizeSettings(**kwargs)
    yield objsize.ObjSizeSettings().replace(**kwargs)
    settings = objsize.ObjSizeSettings()
    settings.update(**kwargs)
    yield settings


def get_weakref_referents(*objs):
    yield from gc.get_referents(*objs)

    for o in objs:
        if type(o) in weakref.ProxyTypes:
            try:
                yield o.__repr__.__self__
            except ReferenceError:
                pass
        else:
            try:
                yield o.__dict__
            except AttributeError:
                pass


##################################################################
# Tests
##################################################################


def test_traverse():
    keys = get_unique_strings(3)
    tested_obj = {keys[0]: keys[1], keys[2]: set(keys)}
    objs = set(map(id, objsize.traverse_bfs(tested_obj)))
    expected_ids = set(map(id, [*keys, tested_obj, tested_obj[keys[2]]]))
    assert objs == expected_ids


def test_traverse_exclusive():
    keys = get_unique_strings(3)
    tested_obj = {keys[0]: keys[1], keys[2]: set(keys)}
    objs = set(map(id, objsize.traverse_exclusive_bfs(tested_obj)))
    expected_ids = set(map(id, [tested_obj, tested_obj[keys[2]]]))
    assert objs == expected_ids


def test_unique_string():
    obj = get_unique_strings(5)
    expected_sz = get_flat_list_expected_size(obj)
    assert expected_sz == objsize.get_deep_size(obj)


def test_exclusive():
    obj = get_unique_strings(5)
    expected_sz = get_flat_list_expected_size(obj)
    assert expected_sz == objsize.get_deep_size(obj)

    gc.collect()
    assert expected_sz == objsize.get_exclusive_deep_size(obj)

    fake_holder = [obj[2]]
    expected_sz -= sys.getsizeof(fake_holder[0])

    gc.collect()
    assert expected_sz == objsize.get_exclusive_deep_size(obj)


def test_exclude():
    obj = get_unique_strings(5)
    expected_sz = get_flat_list_expected_size(obj)

    exclude = [obj[2]]
    expected_sz -= sys.getsizeof(exclude[0])

    assert expected_sz == objsize.get_deep_size(obj, exclude=exclude)
    for cur_objsize in _test_all_update_techniques(exclude=exclude):
        assert expected_sz == cur_objsize.get_deep_size(obj)


def test_exclusive_exclude():
    obj = get_unique_strings(5)
    expected_sz = get_flat_list_expected_size(obj)

    gc.collect()
    assert expected_sz == objsize.get_exclusive_deep_size(obj)

    fake_holder = [obj[2]]
    expected_sz -= sys.getsizeof(fake_holder[0])

    exclude = [obj[1]]
    expected_sz -= sys.getsizeof(exclude[0])

    gc.collect()
    assert expected_sz == objsize.get_exclusive_deep_size(obj, exclude=exclude)
    for cur_objsize in _test_all_update_techniques(exclude=exclude):
        assert expected_sz == cur_objsize.get_exclusive_deep_size(obj)


def test_size_func():
    obj = get_unique_strings(5)
    obj.append("test")
    expected_sz = get_flat_list_expected_size(obj) - sys.getsizeof("test")

    def size_func(o):
        if o == "test":
            return 0
        else:
            return sys.getsizeof(o)

    assert expected_sz == objsize.get_deep_size(obj, get_size_func=size_func)
    for cur_objsize in _test_all_update_techniques(get_size_func=size_func):
        assert expected_sz == cur_objsize.get_deep_size(obj)


def test_referents_func():
    obj = get_unique_strings(5)
    expected_sz = get_flat_list_expected_size(obj)

    with_additional_str = obj[0]
    additional_obj = "additional"
    expected_sz += sys.getsizeof(additional_obj)

    def referents_func(*objs):
        yield from gc.get_referents(*objs)
        for o in objs:
            if o == with_additional_str:
                yield additional_obj

    assert expected_sz == objsize.get_deep_size(obj, get_referents_func=referents_func)
    for cur_objsize in _test_all_update_techniques(get_referents_func=referents_func):
        assert expected_sz == cur_objsize.get_deep_size(obj)


def test_filter_func():
    obj = get_unique_strings(5)
    subtree = get_unique_strings(3)
    obj.append(subtree)

    # We count subtree twice, then remove it once
    expected_sz = get_flat_list_expected_size(obj) - sys.getsizeof(subtree)

    def filter_func(o):
        return objsize.default_object_filter(o) and o != subtree

    assert expected_sz == objsize.get_deep_size(obj, filter_func=filter_func)
    for cur_objsize in _test_all_update_techniques(filter_func=filter_func):
        assert expected_sz == cur_objsize.get_deep_size(obj)


def test_class_with_none():
    # None doesn't occupy extra space because it is a singleton
    obj = FakeClass(None)
    assert FakeClass.sizeof(obj) == objsize.get_deep_size(obj)


def test_class_with_string():
    runtime_int = random.randint(50, 100)
    string = "=" * runtime_int

    # A string occupies space
    obj = FakeClass(string)
    assert FakeClass.sizeof(obj) + sys.getsizeof(string) == objsize.get_deep_size(obj)


def test_with_function():
    obj = {"func": lambda x: x}
    with_functions = _test_all_update_techniques(filter_func=objsize.shared_object_filter)
    without_functions = _test_all_update_techniques(filter_func=objsize.shared_object_or_function_filter)
    for wf, wof in zip(with_functions, without_functions):
        assert wf.get_deep_size(obj) > wof.get_deep_size(obj)

    with_functions_sz = objsize.get_deep_size(obj, filter_func=objsize.shared_object_filter)
    without_functions_sz = objsize.get_deep_size(obj, filter_func=objsize.shared_object_or_function_filter)
    assert with_functions_sz > without_functions_sz


def test_size_of_weak_ref():
    class Foo(list):
        pass

    obj = Foo(get_unique_strings(5))
    expected_sz = get_flat_list_expected_size(obj) + sys.getsizeof(obj.__dict__)
    assert expected_sz == objsize.get_deep_size(obj)

    wait_event = threading.Event()
    obj_proxy = weakref.proxy(obj, lambda value: wait_event.set())
    proxy_sz = sys.getsizeof(obj_proxy)
    expected_with_proxy_sz = proxy_sz + expected_sz

    assert expected_with_proxy_sz == objsize.get_deep_size(obj_proxy, get_referents_func=get_weakref_referents)
    for cur_objsize in _test_all_update_techniques(get_referents_func=get_weakref_referents):
        assert expected_with_proxy_sz == cur_objsize.get_deep_size(obj_proxy)

    del obj

    gc.collect()
    wait_event.wait()

    assert proxy_sz == objsize.get_deep_size(obj_proxy, get_referents_func=get_weakref_referents)
    for cur_objsize in _test_all_update_techniques(get_referents_func=get_weakref_referents):
        assert proxy_sz == cur_objsize.get_deep_size(obj_proxy)


# noinspection PyDeprecation
def test_get_exclude_set():
    with pytest.deprecated_call():
        init_set = objsize.get_exclude_set(exclude_modules_globals=False)
    assert len(init_set) > 0

    with pytest.deprecated_call():
        first_set = objsize.get_exclude_set(exclude_modules_globals=False)
    with pytest.deprecated_call():
        second_set = objsize.get_exclude_set(exclude_modules_globals=False)
    assert len(second_set) == len(first_set)

    obj1 = [1]
    with pytest.deprecated_call():
        second_set = objsize.get_exclude_set(obj1, exclude_set=set(first_set), exclude_modules_globals=False)
    assert len(second_set) == len(first_set) + 1

    obj2 = [2]
    with pytest.deprecated_call():
        third_set = objsize.get_exclude_set(obj2, exclude_set=set(second_set), exclude_modules_globals=False)
    assert len(third_set) == len(second_set) + 1


def test_bad_module():
    # noinspection PyTypeChecker
    sys.modules["fake_module"] = None
    objsize.get_deep_size({})


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


def test_empty_list():
    empty_list = []
    assert sys.getsizeof(empty_list) == objsize.get_deep_size(empty_list)


def test_list_of_collections():
    collection_list = [[], {}, ()]
    empty_list_size = sys.getsizeof([])
    empty_tuple_size = sys.getsizeof(())
    empty_dict_size = sys.getsizeof({})
    expected_size = sys.getsizeof(collection_list) + empty_list_size + empty_tuple_size + empty_dict_size

    assert expected_size == objsize.get_deep_size(collection_list)


def test_no_double_counting():
    rep = ["test1"]
    obj = [rep, rep]
    obj2 = [rep]
    expected_sz = objsize.get_deep_size(obj2) - sys.getsizeof(obj2) + sys.getsizeof(obj)
    assert expected_sz == objsize.get_deep_size(obj)


def test_gracefully_handles_self_referential_objects():
    class MyClass(object):
        pass

    obj = MyClass()
    obj.prop = obj
    assert objsize.get_deep_size(obj) == objsize.get_deep_size(obj.prop)


def test_string():
    some_test_string = "abc"
    assert sys.getsizeof(some_test_string) == objsize.get_deep_size(some_test_string)


def test_custom_class():
    class MyClass(object):
        def __init__(self, x, y):
            self.x = x
            self.y = y

    point = MyClass(3, 4)
    expected_size = calc_class_obj_sz(point) + sys.getsizeof(3) + sys.getsizeof(4)
    assert expected_size == objsize.get_deep_size(point)


def test_namedtuple():
    Point = namedtuple("Point", ["x", "y"])
    point = Point(3, 4)
    # namedtuple object does not contain a dict.
    expected_size = sys.getsizeof(point) + sys.getsizeof(3) + sys.getsizeof(4)
    assert expected_size == objsize.get_deep_size(point)


def test_subclass_of_namedtuple():
    class MyPoint(namedtuple("MyPoint", ["x", "y"])):
        pass

    point = MyPoint(3, 4)
    expected_size = sys.getsizeof(point) + sys.getsizeof(point.__dict__) + sys.getsizeof(3) + sys.getsizeof(4)
    assert expected_size == objsize.get_deep_size(point)


def test_subclass_of_namedtuple_with_slots():
    class MyPoint(namedtuple("MyPoint", ["x", "y"])):
        __slots__ = ()

    point = MyPoint(3, 4)
    # slot object does not contain a dict.
    expected_size = sys.getsizeof(point) + sys.getsizeof(3) + sys.getsizeof(4)
    assert expected_size == objsize.get_deep_size(point)


def test_slots():
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

    assert s1_sz == objsize.get_deep_size(s1)
    assert s2_sz == objsize.get_deep_size(s2)
    assert s3_sz == objsize.get_deep_size(s3)


def test_multi_obj():
    class MyClass(object):
        def __init__(self, x, y):
            self.x = x
            self.y = y

    strs = "hello world", "foo bar", "something else"
    objs = (
        MyClass(strs[0], strs[1]),
        MyClass(strs[0], strs[2]),
        MyClass(strs[1], strs[2]),
    )
    expected_sz = sum(map(sys.getsizeof, strs))

    expected_sz += sum(calc_class_obj_sz(o) for o in objs)

    assert expected_sz == objsize.get_deep_size(*objs)
    assert expected_sz == objsize.get_deep_size(*objs, *objs)
