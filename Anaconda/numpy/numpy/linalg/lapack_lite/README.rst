Regenerating lapack_lite source
===============================

:Author: David M. Cooke <cookedm@physics.mcmaster.ca>

The ``numpy/linalg/blas_lite.c``, ``numpy/linalg/dlapack_lite.c``, and
``numpy/linalg/zlapack_lite.c`` are ``f2c``'d versions of the LAPACK routines
required by the ``LinearAlgebra`` module, and wrapped by the ``lapack_lite``
module. The scripts in this directory can be used to create these files
automatically from a directory of LAPACK source files.

You'll need `plex 2.0.0dev`_, available from PyPI, installed to do the
appropriate scrubbing. As of writing, **this is only available for python 2.7**,
and is unlikely to ever be ported to python 3.

.. _plex 2.0.0dev: https://pypi.python.org/pypi/plex/

The routines that ``lapack_litemodule.c`` wraps are listed in
``wrapped_routines``, along with a few exceptions that aren't picked up
properly. Assuming that you have an unpacked LAPACK source tree in
``~/LAPACK``, you generate the new routines in a directory ``new-lite/`` with::

$ python2 ./make_lite.py wrapped_routines ~/LAPACK new-lite/

This will grab the right routines, with dependencies, put them into the
appropriate ``blas_lite.f``, ``dlapack_lite.f``, or ``zlapack_lite.f`` files,
run ``f2c`` over them, then do some scrubbing similar to that done to
generate the CLAPACK_ distribution.

.. _CLAPACK: http://netlib.org/clapack/index.html

The versions in Numeric CVS as of 2005-04-12 use the LAPACK source from the
`Debian package lapack3`_, version 3.0.20000531a-6. It was found that these
(being regularly maintained) worked better than the patches to the last
released version of LAPACK available at the LAPACK_ page.

.. _Debian package lapack3: http://packages.debian.org/unstable/libs/lapack3
.. _LAPACK: http://netlib.org/lapack/index.html

A slightly-patched ``f2c`` was used to add parentheses around ``||`` expressions
and the arguments to ``<<`` to silence gcc warnings. Edit
the ``src/output.c`` in the ``f2c`` source to do this.
