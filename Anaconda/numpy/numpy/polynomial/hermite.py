"""
Objects for dealing with Hermite series.

This module provides a number of objects (mostly functions) useful for
dealing with Hermite series, including a `Hermite` class that
encapsulates the usual arithmetic operations.  (General information
on how this module represents and works with such polynomials is in the
docstring for its "parent" sub-package, `numpy.polynomial`).

Constants
---------
- `hermdomain` -- Hermite series default domain, [-1,1].
- `hermzero` -- Hermite series that evaluates identically to 0.
- `hermone` -- Hermite series that evaluates identically to 1.
- `hermx` -- Hermite series for the identity map, ``f(x) = x``.

Arithmetic
----------
- `hermmulx` -- multiply a Hermite series in ``P_i(x)`` by ``x``.
- `hermadd` -- add two Hermite series.
- `hermsub` -- subtract one Hermite series from another.
- `hermmul` -- multiply two Hermite series.
- `hermdiv` -- divide one Hermite series by another.
- `hermval` -- evaluate a Hermite series at given points.
- `hermval2d` -- evaluate a 2D Hermite series at given points.
- `hermval3d` -- evaluate a 3D Hermite series at given points.
- `hermgrid2d` -- evaluate a 2D Hermite series on a Cartesian product.
- `hermgrid3d` -- evaluate a 3D Hermite series on a Cartesian product.

Calculus
--------
- `hermder` -- differentiate a Hermite series.
- `hermint` -- integrate a Hermite series.

Misc Functions
--------------
- `hermfromroots` -- create a Hermite series with specified roots.
- `hermroots` -- find the roots of a Hermite series.
- `hermvander` -- Vandermonde-like matrix for Hermite polynomials.
- `hermvander2d` -- Vandermonde-like matrix for 2D power series.
- `hermvander3d` -- Vandermonde-like matrix for 3D power series.
- `hermgauss` -- Gauss-Hermite quadrature, points and weights.
- `hermweight` -- Hermite weight function.
- `hermcompanion` -- symmetrized companion matrix in Hermite form.
- `hermfit` -- least-squares fit returning a Hermite series.
- `hermtrim` -- trim leading coefficients from a Hermite series.
- `hermline` -- Hermite series of given straight line.
- `herm2poly` -- convert a Hermite series to a polynomial.
- `poly2herm` -- convert a polynomial to a Hermite series.

Classes
-------
- `Hermite` -- A Hermite series class.

See also
--------
`numpy.polynomial`

"""
from __future__ import division, absolute_import, print_function

import warnings
import numpy as np
import numpy.linalg as la

from . import polyutils as pu
from ._polybase import ABCPolyBase

__all__ = [
    'hermzero', 'hermone', 'hermx', 'hermdomain', 'hermline', 'hermadd',
    'hermsub', 'hermmulx', 'hermmul', 'hermdiv', 'hermpow', 'hermval',
    'hermder', 'hermint', 'herm2poly', 'poly2herm', 'hermfromroots',
    'hermvander', 'hermfit', 'hermtrim', 'hermroots', 'Hermite',
    'hermval2d', 'hermval3d', 'hermgrid2d', 'hermgrid3d', 'hermvander2d',
    'hermvander3d', 'hermcompanion', 'hermgauss', 'hermweight']

hermtrim = pu.trimcoef


def poly2herm(pol):
    """
    poly2herm(pol)

    Convert a polynomial to a Hermite series.

    Convert an array representing the coefficients of a polynomial (relative
    to the "standard" basis) ordered from lowest degree to highest, to an
    array of the coefficients of the equivalent Hermite series, ordered
    from lowest to highest degree.

    Parameters
    ----------
    pol : array_like
        1-D array containing the polynomial coefficients

    Returns
    -------
    c : ndarray
        1-D array containing the coefficients of the equivalent Hermite
        series.

    See Also
    --------
    herm2poly

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy.polynomial.hermite import poly2herm
    >>> poly2herm(np.arange(4))
    array([ 1.   ,  2.75 ,  0.5  ,  0.375])

    """
    [pol] = pu.as_series([pol])
    deg = len(pol) - 1
    res = 0
    for i in range(deg, -1, -1):
        res = hermadd(hermmulx(res), pol[i])
    return res


def herm2poly(c):
    """
    Convert a Hermite series to a polynomial.

    Convert an array representing the coefficients of a Hermite series,
    ordered from lowest degree to highest, to an array of the coefficients
    of the equivalent polynomial (relative to the "standard" basis) ordered
    from lowest to highest degree.

    Parameters
    ----------
    c : array_like
        1-D array containing the Hermite series coefficients, ordered
        from lowest order term to highest.

    Returns
    -------
    pol : ndarray
        1-D array containing the coefficients of the equivalent polynomial
        (relative to the "standard" basis) ordered from lowest order term
        to highest.

    See Also
    --------
    poly2herm

    Notes
    -----
    The easy way to do conversions between polynomial basis sets
    is to use the convert method of a class instance.

    Examples
    --------
    >>> from numpy.polynomial.hermite import herm2poly
    >>> herm2poly([ 1.   ,  2.75 ,  0.5  ,  0.375])
    array([ 0.,  1.,  2.,  3.])

    """
    from .polynomial import polyadd, polysub, polymulx

    [c] = pu.as_series([c])
    n = len(c)
    if n == 1:
        return c
    if n == 2:
        c[1] *= 2
        return c
    else:
        c0 = c[-2]
        c1 = c[-1]
        # i is the current degree of c1
        for i in range(n - 1, 1, -1):
            tmp = c0
            c0 = polysub(c[i - 2], c1*(2*(i - 1)))
            c1 = polyadd(tmp, polymulx(c1)*2)
        return polyadd(c0, polymulx(c1)*2)

#
# These are constant arrays are of integer type so as to be compatible
# with the widest range of other types, such as Decimal.
#

# Hermite
hermdomain = np.array([-1, 1])

# Hermite coefficients representing zero.
hermzero = np.array([0])

# Hermite coefficients representing one.
hermone = np.array([1])

# Hermite coefficients representing the identity x.
hermx = np.array([0, 1/2])


def hermline(off, scl):
    """
    Hermite series whose graph is a straight line.



    Parameters
    ----------
    off, scl : scalars
        The specified line is given by ``off + scl*x``.

    Returns
    -------
    y : ndarray
        This module's representation of the Hermite series for
        ``off + scl*x``.

    See Also
    --------
    polyline, chebline

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermline, hermval
    >>> hermval(0,hermline(3, 2))
    3.0
    >>> hermval(1,hermline(3, 2))
    5.0

    """
    if scl != 0:
        return np.array([off, scl/2])
    else:
        return np.array([off])


