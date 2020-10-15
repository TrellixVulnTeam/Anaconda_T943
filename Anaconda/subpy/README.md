<p align="center" style="padding: 20px">
<img src="https://raw.github.com/sdiehl/subpy/master/logo_sml.png">
</p>

Subpy
=====

Subpy is a library for defining subsets of the Python language
and querying ASTs for language-level properties that are
specified as sets of features.

Many projects aim to work with specific subsets of Python that
are amenable to *static analysis* and *type inference*, subpy is
simply a static analysis  library for checking for subsets with
the intention of providing more informative error reporting for
end-users.

Usage
-----

The input to the ``checker`` can be either a Module, Function or
source code as string. It returns a dictionary of lists keyed by
the ``feature`` enumeration code and the values with the line
numbers where the feature is detected. 

```python
>>> from subpy import checker
>>> import io

>>> print checker(io)

{3: [98],
 5: [78, 81, 84, 87],
 9: [78, 81, 84, 87],
 10: [81, 84, 87],
 32: [92, 96],
 34: [79]}
```

Matching the feature codes with the keys in the dictionary we see
the information this is telling us that in the ``io`` module in
the standard library:

* A *delete* is used on line 98.
* A *class* is used on line 78, 81, 84, and 87.
* *Inheritance* is used on line 78, 81, 84, and 87.
* *Multiple inheritance* is used on line 81, 84, and 87.
* A *custom iterator* is used on line 92 and 96.
* A *metaclass* is used on line 79.

A example using the function level checker:

```python
from subpy import checker
from subpy.features import ListComp

def example1():
    return [x**2 for x in range(25)]

def example2():
    return 'hello'

features = checker(example1)

if ListComp in features:
    print 'You used a list comprehension on lines %r' % (features[ListComp])

features = checker(example2)

if ListComp not in features:
    print 'You did not use any list comprehensions!'

```

Defining Subsets
----------------

For example if we want to exclude the use of *List Comprehensions*
and *Set Comprehensions* we could define a subset of Python that
excludes these features.

```python
MyPythonSubset = FullPython - { ListComp, SetComp }
```

The ``validator`` command can be used to raise when unsupported
features are detected in the given source. For example, we'll
support the python feature set excluding list comprehensions and
set comprehensions.

```python
from subpy import validator, FullPython, FeatureNotSupported
from subpy.features import ListComp, SetComp

def example():
    return [x**2 for x in range(25)]

my_features = FullPython - { ListComp, SetComp }

validator(example, features=my_features)
```

```python
  File "<stdin>", line 2
    return [x**2 for x in range(25)]
            ^
subpy.validate.FeatureNotSupported: ListComp
```

Subpy is currently able to parse the entire standard library and
can be used to query some interesting trivia facts.

```python
from subpy import detect
from subpy.stdlib import libraries
from subpy.features import Metaclasses, MInheritance, Exec

import importlib

print('Libraries with Multiple Inheritance and Metaclasses:')
for lib in libraries:
    mod = importlib.import_module(lib)
    features = detect(mod)

    if Metaclasses in features and MInheritance in features:
        print(lib)

```

```
Libraries with Multiple Inheritance and Metaclasses:
io
```

Or to query for potentially unsafe code execution:

```python
print('Libraries with Exec')
for lib in libraries:
    mod = importlib.import_module(lib)
    features = detect(mod)

    if Exec in features:
        print(lib)
```

```
Libraries with Exec
ihooks
site
cgi
rexec
Bastion
imputil
trace
timeit
cProfile
doctest
code
bdb
runpy
profile
collections
```

Feature Codes
-------------

Currently supported features are an enumeration with values given
below:

1. ImplicitCasts
1. Generators
1. DelVar
1. Closures
1. Classes
1. Decorators
1. VarArgs
1. KeywordArgs
1. Inheritance
1. MInheritance
1. ClassDecorators
1. Assertions
1. ChainComparison
1. Exceptions
1. Lambda
1. RelativeImports
1. ImportStar
1. HeteroList
1. Continue
1. MultipleReturn
1. DictComp
1. Ellipsi
1. TupleUnpacking
1. Exec
1. FancyIndexing
1. Globals
1. ContextManagers
1. GeneratorExp
1. Ternary
1. ListComp
1. SetComp
1. CustomIterators
1. Printing
1. Metaclasses

Testing
-------

To test run:

```bash
$ python -m unittest discover subpy/tests
```

Copying
-------

The core logic is self-contained in ``features.py`` and
``validate.py`` which will function as standalone modules without
subpy package, which includes the test suite. There are no
dependencies other than the standard library.

License
-------

Copyright (c) 2013, Continuum Analytics, Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
