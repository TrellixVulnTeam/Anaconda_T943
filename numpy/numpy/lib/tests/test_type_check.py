from __future__ import division, absolute_import, print_function

import numpy as np
from numpy.compat import long
from numpy.testing import (
    TestCase, assert_, assert_equal, assert_array_equal, run_module_suite
    )
from numpy.lib.type_check import (
    common_type, mintypecode, isreal, iscomplex, isposinf, isneginf,
    nan_to_num, isrealobj, iscomplexobj, asfarray, real_if_close
    )


def assert_all(x):
    assert_(np.all(x), x)


class TestCommonType(TestCase):
    def test_basic(self):
        ai32 = np.array([[1, 2], [3, 4]], dtype=np.int32)
        af16 = np.array([[1, 2], [3, 4]], dtype=np.float16)
        af32 = np.array([[1, 2], [3, 4]], dtype=np.float32)
        af64 = np.array([[1, 2], [3, 4]], dtype=np.float64)
        acs = np.array([[1+5j, 2+6j], [3+7j, 4+8j]], dtype=np.csingle)
        acd = np.array([[1+5j, 2+6j], [3+7j, 4+8j]], dtype=np.cdouble)
        assert_(common_type(ai32) == np.float64)
        assert_(common_type(af16) == np.float16)
        assert_(common_type(af32) == np.float32)
        assert_(common_type(af64) == np.float64)
        assert_(common_type(acs) == np.csingle)
        assert_(common_type(acd) == np.cdouble)


class TestMintypecode(TestCase):

    def test_default_1(self):
        for itype in '1bcsuwil':
            assert_equal(mintypecode(itype), 'd')
        assert_equal(mintypecode('f'), 'f')
        assert_equal(mintypecode('d'), 'd')
        assert_equal(mintypecode('F'), 'F')
        assert_equal(mintypecode('D'), 'D')

    def test_default_2(self):
        for itype in '1bcsuwil':
            assert_equal(mintypecode(itype+'f'), 'f')
            assert_equal(mintypecode(itype+'d'), 'd')
            assert_equal(mintypecode(itype+'F'), 'F')
            assert_equal(mintypecode(itype+'D'), 'D')
        assert_equal(mintypecode('ff'), 'f')
        assert_equal(mintypecode('fd'), 'd')
        assert_equal(mintypecode('fF'), 'F')
        assert_equal(mintypecode('fD'), 'D')
        assert_equal(mintypecode('df'), 'd')
        assert_equal(mintypecode('dd'), 'd')
        #assert_equal(mintypecode('dF',savespace=1),'F')
        assert_equal(mintypecode('dF'), 'D')
        assert_equal(mintypecode('dD'), 'D')
        assert_equal(mintypecode('Ff'), 'F')
        #assert_equal(mintypecode('Fd',savespace=1),'F')
        assert_equal(mintypecode('Fd'), 'D')
        assert_equal(mintypecode('FF'), 'F')
        assert_equal(mintypecode('FD'), 'D')
        assert_equal(mintypecode('Df'), 'D')
        assert_equal(mintypecode('Dd'), 'D')
        assert_equal(mintypecode('DF'), 'D')
        assert_equal(mintypecode('DD'), 'D')

    def test_default_3(self):
        assert_equal(mintypecode('fdF'), 'D')
        #assert_equal(mintypecode('fdF',savespace=1),'F')
        assert_equal(mintypecode('fdD'), 'D')
        assert_equal(mintypecode('fFD'), 'D')
        assert_equal(mintypecode('dFD'), 'D')

        assert_equal(mintypecode('ifd'), 'd')
        assert_equal(mintypecode('ifF'), 'F')
        assert_equal(mintypecode('ifD'), 'D')
        assert_equal(mintypecode('idF'), 'D')
        #assert_equal(mintypecode('idF',savespace=1),'F')
        assert_equal(mintypecode('idD'), 'D')


class TestIsscalar(TestCase):

    def test_basic(self):
        assert_(np.isscalar(3))
        assert_(not np.isscalar([3]))
        assert_(not np.isscalar((3,)))
        assert_(np.isscalar(3j))
        assert_(np.isscalar(long(10)))
        assert_(np.isscalar(4.0))


class TestReal(TestCase):

    def test_real(self):
        y = np.random.rand(10,)
        assert_array_equal(y, np.real(y))

    def test_cmplx(self):
        y = np.random.rand(10,)+1j*np.random.rand(10,)
        assert_array_equal(y.real, np.real(y))


class TestImag(TestCase):

    def test_real(self):
        y = np.random.rand(10,)
        assert_array_equal(0, np.imag(y))

    def test_cmplx(self):
        y = np.random.rand(10,)+1j*np.random.rand(10,)
        assert_array_equal(y.imag, np.imag(y))


class TestIscomplex(TestCase):

    def test_fail(self):
        z = np.array([-1, 0, 1])
        res = iscomplex(z)
        assert_(not np.sometrue(res, axis=0))

    def test_pass(self):
        z = np.array([-1j, 1, 0])
        res = iscomplex(z)
        assert_array_equal(res, [1, 0, 0])


class TestIsreal(TestCase):

    def test_pass(self):
        z = np.array([-1, 0, 1j])
        res = isreal(z)
        assert_array_equal(res, [1, 1, 0])

    def test_fail(self):
        z = np.array([-1j, 1, 0])
        res = isreal(z)
        assert_array_equal(res, [0, 1, 1])