def hermfromroots(roots):
    """
    Generate a Hermite series with given roots.

    The function returns the coefficients of the polynomial

    .. math:: p(x) = (x - r_0) * (x - r_1) * ... * (x - r_n),

    in Hermite form, where the `r_n` are the roots specified in `roots`.
    If a zero has multiplicity n, then it must appear in `roots` n times.
    For instance, if 2 is a root of multiplicity three and 3 is a root of
    multiplicity 2, then `roots` looks something like [2, 2, 2, 3, 3]. The
    roots can appear in any order.

    If the returned coefficients are `c`, then

    .. math:: p(x) = c_0 + c_1 * H_1(x) + ... +  c_n * H_n(x)

    The coefficient of the last term is not generally 1 for monic
    polynomials in Hermite form.

    Parameters
    ----------
    roots : array_like
        Sequence containing the roots.

    Returns
    -------
    out : ndarray
        1-D array of coefficients.  If all roots are real then `out` is a
        real array, if some of the roots are complex, then `out` is complex
        even if all the coefficients in the result are real (see Examples
        below).

    See Also
    --------
    polyfromroots, legfromroots, lagfromroots, chebfromroots,
    hermefromroots.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermfromroots, hermval
    >>> coef = hermfromroots((-1, 0, 1))
    >>> hermval((-1, 0, 1), coef)
    array([ 0.,  0.,  0.])
    >>> coef = hermfromroots((-1j, 1j))
    >>> hermval((-1j, 1j), coef)
    array([ 0.+0.j,  0.+0.j])

    """
    if len(roots) == 0:
        return np.ones(1)
    else:
        [roots] = pu.as_series([roots], trim=False)
        roots.sort()
        p = [hermline(-r, 1) for r in roots]
        n = len(p)
        while n > 1:
            m, r = divmod(n, 2)
            tmp = [hermmul(p[i], p[i+m]) for i in range(m)]
            if r:
                tmp[0] = hermmul(tmp[0], p[-1])
            p = tmp
            n = m
        return p[0]


