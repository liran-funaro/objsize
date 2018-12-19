"""
Calculates the deep size of Python's objects.

Author: Liran Funaro <funaro@cs.technion.ac.il>

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
import gc
import sys


def get_deep_size(*objs, only_exclusive=False):
    """
    Calculates the deep size of all the arguments.

    :param objs: One or more object(s)
    :param only_exclusive: If True, then only calculate objects that are exclusive
        to this objects and/or its descendants.
    :return: The object's deep size
    """
    root_obj_ids = set(id(o) for o in objs)
    marked = set()
    sz = 0
    collected = []

    while objs:
        # Get the object's ids
        objs = ((id(o), o) for o in objs)

        # Filter:
        #  - Object that are already marked (using the marked set).
        #  - Type objects such as a class or a module as they are common among all objects.
        #  - Repeated objects (using dict notation).
        objs = {o_id: o for o_id, o in objs if o_id not in marked and not isinstance(o, type)}

        # Update the marked set with the ids so we will not traverse them again.
        marked.update(objs.keys())

        if only_exclusive:
            # Collect the objects
            collected.extend(objs.values())
        else:
            # Calculate each object size
            sz += sum(map(sys.getsizeof, objs.values()))

        # Lookup all the object referred to by the object from the current round.
        # See: https://docs.python.org/3.7/library/gc.html#gc.get_referents
        objs = gc.get_referents(*objs.values())

    if only_exclusive:
        # Test for each object that all the object that refer to it is in the marked set or is a root
        # See: https://docs.python.org/3.7/library/gc.html#gc.get_referrers

        # We add the collected list to the marked items because it referrers all our objects
        marked.add(id(collected))
        # We first make sure that any "old" objects were collected
        gc.collect()

        sz = sum(map(sys.getsizeof,
                     filter(lambda o: (id(o) in root_obj_ids) or (marked.issuperset(map(id, gc.get_referrers(o)))),
                            collected)))

    return sz
