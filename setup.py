"""
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
from setuptools import setup

setup(
      name="objsize",
      version="0.1",
      py_modules=['objsize'],
      description="Calculates an object deep size",
      author="Liran Funaro",
      author_email="fonaro+objsize@gmail.com",
      url="https://github.com/fonaro/objsize",
      classifiers=[
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 3",
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Operating System :: OS Independent",
            "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      long_description=open('README.md').read(),
)