class TestIscomplexobj(TestCase):

    def test_basic(self):
        z = np.array([-1, 0, 1])
        assert_(not iscomplexobj(z))
        z = np.array([-1j, 0, -1])
        assert_(iscomplexobj(z))

    def test_scalar(self):
        assert_(not iscomplexobj(1.0))
        assert_(iscomplexobj(1+0j))

    def test_list(self):
        assert_(iscomplexobj([3, 1+0j, True]))
        assert_(not iscomplexobj([3, 1, True]))

    def test_duck(self):
        class DummyComplexArray:
            @property
            def dtype(self):
                return np.dtype(complex)
        dummy = DummyComplexArray()
        assert_(iscomplexobj(dummy))

    def test_pandas_duck(self):
        # This tests a custom np.dtype duck-typed class, such as used by pandas
        # (pandas.core.dtypes)
        class PdComplex(np.complex128):
            pass
        class PdDtype(object):
            name = 'category'
            names = None
            type = PdComplex
            kind = 'c'
            str = '<c16'
            base = np.dtype('complex128')
        class DummyPd:
            @property
            def dtype(self):
                return PdDtype
        dummy = DummyPd()
        assert_(iscomplexobj(dummy))


class TestIsrealobj(TestCase):
    def test_basic(self):
        z = np.array([-1, 0, 1])
        assert_(isrealobj(z))
        z = np.array([-1j, 0, -1])
        assert_(not isrealobj(z))


class TestIsnan(TestCase):

    def test_goodvalues(self):
        z = np.array((-1., 0., 1.))
        res = np.isnan(z) == 0
        assert_all(np.all(res, axis=0))

    def test_posinf(self):
        with np.errstate(divide='ignore'):
            assert_all(np.isnan(np.array((1.,))/0.) == 0)

    def test_neginf(self):
        with np.errstate(divide='ignore'):
            assert_all(np.isnan(np.array((-1.,))/0.) == 0)

    def test_ind(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isnan(np.array((0.,))/0.) == 1)

    def test_integer(self):
        assert_all(np.isnan(1) == 0)

    def test_complex(self):
        assert_all(np.isnan(1+1j) == 0)

    def test_complex1(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isnan(np.array(0+0j)/0.) == 1)


class TestIsfinite(TestCase):
    # Fixme, wrong place, isfinite now ufunc

    def test_goodvalues(self):
        z = np.array((-1., 0., 1.))
        res = np.isfinite(z) == 1
        assert_all(np.all(res, axis=0))

    def test_posinf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array((1.,))/0.) == 0)

    def test_neginf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array((-1.,))/0.) == 0)

    def test_ind(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array((0.,))/0.) == 0)

    def test_integer(self):
        assert_all(np.isfinite(1) == 1)

    def test_complex(self):
        assert_all(np.isfinite(1+1j) == 1)

    def test_complex1(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array(1+1j)/0.) == 0)


class TestIsinf(TestCase):
    # Fixme, wrong place, isinf now ufunc

    def test_goodvalues(self):
        z = np.array((-1., 0., 1.))
        res = np.isinf(z) == 0
        assert_all(np.all(res, axis=0))

    def test_posinf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array((1.,))/0.) == 1)

    def test_posinf_scalar(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array(1.,)/0.) == 1)

    def test_neginf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array((-1.,))/0.) == 1)

    def test_neginf_scalar(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array(-1.)/0.) == 1)

    def test_ind(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array((0.,))/0.) == 0)


class TestIsposinf(TestCase):

    def test_generic(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = isposinf(np.array((-1., 0, 1))/0.)
        assert_(vals[0] == 0)
        assert_(vals[1] == 0)
        assert_(vals[2] == 1)


class TestIsneginf(TestCase):

    def test_generic(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = isneginf(np.array((-1., 0, 1))/0.)
        assert_(vals[0] == 1)
        assert_(vals[1] == 0)
        assert_(vals[2] == 0)


class TestNanToNum(TestCase):

    def test_generic(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = nan_to_num(np.array((-1., 0, 1))/0.)
        assert_all(vals[0] < -1e10) and assert_all(np.isfinite(vals[0]))
        assert_(vals[1] == 0)
        assert_all(vals[2] > 1e10) and assert_all(np.isfinite(vals[2]))

    def test_integer(self):
        vals = nan_to_num(1)
        assert_all(vals == 1)
        vals = nan_to_num([1])
        assert_array_equal(vals, np.array([1], np.int))

    def test_complex_good(self):
        vals = nan_to_num(1+1j)
        assert_all(vals == 1+1j)

    def test_complex_bad(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            v = 1 + 1j
            v += np.array(0+1.j)/0.
        vals = nan_to_num(v)
        # !! This is actually (unexpectedly) zero
        assert_all(np.isfinite(vals))

    def test_complex_bad2(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            v = 1 + 1j
            v += np.array(-1+1.j)/0.
        vals = nan_to_num(v)
        assert_all(np.isfinite(vals))
        # Fixme
        #assert_all(vals.imag > 1e10)  and assert_all(np.isfinite(vals))
        # !! This is actually (unexpectedly) positive
        # !! inf.  Comment out for now, and see if it
        # !! changes
        #assert_all(vals.real < -1e10) and assert_all(np.isfinite(vals))


class TestRealIfClose(TestCase):

    def test_basic(self):
        a = np.random.rand(10)
        b = real_if_close(a+1e-15j)
        assert_all(isrealobj(b))
        assert_array_equal(a, b)
        b = real_if_close(a+1e-7j)
        assert_all(iscomplexobj(b))
        b = real_if_close(a+1e-7j, tol=1e-6)
        assert_all(isrealobj(b))


class TestArrayConversion(TestCase):

    def test_asfarray(self):
        a = asfarray(np.array([1, 2, 3]))
        assert_equal(a.__class__, np.ndarray)
        assert_(np.issubdtype(a.dtype, np.float))

if __name__ == "__main__":
    run_module_suite()