def hermadd(c1, c2):
    """
    Add one Hermite series to another.

    Returns the sum of two Hermite series `c1` + `c2`.  The arguments
    are sequences of coefficients ordered from lowest order term to
    highest, i.e., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the Hermite series of their sum.

    See Also
    --------
    hermsub, hermmul, hermdiv, hermpow

    Notes
    -----
    Unlike multiplication, division, etc., the sum of two Hermite series
    is a Hermite series (without having to "reproject" the result onto
    the basis set) so addition, just like that of "standard" polynomials,
    is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermadd
    >>> hermadd([1, 2, 3], [1, 2, 3, 4])
    array([ 2.,  4.,  6.,  4.])

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    if len(c1) > len(c2):
        c1[:c2.size] += c2
        ret = c1
    else:
        c2[:c1.size] += c1
        ret = c2
    return pu.trimseq(ret)


def hermsub(c1, c2):
    """
    Subtract one Hermite series from another.

    Returns the difference of two Hermite series `c1` - `c2`.  The
    sequences of coefficients are from lowest order term to highest, i.e.,
    [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Hermite series coefficients representing their difference.

    See Also
    --------
    hermadd, hermmul, hermdiv, hermpow

    Notes
    -----
    Unlike multiplication, division, etc., the difference of two Hermite
    series is a Hermite series (without having to "reproject" the result
    onto the basis set) so subtraction, just like that of "standard"
    polynomials, is simply "component-wise."

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermsub
    >>> hermsub([1, 2, 3, 4], [1, 2, 3])
    array([ 0.,  0.,  0.,  4.])

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    if len(c1) > len(c2):
        c1[:c2.size] -= c2
        ret = c1
    else:
        c2 = -c2
        c2[:c1.size] += c1
        ret = c2
    return pu.trimseq(ret)


def hermmulx(c):
    """Multiply a Hermite series by x.

    Multiply the Hermite series `c` by x, where x is the independent
    variable.


    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Array representing the result of the multiplication.

    Notes
    -----
    The multiplication uses the recursion relationship for Hermite
    polynomials in the form

    .. math::

    xP_i(x) = (P_{i + 1}(x)/2 + i*P_{i - 1}(x))

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermmulx
    >>> hermmulx([1, 2, 3])
    array([ 2. ,  6.5,  1. ,  1.5])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    # The zero series needs special treatment
    if len(c) == 1 and c[0] == 0:
        return c

    prd = np.empty(len(c) + 1, dtype=c.dtype)
    prd[0] = c[0]*0
    prd[1] = c[0]/2
    for i in range(1, len(c)):
        prd[i + 1] = c[i]/2
        prd[i - 1] += c[i]*i
    return prd


def hermmul(c1, c2):
    """
    Multiply one Hermite series by another.

    Returns the product of two Hermite series `c1` * `c2`.  The arguments
    are sequences of coefficients, from lowest order "term" to highest,
    e.g., [1,2,3] represents the series ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    out : ndarray
        Of Hermite series coefficients representing their product.

    See Also
    --------
    hermadd, hermsub, hermdiv, hermpow

    Notes
    -----
    In general, the (polynomial) product of two C-series results in terms
    that are not in the Hermite polynomial basis set.  Thus, to express
    the product as a Hermite series, it is necessary to "reproject" the
    product onto said basis set, which may produce "unintuitive" (but
    correct) results; see Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermmul
    >>> hermmul([1, 2, 3], [0, 1, 2])
    array([ 52.,  29.,  52.,   7.,   6.])

    """
    # s1, s2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])

    if len(c1) > len(c2):
        c = c2
        xs = c1
    else:
        c = c1
        xs = c2

    if len(c) == 1:
        c0 = c[0]*xs
        c1 = 0
    elif len(c) == 2:
        c0 = c[0]*xs
        c1 = c[1]*xs
    else:
        nd = len(c)
        c0 = c[-2]*xs
        c1 = c[-1]*xs
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = hermsub(c[-i]*xs, c1*(2*(nd - 1)))
            c1 = hermadd(tmp, hermmulx(c1)*2)
    return hermadd(c0, hermmulx(c1)*2)


def hermdiv(c1, c2):
    """
    Divide one Hermite series by another.

    Returns the quotient-with-remainder of two Hermite series
    `c1` / `c2`.  The arguments are sequences of coefficients from lowest
    order "term" to highest, e.g., [1,2,3] represents the series
    ``P_0 + 2*P_1 + 3*P_2``.

    Parameters
    ----------
    c1, c2 : array_like
        1-D arrays of Hermite series coefficients ordered from low to
        high.

    Returns
    -------
    [quo, rem] : ndarrays
        Of Hermite series coefficients representing the quotient and
        remainder.

    See Also
    --------
    hermadd, hermsub, hermmul, hermpow

    Notes
    -----
    In general, the (polynomial) division of one Hermite series by another
    results in quotient and remainder terms that are not in the Hermite
    polynomial basis set.  Thus, to express these results as a Hermite
    series, it is necessary to "reproject" the results onto the Hermite
    basis set, which may produce "unintuitive" (but correct) results; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermdiv
    >>> hermdiv([ 52.,  29.,  52.,   7.,   6.], [0, 1, 2])
    (array([ 1.,  2.,  3.]), array([ 0.]))
    >>> hermdiv([ 54.,  31.,  52.,   7.,   6.], [0, 1, 2])
    (array([ 1.,  2.,  3.]), array([ 2.,  2.]))
    >>> hermdiv([ 53.,  30.,  52.,   7.,   6.], [0, 1, 2])
    (array([ 1.,  2.,  3.]), array([ 1.,  1.]))

    """
    # c1, c2 are trimmed copies
    [c1, c2] = pu.as_series([c1, c2])
    if c2[-1] == 0:
        raise ZeroDivisionError()

    lc1 = len(c1)
    lc2 = len(c2)
    if lc1 < lc2:
        return c1[:1]*0, c1
    elif lc2 == 1:
        return c1/c2[-1], c1[:1]*0
    else:
        quo = np.empty(lc1 - lc2 + 1, dtype=c1.dtype)
        rem = c1
        for i in range(lc1 - lc2, - 1, -1):
            p = hermmul([0]*i + [1], c2)
            q = rem[-1]/p[-1]
            rem = rem[:-1] - q*p[:-1]
            quo[i] = q
        return quo, pu.trimseq(rem)


def hermpow(c, pow, maxpower=16):
    """Raise a Hermite series to a power.

    Returns the Hermite series `c` raised to the power `pow`. The
    argument `c` is a sequence of coefficients ordered from low to high.
    i.e., [1,2,3] is the series  ``P_0 + 2*P_1 + 3*P_2.``

    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to
        high.
    pow : integer
        Power to which the series will be raised
    maxpower : integer, optional
        Maximum power allowed. This is mainly to limit growth of the series
        to unmanageable size. Default is 16

    Returns
    -------
    coef : ndarray
        Hermite series of power.

    See Also
    --------
    hermadd, hermsub, hermmul, hermdiv

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermpow
    >>> hermpow([1, 2, 3], 2)
    array([ 81.,  52.,  82.,  12.,   9.])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    power = int(pow)
    if power != pow or power < 0:
        raise ValueError("Power must be a non-negative integer.")
    elif maxpower is not None and power > maxpower:
        raise ValueError("Power is too large")
    elif power == 0:
        return np.array([1], dtype=c.dtype)
    elif power == 1:
        return c
    else:
        # This can be made more efficient by using powers of two
        # in the usual way.
        prd = c
        for i in range(2, power + 1):
            prd = hermmul(prd, c)
        return prd


def hermder(c, m=1, scl=1, axis=0):
    """
    Differentiate a Hermite series.

    Returns the Hermite series coefficients `c` differentiated `m` times
    along `axis`.  At each iteration the result is multiplied by `scl` (the
    scaling factor is for use in a linear change of variable). The argument
    `c` is an array of coefficients from low to high degree along each
    axis, e.g., [1,2,3] represents the series ``1*H_0 + 2*H_1 + 3*H_2``
    while [[1,2],[1,2]] represents ``1*H_0(x)*H_0(y) + 1*H_1(x)*H_0(y) +
    2*H_0(x)*H_1(y) + 2*H_1(x)*H_1(y)`` if axis=0 is ``x`` and axis=1 is
    ``y``.

    Parameters
    ----------
    c : array_like
        Array of Hermite series coefficients. If `c` is multidimensional the
        different axis correspond to different variables with the degree in
        each axis given by the corresponding index.
    m : int, optional
        Number of derivatives taken, must be non-negative. (Default: 1)
    scl : scalar, optional
        Each differentiation is multiplied by `scl`.  The end result is
        multiplication by ``scl**m``.  This is for use in a linear change of
        variable. (Default: 1)
    axis : int, optional
        Axis over which the derivative is taken. (Default: 0).

        .. versionadded:: 1.7.0

    Returns
    -------
    der : ndarray
        Hermite series of the derivative.

    See Also
    --------
    hermint

    Notes
    -----
    In general, the result of differentiating a Hermite series does not
    resemble the same operation on a power series. Thus the result of this
    function may be "unintuitive," albeit correct; see Examples section
    below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermder
    >>> hermder([ 1. ,  0.5,  0.5,  0.5])
    array([ 1.,  2.,  3.])
    >>> hermder([-0.5,  1./2.,  1./8.,  1./12.,  1./16.], m=2)
    array([ 1.,  2.,  3.])

    """
    c = np.array(c, ndmin=1, copy=1)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    cnt, iaxis = [int(t) for t in [m, axis]]

    if cnt != m:
        raise ValueError("The order of derivation must be integer")
    if cnt < 0:
        raise ValueError("The order of derivation must be non-negative")
    if iaxis != axis:
        raise ValueError("The axis must be integer")
    if not -c.ndim <= iaxis < c.ndim:
        raise ValueError("The axis is out of range")
    if iaxis < 0:
        iaxis += c.ndim

    if cnt == 0:
        return c

    c = np.rollaxis(c, iaxis)
    n = len(c)
    if cnt >= n:
        c = c[:1]*0
    else:
        for i in range(cnt):
            n = n - 1
            c *= scl
            der = np.empty((n,) + c.shape[1:], dtype=c.dtype)
            for j in range(n, 0, -1):
                der[j - 1] = (2*j)*c[j]
            c = der
    c = np.rollaxis(c, 0, iaxis + 1)
    return c


def hermint(c, m=1, k=[], lbnd=0, scl=1, axis=0):
    """
    Integrate a Hermite series.

    Returns the Hermite series coefficients `c` integrated `m` times from
    `lbnd` along `axis`. At each iteration the resulting series is
    **multiplied** by `scl` and an integration constant, `k`, is added.
    The scaling factor is for use in a linear change of variable.  ("Buyer
    beware": note that, depending on what one is doing, one may want `scl`
    to be the reciprocal of what one might expect; for more information,
    see the Notes section below.)  The argument `c` is an array of
    coefficients from low to high degree along each axis, e.g., [1,2,3]
    represents the series ``H_0 + 2*H_1 + 3*H_2`` while [[1,2],[1,2]]
    represents ``1*H_0(x)*H_0(y) + 1*H_1(x)*H_0(y) + 2*H_0(x)*H_1(y) +
    2*H_1(x)*H_1(y)`` if axis=0 is ``x`` and axis=1 is ``y``.

    Parameters
    ----------
    c : array_like
        Array of Hermite series coefficients. If c is multidimensional the
        different axis correspond to different variables with the degree in
        each axis given by the corresponding index.
    m : int, optional
        Order of integration, must be positive. (Default: 1)
    k : {[], list, scalar}, optional
        Integration constant(s).  The value of the first integral at
        ``lbnd`` is the first value in the list, the value of the second
        integral at ``lbnd`` is the second value, etc.  If ``k == []`` (the
        default), all constants are set to zero.  If ``m == 1``, a single
        scalar can be given instead of a list.
    lbnd : scalar, optional
        The lower bound of the integral. (Default: 0)
    scl : scalar, optional
        Following each integration the result is *multiplied* by `scl`
        before the integration constant is added. (Default: 1)
    axis : int, optional
        Axis over which the integral is taken. (Default: 0).

        .. versionadded:: 1.7.0

    Returns
    -------
    S : ndarray
        Hermite series coefficients of the integral.

    Raises
    ------
    ValueError
        If ``m < 0``, ``len(k) > m``, ``np.isscalar(lbnd) == False``, or
        ``np.isscalar(scl) == False``.

    See Also
    --------
    hermder

    Notes
    -----
    Note that the result of each integration is *multiplied* by `scl`.
    Why is this important to note?  Say one is making a linear change of
    variable :math:`u = ax + b` in an integral relative to `x`.  Then
    .. math::`dx = du/a`, so one will need to set `scl` equal to
    :math:`1/a` - perhaps not what one would have first thought.

    Also note that, in general, the result of integrating a C-series needs
    to be "reprojected" onto the C-series basis set.  Thus, typically,
    the result of this function is "unintuitive," albeit correct; see
    Examples section below.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermint
    >>> hermint([1,2,3]) # integrate once, value 0 at 0.
    array([ 1. ,  0.5,  0.5,  0.5])
    >>> hermint([1,2,3], m=2) # integrate twice, value & deriv 0 at 0
    array([-0.5       ,  0.5       ,  0.125     ,  0.08333333,  0.0625    ])
    >>> hermint([1,2,3], k=1) # integrate once, value 1 at 0.
    array([ 2. ,  0.5,  0.5,  0.5])
    >>> hermint([1,2,3], lbnd=-1) # integrate once, value 0 at -1
    array([-2. ,  0.5,  0.5,  0.5])
    >>> hermint([1,2,3], m=2, k=[1,2], lbnd=-1)
    array([ 1.66666667, -0.5       ,  0.125     ,  0.08333333,  0.0625    ])

    """
    c = np.array(c, ndmin=1, copy=1)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if not np.iterable(k):
        k = [k]
    cnt, iaxis = [int(t) for t in [m, axis]]

    if cnt != m:
        raise ValueError("The order of integration must be integer")
    if cnt < 0:
        raise ValueError("The order of integration must be non-negative")
    if len(k) > cnt:
        raise ValueError("Too many integration constants")
    if iaxis != axis:
        raise ValueError("The axis must be integer")
    if not -c.ndim <= iaxis < c.ndim:
        raise ValueError("The axis is out of range")
    if iaxis < 0:
        iaxis += c.ndim

    if cnt == 0:
        return c

    c = np.rollaxis(c, iaxis)
    k = list(k) + [0]*(cnt - len(k))
    for i in range(cnt):
        n = len(c)
        c *= scl
        if n == 1 and np.all(c[0] == 0):
            c[0] += k[i]
        else:
            tmp = np.empty((n + 1,) + c.shape[1:], dtype=c.dtype)
            tmp[0] = c[0]*0
            tmp[1] = c[0]/2
            for j in range(1, n):
                tmp[j + 1] = c[j]/(2*(j + 1))
            tmp[0] += k[i] - hermval(lbnd, tmp)
            c = tmp
    c = np.rollaxis(c, 0, iaxis + 1)
    return c


def hermval(x, c, tensor=True):
    """
    Evaluate an Hermite series at points x.

    If `c` is of length `n + 1`, this function returns the value:

    .. math:: p(x) = c_0 * H_0(x) + c_1 * H_1(x) + ... + c_n * H_n(x)

    The parameter `x` is converted to an array only if it is a tuple or a
    list, otherwise it is treated as a scalar. In either case, either `x`
    or its elements must support multiplication and addition both with
    themselves and with the elements of `c`.

    If `c` is a 1-D array, then `p(x)` will have the same shape as `x`.  If
    `c` is multidimensional, then the shape of the result depends on the
    value of `tensor`. If `tensor` is true the shape will be c.shape[1:] +
    x.shape. If `tensor` is false the shape will be c.shape[1:]. Note that
    scalars have shape (,).

    Trailing zeros in the coefficients will be used in the evaluation, so
    they should be avoided if efficiency is a concern.

    Parameters
    ----------
    x : array_like, compatible object
        If `x` is a list or tuple, it is converted to an ndarray, otherwise
        it is left unchanged and treated as a scalar. In either case, `x`
        or its elements must support addition and multiplication with
        with themselves and with the elements of `c`.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree n are contained in c[n]. If `c` is multidimensional the
        remaining indices enumerate multiple polynomials. In the two
        dimensional case the coefficients may be thought of as stored in
        the columns of `c`.
    tensor : boolean, optional
        If True, the shape of the coefficient array is extended with ones
        on the right, one for each dimension of `x`. Scalars have dimension 0
        for this action. The result is that every column of coefficients in
        `c` is evaluated for every element of `x`. If False, `x` is broadcast
        over the columns of `c` for the evaluation.  This keyword is useful
        when `c` is multidimensional. The default value is True.

        .. versionadded:: 1.7.0

    Returns
    -------
    values : ndarray, algebra_like
        The shape of the return value is described above.

    See Also
    --------
    hermval2d, hermgrid2d, hermval3d, hermgrid3d

    Notes
    -----
    The evaluation uses Clenshaw recursion, aka synthetic division.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermval
    >>> coef = [1,2,3]
    >>> hermval(1, coef)
    11.0
    >>> hermval([[1,2],[3,4]], coef)
    array([[  11.,   51.],
           [ 115.,  203.]])

    """
    c = np.array(c, ndmin=1, copy=0)
    if c.dtype.char in '?bBhHiIlLqQpP':
        c = c.astype(np.double)
    if isinstance(x, (tuple, list)):
        x = np.asarray(x)
    if isinstance(x, np.ndarray) and tensor:
        c = c.reshape(c.shape + (1,)*x.ndim)

    x2 = x*2
    if len(c) == 1:
        c0 = c[0]
        c1 = 0
    elif len(c) == 2:
        c0 = c[0]
        c1 = c[1]
    else:
        nd = len(c)
        c0 = c[-2]
        c1 = c[-1]
        for i in range(3, len(c) + 1):
            tmp = c0
            nd = nd - 1
            c0 = c[-i] - c1*(2*(nd - 1))
            c1 = tmp + c1*x2
    return c0 + c1*x2


def hermval2d(x, y, c):
    """
    Evaluate a 2-D Hermite series at points (x, y).

    This function returns the values:

    .. math:: p(x,y) = \\sum_{i,j} c_{i,j} * H_i(x) * H_j(y)

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars and they
    must have the same shape after conversion. In either case, either `x`
    and `y` or their elements must support multiplication and addition both
    with themselves and with the elements of `c`.

    If `c` is a 1-D array a one is implicitly appended to its shape to make
    it 2-D. The shape of the result will be c.shape[2:] + x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points `(x, y)`,
        where `x` and `y` must have the same shape. If `x` or `y` is a list
        or tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and if it isn't an ndarray it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term
        of multi-degree i,j is contained in ``c[i,j]``. If `c` has
        dimension greater than two the remaining indices enumerate multiple
        sets of coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points formed with
        pairs of corresponding values from `x` and `y`.

    See Also
    --------
    hermval, hermgrid2d, hermval3d, hermgrid3d

    Notes
    -----

    .. versionadded::1.7.0

    """
    try:
        x, y = np.array((x, y), copy=0)
    except:
        raise ValueError('x, y are incompatible')

    c = hermval(x, c)
    c = hermval(y, c, tensor=False)
    return c


def hermgrid2d(x, y, c):
    """
    Evaluate a 2-D Hermite series on the Cartesian product of x and y.

    This function returns the values:

    .. math:: p(a,b) = \\sum_{i,j} c_{i,j} * H_i(a) * H_j(b)

    where the points `(a, b)` consist of all pairs formed by taking
    `a` from `x` and `b` from `y`. The resulting points form a grid with
    `x` in the first dimension and `y` in the second.

    The parameters `x` and `y` are converted to arrays only if they are
    tuples or a lists, otherwise they are treated as a scalars. In either
    case, either `x` and `y` or their elements must support multiplication
    and addition both with themselves and with the elements of `c`.

    If `c` has fewer than two dimensions, ones are implicitly appended to
    its shape to make it 2-D. The shape of the result will be c.shape[2:] +
    x.shape.

    Parameters
    ----------
    x, y : array_like, compatible objects
        The two dimensional series is evaluated at the points in the
        Cartesian product of `x` and `y`.  If `x` or `y` is a list or
        tuple, it is first converted to an ndarray, otherwise it is left
        unchanged and, if it isn't an ndarray, it is treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    hermval, hermval2d, hermval3d, hermgrid3d

    Notes
    -----

    .. versionadded::1.7.0

    """
    c = hermval(x, c)
    c = hermval(y, c)
    return c


def hermval3d(x, y, z, c):
    """
    Evaluate a 3-D Hermite series at points (x, y, z).

    This function returns the values:

    .. math:: p(x,y,z) = \\sum_{i,j,k} c_{i,j,k} * H_i(x) * H_j(y) * H_k(z)

    The parameters `x`, `y`, and `z` are converted to arrays only if
    they are tuples or a lists, otherwise they are treated as a scalars and
    they must have the same shape after conversion. In either case, either
    `x`, `y`, and `z` or their elements must support multiplication and
    addition both with themselves and with the elements of `c`.

    If `c` has fewer than 3 dimensions, ones are implicitly appended to its
    shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible object
        The three dimensional series is evaluated at the points
        `(x, y, z)`, where `x`, `y`, and `z` must have the same shape.  If
        any of `x`, `y`, or `z` is a list or tuple, it is first converted
        to an ndarray, otherwise it is left unchanged and if it isn't an
        ndarray it is  treated as a scalar.
    c : array_like
        Array of coefficients ordered so that the coefficient of the term of
        multi-degree i,j,k is contained in ``c[i,j,k]``. If `c` has dimension
        greater than 3 the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the multidimensional polynomial on points formed with
        triples of corresponding values from `x`, `y`, and `z`.

    See Also
    --------
    hermval, hermval2d, hermgrid2d, hermgrid3d

    Notes
    -----

    .. versionadded::1.7.0

    """
    try:
        x, y, z = np.array((x, y, z), copy=0)
    except:
        raise ValueError('x, y, z are incompatible')

    c = hermval(x, c)
    c = hermval(y, c, tensor=False)
    c = hermval(z, c, tensor=False)
    return c


def hermgrid3d(x, y, z, c):
    """
    Evaluate a 3-D Hermite series on the Cartesian product of x, y, and z.

    This function returns the values:

    .. math:: p(a,b,c) = \\sum_{i,j,k} c_{i,j,k} * H_i(a) * H_j(b) * H_k(c)

    where the points `(a, b, c)` consist of all triples formed by taking
    `a` from `x`, `b` from `y`, and `c` from `z`. The resulting points form
    a grid with `x` in the first dimension, `y` in the second, and `z` in
    the third.

    The parameters `x`, `y`, and `z` are converted to arrays only if they
    are tuples or a lists, otherwise they are treated as a scalars. In
    either case, either `x`, `y`, and `z` or their elements must support
    multiplication and addition both with themselves and with the elements
    of `c`.

    If `c` has fewer than three dimensions, ones are implicitly appended to
    its shape to make it 3-D. The shape of the result will be c.shape[3:] +
    x.shape + y.shape + z.shape.

    Parameters
    ----------
    x, y, z : array_like, compatible objects
        The three dimensional series is evaluated at the points in the
        Cartesian product of `x`, `y`, and `z`.  If `x`,`y`, or `z` is a
        list or tuple, it is first converted to an ndarray, otherwise it is
        left unchanged and, if it isn't an ndarray, it is treated as a
        scalar.
    c : array_like
        Array of coefficients ordered so that the coefficients for terms of
        degree i,j are contained in ``c[i,j]``. If `c` has dimension
        greater than two the remaining indices enumerate multiple sets of
        coefficients.

    Returns
    -------
    values : ndarray, compatible object
        The values of the two dimensional polynomial at points in the Cartesian
        product of `x` and `y`.

    See Also
    --------
    hermval, hermval2d, hermgrid2d, hermval3d

    Notes
    -----

    .. versionadded::1.7.0

    """
    c = hermval(x, c)
    c = hermval(y, c)
    c = hermval(z, c)
    return c


def hermvander(x, deg):
    """Pseudo-Vandermonde matrix of given degree.

    Returns the pseudo-Vandermonde matrix of degree `deg` and sample points
    `x`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., i] = H_i(x),

    where `0 <= i <= deg`. The leading indices of `V` index the elements of
    `x` and the last index is the degree of the Hermite polynomial.

    If `c` is a 1-D array of coefficients of length `n + 1` and `V` is the
    array ``V = hermvander(x, n)``, then ``np.dot(V, c)`` and
    ``hermval(x, c)`` are the same up to roundoff. This equivalence is
    useful both for least squares fitting and for the evaluation of a large
    number of Hermite series of the same degree and sample points.

    Parameters
    ----------
    x : array_like
        Array of points. The dtype is converted to float64 or complex128
        depending on whether any of the elements are complex. If `x` is
        scalar it is converted to a 1-D array.
    deg : int
        Degree of the resulting matrix.

    Returns
    -------
    vander : ndarray
        The pseudo-Vandermonde matrix. The shape of the returned matrix is
        ``x.shape + (deg + 1,)``, where The last index is the degree of the
        corresponding Hermite polynomial.  The dtype will be the same as
        the converted `x`.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermvander
    >>> x = np.array([-1, 0, 1])
    >>> hermvander(x, 3)
    array([[ 1., -2.,  2.,  4.],
           [ 1.,  0., -2., -0.],
           [ 1.,  2.,  2., -4.]])

    """
    ideg = int(deg)
    if ideg != deg:
        raise ValueError("deg must be integer")
    if ideg < 0:
        raise ValueError("deg must be non-negative")

    x = np.array(x, copy=0, ndmin=1) + 0.0
    dims = (ideg + 1,) + x.shape
    dtyp = x.dtype
    v = np.empty(dims, dtype=dtyp)
    v[0] = x*0 + 1
    if ideg > 0:
        x2 = x*2
        v[1] = x2
        for i in range(2, ideg + 1):
            v[i] = (v[i-1]*x2 - v[i-2]*(2*(i - 1)))
    return np.rollaxis(v, 0, v.ndim)


def hermvander2d(x, y, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points `(x, y)`. The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., deg[1]*i + j] = H_i(x) * H_j(y),

    where `0 <= i <= deg[0]` and `0 <= j <= deg[1]`. The leading indices of
    `V` index the points `(x, y)` and the last index encodes the degrees of
    the Hermite polynomials.

    If ``V = hermvander2d(x, y, [xdeg, ydeg])``, then the columns of `V`
    correspond to the elements of a 2-D coefficient array `c` of shape
    (xdeg + 1, ydeg + 1) in the order

    .. math:: c_{00}, c_{01}, c_{02} ... , c_{10}, c_{11}, c_{12} ...

    and ``np.dot(V, c.flat)`` and ``hermval2d(x, y, c)`` will be the same
    up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 2-D Hermite
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y : array_like
        Arrays of point coordinates, all of the same shape. The dtypes
        will be converted to either float64 or complex128 depending on
        whether any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg].

    Returns
    -------
    vander2d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg([1]+1)`.  The dtype will be the same
        as the converted `x` and `y`.

    See Also
    --------
    hermvander, hermvander3d. hermval2d, hermval3d

    Notes
    -----

    .. versionadded::1.7.0

    """
    ideg = [int(d) for d in deg]
    is_valid = [id == d and id >= 0 for id, d in zip(ideg, deg)]
    if is_valid != [1, 1]:
        raise ValueError("degrees must be non-negative integers")
    degx, degy = ideg
    x, y = np.array((x, y), copy=0) + 0.0

    vx = hermvander(x, degx)
    vy = hermvander(y, degy)
    v = vx[..., None]*vy[..., None,:]
    return v.reshape(v.shape[:-2] + (-1,))


def hermvander3d(x, y, z, deg):
    """Pseudo-Vandermonde matrix of given degrees.

    Returns the pseudo-Vandermonde matrix of degrees `deg` and sample
    points `(x, y, z)`. If `l, m, n` are the given degrees in `x, y, z`,
    then The pseudo-Vandermonde matrix is defined by

    .. math:: V[..., (m+1)(n+1)i + (n+1)j + k] = H_i(x)*H_j(y)*H_k(z),

    where `0 <= i <= l`, `0 <= j <= m`, and `0 <= j <= n`.  The leading
    indices of `V` index the points `(x, y, z)` and the last index encodes
    the degrees of the Hermite polynomials.

    If ``V = hermvander3d(x, y, z, [xdeg, ydeg, zdeg])``, then the columns
    of `V` correspond to the elements of a 3-D coefficient array `c` of
    shape (xdeg + 1, ydeg + 1, zdeg + 1) in the order

    .. math:: c_{000}, c_{001}, c_{002},... , c_{010}, c_{011}, c_{012},...

    and  ``np.dot(V, c.flat)`` and ``hermval3d(x, y, z, c)`` will be the
    same up to roundoff. This equivalence is useful both for least squares
    fitting and for the evaluation of a large number of 3-D Hermite
    series of the same degrees and sample points.

    Parameters
    ----------
    x, y, z : array_like
        Arrays of point coordinates, all of the same shape. The dtypes will
        be converted to either float64 or complex128 depending on whether
        any of the elements are complex. Scalars are converted to 1-D
        arrays.
    deg : list of ints
        List of maximum degrees of the form [x_deg, y_deg, z_deg].

    Returns
    -------
    vander3d : ndarray
        The shape of the returned matrix is ``x.shape + (order,)``, where
        :math:`order = (deg[0]+1)*(deg([1]+1)*(deg[2]+1)`.  The dtype will
        be the same as the converted `x`, `y`, and `z`.

    See Also
    --------
    hermvander, hermvander3d. hermval2d, hermval3d

    Notes
    -----

    .. versionadded::1.7.0

    """
    ideg = [int(d) for d in deg]
    is_valid = [id == d and id >= 0 for id, d in zip(ideg, deg)]
    if is_valid != [1, 1, 1]:
        raise ValueError("degrees must be non-negative integers")
    degx, degy, degz = ideg
    x, y, z = np.array((x, y, z), copy=0) + 0.0

    vx = hermvander(x, degx)
    vy = hermvander(y, degy)
    vz = hermvander(z, degz)
    v = vx[..., None, None]*vy[..., None,:, None]*vz[..., None, None,:]
    return v.reshape(v.shape[:-3] + (-1,))


def hermfit(x, y, deg, rcond=None, full=False, w=None):
    """
    Least squares fit of Hermite series to data.

    Return the coefficients of a Hermite series of degree `deg` that is the
    least squares fit to the data values `y` given at points `x`. If `y` is
    1-D the returned coefficients will also be 1-D. If `y` is 2-D multiple
    fits are done, one for each column of `y`, and the resulting
    coefficients are stored in the corresponding columns of a 2-D return.
    The fitted polynomial(s) are in the form

    .. math::  p(x) = c_0 + c_1 * H_1(x) + ... + c_n * H_n(x),

    where `n` is `deg`.

    Parameters
    ----------
    x : array_like, shape (M,)
        x-coordinates of the M sample points ``(x[i], y[i])``.
    y : array_like, shape (M,) or (M, K)
        y-coordinates of the sample points. Several data sets of sample
        points sharing the same x-coordinates can be fitted at once by
        passing in a 2D-array that contains one dataset per column.
    deg : int or 1-D array_like
        Degree(s) of the fitting polynomials. If `deg` is a single integer
        all terms up to and including the `deg`'th term are included in the
        fit. For NumPy versions >= 1.11.0 a list of integers specifying the
        degrees of the terms to include may be used instead.
    rcond : float, optional
        Relative condition number of the fit. Singular values smaller than
        this relative to the largest singular value will be ignored. The
        default value is len(x)*eps, where eps is the relative precision of
        the float type, about 2e-16 in most cases.
    full : bool, optional
        Switch determining nature of return value. When it is False (the
        default) just the coefficients are returned, when True diagnostic
        information from the singular value decomposition is also returned.
    w : array_like, shape (`M`,), optional
        Weights. If not None, the contribution of each point
        ``(x[i],y[i])`` to the fit is weighted by `w[i]`. Ideally the
        weights are chosen so that the errors of the products ``w[i]*y[i]``
        all have the same variance.  The default value is None.

    Returns
    -------
    coef : ndarray, shape (M,) or (M, K)
        Hermite coefficients ordered from low to high. If `y` was 2-D,
        the coefficients for the data in column k  of `y` are in column
        `k`.

    [residuals, rank, singular_values, rcond] : list
        These values are only returned if `full` = True

        resid -- sum of squared residuals of the least squares fit
        rank -- the numerical rank of the scaled Vandermonde matrix
        sv -- singular values of the scaled Vandermonde matrix
        rcond -- value of `rcond`.

        For more details, see `linalg.lstsq`.

    Warns
    -----
    RankWarning
        The rank of the coefficient matrix in the least-squares fit is
        deficient. The warning is only raised if `full` = False.  The
        warnings can be turned off by

        >>> import warnings
        >>> warnings.simplefilter('ignore', RankWarning)

    See Also
    --------
    chebfit, legfit, lagfit, polyfit, hermefit
    hermval : Evaluates a Hermite series.
    hermvander : Vandermonde matrix of Hermite series.
    hermweight : Hermite weight function
    linalg.lstsq : Computes a least-squares fit from the matrix.
    scipy.interpolate.UnivariateSpline : Computes spline fits.

    Notes
    -----
    The solution is the coefficients of the Hermite series `p` that
    minimizes the sum of the weighted squared errors

    .. math:: E = \\sum_j w_j^2 * |y_j - p(x_j)|^2,

    where the :math:`w_j` are the weights. This problem is solved by
    setting up the (typically) overdetermined matrix equation

    .. math:: V(x) * c = w * y,

    where `V` is the weighted pseudo Vandermonde matrix of `x`, `c` are the
    coefficients to be solved for, `w` are the weights, `y` are the
    observed values.  This equation is then solved using the singular value
    decomposition of `V`.

    If some of the singular values of `V` are so small that they are
    neglected, then a `RankWarning` will be issued. This means that the
    coefficient values may be poorly determined. Using a lower order fit
    will usually get rid of the warning.  The `rcond` parameter can also be
    set to a value smaller than its default, but the resulting fit may be
    spurious and have large contributions from roundoff error.

    Fits using Hermite series are probably most useful when the data can be
    approximated by ``sqrt(w(x)) * p(x)``, where `w(x)` is the Hermite
    weight. In that case the weight ``sqrt(w(x[i])`` should be used
    together with data values ``y[i]/sqrt(w(x[i])``. The weight function is
    available as `hermweight`.

    References
    ----------
    .. [1] Wikipedia, "Curve fitting",
           http://en.wikipedia.org/wiki/Curve_fitting

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermfit, hermval
    >>> x = np.linspace(-10, 10)
    >>> err = np.random.randn(len(x))/10
    >>> y = hermval(x, [1, 2, 3]) + err
    >>> hermfit(x, y, 2)
    array([ 0.97902637,  1.99849131,  3.00006   ])

    """
    x = np.asarray(x) + 0.0
    y = np.asarray(y) + 0.0
    deg = np.asarray(deg)

    # check arguments.
    if deg.ndim > 1 or deg.dtype.kind not in 'iu' or deg.size == 0:
        raise TypeError("deg must be an int or non-empty 1-D array of int")
    if deg.min() < 0:
        raise ValueError("expected deg >= 0")
    if x.ndim != 1:
        raise TypeError("expected 1D vector for x")
    if x.size == 0:
        raise TypeError("expected non-empty vector for x")
    if y.ndim < 1 or y.ndim > 2:
        raise TypeError("expected 1D or 2D array for y")
    if len(x) != len(y):
        raise TypeError("expected x and y to have same length")

    if deg.ndim == 0:
        lmax = deg
        order = lmax + 1
        van = hermvander(x, lmax)
    else:
        deg = np.sort(deg)
        lmax = deg[-1]
        order = len(deg)
        van = hermvander(x, lmax)[:, deg]

    # set up the least squares matrices in transposed form
    lhs = van.T
    rhs = y.T
    if w is not None:
        w = np.asarray(w) + 0.0
        if w.ndim != 1:
            raise TypeError("expected 1D vector for w")
        if len(x) != len(w):
            raise TypeError("expected x and w to have same length")
        # apply weights. Don't use inplace operations as they
        # can cause problems with NA.
        lhs = lhs * w
        rhs = rhs * w

    # set rcond
    if rcond is None:
        rcond = len(x)*np.finfo(x.dtype).eps

    # Determine the norms of the design matrix columns.
    if issubclass(lhs.dtype.type, np.complexfloating):
        scl = np.sqrt((np.square(lhs.real) + np.square(lhs.imag)).sum(1))
    else:
        scl = np.sqrt(np.square(lhs).sum(1))
    scl[scl == 0] = 1

    # Solve the least squares problem.
    c, resids, rank, s = la.lstsq(lhs.T/scl, rhs.T, rcond)
    c = (c.T/scl).T

    # Expand c to include non-fitted coefficients which are set to zero
    if deg.ndim > 0:
        if c.ndim == 2:
            cc = np.zeros((lmax+1, c.shape[1]), dtype=c.dtype)
        else:
            cc = np.zeros(lmax+1, dtype=c.dtype)
        cc[deg] = c
        c = cc

    # warn on rank reduction
    if rank != order and not full:
        msg = "The fit may be poorly conditioned"
        warnings.warn(msg, pu.RankWarning, stacklevel=2)

    if full:
        return c, [resids, rank, s, rcond]
    else:
        return c


def hermcompanion(c):
    """Return the scaled companion matrix of c.

    The basis polynomials are scaled so that the companion matrix is
    symmetric when `c` is an Hermite basis polynomial. This provides
    better eigenvalue estimates than the unscaled case and for basis
    polynomials the eigenvalues are guaranteed to be real if
    `numpy.linalg.eigvalsh` is used to obtain them.

    Parameters
    ----------
    c : array_like
        1-D array of Hermite series coefficients ordered from low to high
        degree.

    Returns
    -------
    mat : ndarray
        Scaled companion matrix of dimensions (deg, deg).

    Notes
    -----

    .. versionadded::1.7.0

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) < 2:
        raise ValueError('Series must have maximum degree of at least 1.')
    if len(c) == 2:
        return np.array([[-.5*c[0]/c[1]]])

    n = len(c) - 1
    mat = np.zeros((n, n), dtype=c.dtype)
    scl = np.hstack((1., 1./np.sqrt(2.*np.arange(n - 1, 0, -1))))
    scl = np.multiply.accumulate(scl)[::-1]
    top = mat.reshape(-1)[1::n+1]
    bot = mat.reshape(-1)[n::n+1]
    top[...] = np.sqrt(.5*np.arange(1, n))
    bot[...] = top
    mat[:, -1] -= scl*c[:-1]/(2.0*c[-1])
    return mat


def hermroots(c):
    """
    Compute the roots of a Hermite series.

    Return the roots (a.k.a. "zeros") of the polynomial

    .. math:: p(x) = \\sum_i c[i] * H_i(x).

    Parameters
    ----------
    c : 1-D array_like
        1-D array of coefficients.

    Returns
    -------
    out : ndarray
        Array of the roots of the series. If all the roots are real,
        then `out` is also real, otherwise it is complex.

    See Also
    --------
    polyroots, legroots, lagroots, chebroots, hermeroots

    Notes
    -----
    The root estimates are obtained as the eigenvalues of the companion
    matrix, Roots far from the origin of the complex plane may have large
    errors due to the numerical instability of the series for such
    values. Roots with multiplicity greater than 1 will also show larger
    errors as the value of the series near such points is relatively
    insensitive to errors in the roots. Isolated roots near the origin can
    be improved by a few iterations of Newton's method.

    The Hermite series basis polynomials aren't powers of `x` so the
    results of this function may seem unintuitive.

    Examples
    --------
    >>> from numpy.polynomial.hermite import hermroots, hermfromroots
    >>> coef = hermfromroots([-1, 0, 1])
    >>> coef
    array([ 0.   ,  0.25 ,  0.   ,  0.125])
    >>> hermroots(coef)
    array([ -1.00000000e+00,  -1.38777878e-17,   1.00000000e+00])

    """
    # c is a trimmed copy
    [c] = pu.as_series([c])
    if len(c) <= 1:
        return np.array([], dtype=c.dtype)
    if len(c) == 2:
        return np.array([-.5*c[0]/c[1]])

    m = hermcompanion(c)
    r = la.eigvals(m)
    r.sort()
    return r


def _normed_hermite_n(x, n):
    """
    Evaluate a normalized Hermite polynomial.

    Compute the value of the normalized Hermite polynomial of degree ``n``
    at the points ``x``.


    Parameters
    ----------
    x : ndarray of double.
        Points at which to evaluate the function
    n : int
        Degree of the normalized Hermite function to be evaluated.

    Returns
    -------
    values : ndarray
        The shape of the return value is described above.

    Notes
    -----
    .. versionadded:: 1.10.0

    This function is needed for finding the Gauss points and integration
    weights for high degrees. The values of the standard Hermite functions
    overflow when n >= 207.

    """
    if n == 0:
        return np.ones(x.shape)/np.sqrt(np.sqrt(np.pi))

    c0 = 0.
    c1 = 1./np.sqrt(np.sqrt(np.pi))
    nd = float(n)
    for i in range(n - 1):
        tmp = c0
        c0 = -c1*np.sqrt((nd - 1.)/nd)
        c1 = tmp + c1*x*np.sqrt(2./nd)
        nd = nd - 1.0
    return c0 + c1*x*np.sqrt(2)


def hermgauss(deg):
    """
    Gauss-Hermite quadrature.

    Computes the sample points and weights for Gauss-Hermite quadrature.
    These sample points and weights will correctly integrate polynomials of
    degree :math:`2*deg - 1` or less over the interval :math:`[-\\inf, \\inf]`
    with the weight function :math:`f(x) = \\exp(-x^2)`.

    Parameters
    ----------
    deg : int
        Number of sample points and weights. It must be >= 1.

    Returns
    -------
    x : ndarray
        1-D ndarray containing the sample points.
    y : ndarray
        1-D ndarray containing the weights.

    Notes
    -----

    .. versionadded::1.7.0

    The results have only been tested up to degree 100, higher degrees may
    be problematic. The weights are determined by using the fact that

    .. math:: w_k = c / (H'_n(x_k) * H_{n-1}(x_k))

    where :math:`c` is a constant independent of :math:`k` and :math:`x_k`
    is the k'th root of :math:`H_n`, and then scaling the results to get
    the right value when integrating 1.

    """
    ideg = int(deg)
    if ideg != deg or ideg < 1:
        raise ValueError("deg must be a non-negative integer")

    # first approximation of roots. We use the fact that the companion
    # matrix is symmetric in this case in order to obtain better zeros.
    c = np.array([0]*deg + [1], dtype=np.float64)
    m = hermcompanion(c)
    x = la.eigvalsh(m)

    # improve roots by one application of Newton
    dy = _normed_hermite_n(x, ideg)
    df = _normed_hermite_n(x, ideg - 1) * np.sqrt(2*ideg)
    x -= dy/df

    # compute the weights. We scale the factor to avoid possible numerical
    # overflow.
    fm = _normed_hermite_n(x, ideg - 1)
    fm /= np.abs(fm).max()
    w = 1/(fm * fm)

    # for Hermite we can also symmetrize
    w = (w + w[::-1])/2
    x = (x - x[::-1])/2

    # scale w to get the right value
    w *= np.sqrt(np.pi) / w.sum()

    return x, w


def hermweight(x):
    """
    Weight function of the Hermite polynomials.

    The weight function is :math:`\\exp(-x^2)` and the interval of
    integration is :math:`[-\\inf, \\inf]`. the Hermite polynomials are
    orthogonal, but not normalized, with respect to this weight function.

    Parameters
    ----------
    x : array_like
       Values at which the weight function will be computed.

    Returns
    -------
    w : ndarray
       The weight function at `x`.

    Notes
    -----

    .. versionadded::1.7.0

    """
    w = np.exp(-x**2)
    return w


#
# Hermite series class
#

class Hermite(ABCPolyBase):
    """An Hermite series class.

    The Hermite class provides the standard Python numerical methods
    '+', '-', '*', '//', '%', 'divmod', '**', and '()' as well as the
    attributes and methods listed in the `ABCPolyBase` documentation.

    Parameters
    ----------
    coef : array_like
        Hermite coefficients in order of increasing degree, i.e,
        ``(1, 2, 3)`` gives ``1*H_0(x) + 2*H_1(X) + 3*H_2(x)``.
    domain : (2,) array_like, optional
        Domain to use. The interval ``[domain[0], domain[1]]`` is mapped
        to the interval ``[window[0], window[1]]`` by shifting and scaling.
        The default value is [-1, 1].
    window : (2,) array_like, optional
        Window, see `domain` for its use. The default value is [-1, 1].

        .. versionadded:: 1.6.0

    """
    # Virtual Functions
    _add = staticmethod(hermadd)
    _sub = staticmethod(hermsub)
    _mul = staticmethod(hermmul)
    _div = staticmethod(hermdiv)
    _pow = staticmethod(hermpow)
    _val = staticmethod(hermval)
    _int = staticmethod(hermint)
    _der = staticmethod(hermder)
    _fit = staticmethod(hermfit)
    _line = staticmethod(hermline)
    _roots = staticmethod(hermroots)
    _fromroots = staticmethod(hermfromroots)

    # Virtual properties
    nickname = 'herm'
    domain = np.array(hermdomain)
    window = np.array(hermdomain)
