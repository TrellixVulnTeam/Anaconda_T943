from __future__ import division, absolute_import, print_function

import sys
import warnings

import numpy as np
from numpy import array, arange, nditer, all
from numpy.compat import asbytes, sixu
from numpy.core.multiarray_tests import test_nditer_too_large
from numpy.testing import (
    run_module_suite, assert_, assert_equal, assert_array_equal,
    assert_raises, assert_warns, dec, HAS_REFCOUNT, suppress_warnings
    )


def iter_multi_index(i):
    ret = []
    while not i.finished:
        ret.append(i.multi_index)
        i.iternext()
    return ret

def iter_indices(i):
    ret = []
    while not i.finished:
        ret.append(i.index)
        i.iternext()
    return ret

def iter_iterindices(i):
    ret = []
    while not i.finished:
        ret.append(i.iterindex)
        i.iternext()
    return ret

@dec.skipif(not HAS_REFCOUNT, "python does not have sys.getrefcount")
def test_iter_refcount():
    # Make sure the iterator doesn't leak

    # Basic
    a = arange(6)
    dt = np.dtype('f4').newbyteorder()
    rc_a = sys.getrefcount(a)
    rc_dt = sys.getrefcount(dt)
    it = nditer(a, [],
                [['readwrite', 'updateifcopy']],
                casting='unsafe',
                op_dtypes=[dt])
    assert_(not it.iterationneedsapi)
    assert_(sys.getrefcount(a) > rc_a)
    assert_(sys.getrefcount(dt) > rc_dt)
    it = None
    assert_equal(sys.getrefcount(a), rc_a)
    assert_equal(sys.getrefcount(dt), rc_dt)

    # With a copy
    a = arange(6, dtype='f4')
    dt = np.dtype('f4')
    rc_a = sys.getrefcount(a)
    rc_dt = sys.getrefcount(dt)
    it = nditer(a, [],
                [['readwrite']],
                op_dtypes=[dt])
    rc2_a = sys.getrefcount(a)
    rc2_dt = sys.getrefcount(dt)
    it2 = it.copy()
    assert_(sys.getrefcount(a) > rc2_a)
    assert_(sys.getrefcount(dt) > rc2_dt)
    it = None
    assert_equal(sys.getrefcount(a), rc2_a)
    assert_equal(sys.getrefcount(dt), rc2_dt)
    it2 = None
    assert_equal(sys.getrefcount(a), rc_a)
    assert_equal(sys.getrefcount(dt), rc_dt)

    del it2  # avoid pyflakes unused variable warning

def test_iter_best_order():
    # The iterator should always find the iteration order
    # with increasing memory addresses

    # Test the ordering for 1-D to 5-D shapes
    for shape in [(5,), (3, 4), (2, 3, 4), (2, 3, 4, 3), (2, 3, 2, 2, 3)]:
        a = arange(np.prod(shape))
        # Test each combination of positive and negative strides
        for dirs in range(2**len(shape)):
            dirs_index = [slice(None)]*len(shape)
            for bit in range(len(shape)):
                if ((2**bit) & dirs):
                    dirs_index[bit] = slice(None, None, -1)
            dirs_index = tuple(dirs_index)

            aview = a.reshape(shape)[dirs_index]
            # C-order
            i = nditer(aview, [], [['readonly']])
            assert_equal([x for x in i], a)
            # Fortran-order
            i = nditer(aview.T, [], [['readonly']])
            assert_equal([x for x in i], a)
            # Other order
            if len(shape) > 2:
                i = nditer(aview.swapaxes(0, 1), [], [['readonly']])
                assert_equal([x for x in i], a)

def test_iter_c_order():
    # Test forcing C order

    # Test the ordering for 1-D to 5-D shapes
    for shape in [(5,), (3, 4), (2, 3, 4), (2, 3, 4, 3), (2, 3, 2, 2, 3)]:
        a = arange(np.prod(shape))
        # Test each combination of positive and negative strides
        for dirs in range(2**len(shape)):
            dirs_index = [slice(None)]*len(shape)
            for bit in range(len(shape)):
                if ((2**bit) & dirs):
                    dirs_index[bit] = slice(None, None, -1)
            dirs_index = tuple(dirs_index)

            aview = a.reshape(shape)[dirs_index]
            # C-order
            i = nditer(aview, order='C')
            assert_equal([x for x in i], aview.ravel(order='C'))
            # Fortran-order
            i = nditer(aview.T, order='C')
            assert_equal([x for x in i], aview.T.ravel(order='C'))
            # Other order
            if len(shape) > 2:
                i = nditer(aview.swapaxes(0, 1), order='C')
                assert_equal([x for x in i],
                                    aview.swapaxes(0, 1).ravel(order='C'))

def test_iter_f_order():
    # Test forcing F order

    # Test the ordering for 1-D to 5-D shapes
    for shape in [(5,), (3, 4), (2, 3, 4), (2, 3, 4, 3), (2, 3, 2, 2, 3)]:
        a = arange(np.prod(shape))
        # Test each combination of positive and negative strides
        for dirs in range(2**len(shape)):
            dirs_index = [slice(None)]*len(shape)
            for bit in range(len(shape)):
                if ((2**bit) & dirs):
                    dirs_index[bit] = slice(None, None, -1)
            dirs_index = tuple(dirs_index)

            aview = a.reshape(shape)[dirs_index]
            # C-order
            i = nditer(aview, order='F')
            assert_equal([x for x in i], aview.ravel(order='F'))
            # Fortran-order
            i = nditer(aview.T, order='F')
            assert_equal([x for x in i], aview.T.ravel(order='F'))
            # Other order
            if len(shape) > 2:
                i = nditer(aview.swapaxes(0, 1), order='F')
                assert_equal([x for x in i],
                                    aview.swapaxes(0, 1).ravel(order='F'))

def test_iter_c_or_f_order():
    # Test forcing any contiguous (C or F) order

    # Test the ordering for 1-D to 5-D shapes
    for shape in [(5,), (3, 4), (2, 3, 4), (2, 3, 4, 3), (2, 3, 2, 2, 3)]:
        a = arange(np.prod(shape))
        # Test each combination of positive and negative strides
        for dirs in range(2**len(shape)):
            dirs_index = [slice(None)]*len(shape)
            for bit in range(len(shape)):
                if ((2**bit) & dirs):
                    dirs_index[bit] = slice(None, None, -1)
            dirs_index = tuple(dirs_index)

            aview = a.reshape(shape)[dirs_index]
            # C-order
            i = nditer(aview, order='A')
            assert_equal([x for x in i], aview.ravel(order='A'))
            # Fortran-order
            i = nditer(aview.T, order='A')
            assert_equal([x for x in i], aview.T.ravel(order='A'))
            # Other order
            if len(shape) > 2:
                i = nditer(aview.swapaxes(0, 1), order='A')
                assert_equal([x for x in i],
                                    aview.swapaxes(0, 1).ravel(order='A'))

def test_iter_best_order_multi_index_1d():
    # The multi-indices should be correct with any reordering

    a = arange(4)
    # 1D order
    i = nditer(a, ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(0,), (1,), (2,), (3,)])
    # 1D reversed order
    i = nditer(a[::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(3,), (2,), (1,), (0,)])

def test_iter_best_order_multi_index_2d():
    # The multi-indices should be correct with any reordering

    a = arange(6)
    # 2D C-order
    i = nditer(a.reshape(2, 3), ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)])
    # 2D Fortran-order
    i = nditer(a.reshape(2, 3).copy(order='F'), ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)])
    # 2D reversed C-order
    i = nditer(a.reshape(2, 3)[::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(1, 0), (1, 1), (1, 2), (0, 0), (0, 1), (0, 2)])
    i = nditer(a.reshape(2, 3)[:, ::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(0, 2), (0, 1), (0, 0), (1, 2), (1, 1), (1, 0)])
    i = nditer(a.reshape(2, 3)[::-1, ::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(1, 2), (1, 1), (1, 0), (0, 2), (0, 1), (0, 0)])
    # 2D reversed Fortran-order
    i = nditer(a.reshape(2, 3).copy(order='F')[::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(1, 0), (0, 0), (1, 1), (0, 1), (1, 2), (0, 2)])
    i = nditer(a.reshape(2, 3).copy(order='F')[:, ::-1],
                                                   ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(0, 2), (1, 2), (0, 1), (1, 1), (0, 0), (1, 0)])
    i = nditer(a.reshape(2, 3).copy(order='F')[::-1, ::-1],
                                                   ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i), [(1, 2), (0, 2), (1, 1), (0, 1), (1, 0), (0, 0)])

def test_iter_best_order_multi_index_3d():
    # The multi-indices should be correct with any reordering

    a = arange(12)
    # 3D C-order
    i = nditer(a.reshape(2, 3, 2), ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (0, 2, 0), (0, 2, 1),
                             (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1), (1, 2, 0), (1, 2, 1)])
    # 3D Fortran-order
    i = nditer(a.reshape(2, 3, 2).copy(order='F'), ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 2, 0), (1, 2, 0),
                             (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1), (1, 2, 1)])
    # 3D reversed C-order
    i = nditer(a.reshape(2, 3, 2)[::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1), (1, 2, 0), (1, 2, 1),
                             (0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (0, 2, 0), (0, 2, 1)])
    i = nditer(a.reshape(2, 3, 2)[:, ::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(0, 2, 0), (0, 2, 1), (0, 1, 0), (0, 1, 1), (0, 0, 0), (0, 0, 1),
                             (1, 2, 0), (1, 2, 1), (1, 1, 0), (1, 1, 1), (1, 0, 0), (1, 0, 1)])
    i = nditer(a.reshape(2, 3, 2)[:,:, ::-1], ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(0, 0, 1), (0, 0, 0), (0, 1, 1), (0, 1, 0), (0, 2, 1), (0, 2, 0),
                             (1, 0, 1), (1, 0, 0), (1, 1, 1), (1, 1, 0), (1, 2, 1), (1, 2, 0)])
    # 3D reversed Fortran-order
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[::-1],
                                                    ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(1, 0, 0), (0, 0, 0), (1, 1, 0), (0, 1, 0), (1, 2, 0), (0, 2, 0),
                             (1, 0, 1), (0, 0, 1), (1, 1, 1), (0, 1, 1), (1, 2, 1), (0, 2, 1)])
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[:, ::-1],
                                                    ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(0, 2, 0), (1, 2, 0), (0, 1, 0), (1, 1, 0), (0, 0, 0), (1, 0, 0),
                             (0, 2, 1), (1, 2, 1), (0, 1, 1), (1, 1, 1), (0, 0, 1), (1, 0, 1)])
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[:,:, ::-1],
                                                    ['multi_index'], [['readonly']])
    assert_equal(iter_multi_index(i),
                            [(0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1), (1, 2, 1),
                             (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 2, 0), (1, 2, 0)])

def test_iter_best_order_c_index_1d():
    # The C index should be correct with any reordering

    a = arange(4)
    # 1D order
    i = nditer(a, ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [0, 1, 2, 3])
    # 1D reversed order
    i = nditer(a[::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [3, 2, 1, 0])

def test_iter_best_order_c_index_2d():
    # The C index should be correct with any reordering

    a = arange(6)
    # 2D C-order
    i = nditer(a.reshape(2, 3), ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [0, 1, 2, 3, 4, 5])
    # 2D Fortran-order
    i = nditer(a.reshape(2, 3).copy(order='F'),
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [0, 3, 1, 4, 2, 5])
    # 2D reversed C-order
    i = nditer(a.reshape(2, 3)[::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [3, 4, 5, 0, 1, 2])
    i = nditer(a.reshape(2, 3)[:, ::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [2, 1, 0, 5, 4, 3])
    i = nditer(a.reshape(2, 3)[::-1, ::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [5, 4, 3, 2, 1, 0])
    # 2D reversed Fortran-order
    i = nditer(a.reshape(2, 3).copy(order='F')[::-1],
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [3, 0, 4, 1, 5, 2])
    i = nditer(a.reshape(2, 3).copy(order='F')[:, ::-1],
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [2, 5, 1, 4, 0, 3])
    i = nditer(a.reshape(2, 3).copy(order='F')[::-1, ::-1],
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i), [5, 2, 4, 1, 3, 0])

def test_iter_best_order_c_index_3d():
    # The C index should be correct with any reordering

    a = arange(12)
    # 3D C-order
    i = nditer(a.reshape(2, 3, 2), ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    # 3D Fortran-order
    i = nditer(a.reshape(2, 3, 2).copy(order='F'),
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [0, 6, 2, 8, 4, 10, 1, 7, 3, 9, 5, 11])
    # 3D reversed C-order
    i = nditer(a.reshape(2, 3, 2)[::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5])
    i = nditer(a.reshape(2, 3, 2)[:, ::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [4, 5, 2, 3, 0, 1, 10, 11, 8, 9, 6, 7])
    i = nditer(a.reshape(2, 3, 2)[:,:, ::-1], ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10])
    # 3D reversed Fortran-order
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[::-1],
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [6, 0, 8, 2, 10, 4, 7, 1, 9, 3, 11, 5])
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[:, ::-1],
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [4, 10, 2, 8, 0, 6, 5, 11, 3, 9, 1, 7])
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[:,:, ::-1],
                                    ['c_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [1, 7, 3, 9, 5, 11, 0, 6, 2, 8, 4, 10])

def test_iter_best_order_f_index_1d():
    # The Fortran index should be correct with any reordering

    a = arange(4)
    # 1D order
    i = nditer(a, ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [0, 1, 2, 3])
    # 1D reversed order
    i = nditer(a[::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [3, 2, 1, 0])

def test_iter_best_order_f_index_2d():
    # The Fortran index should be correct with any reordering

    a = arange(6)
    # 2D C-order
    i = nditer(a.reshape(2, 3), ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [0, 2, 4, 1, 3, 5])
    # 2D Fortran-order
    i = nditer(a.reshape(2, 3).copy(order='F'),
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [0, 1, 2, 3, 4, 5])
    # 2D reversed C-order
    i = nditer(a.reshape(2, 3)[::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [1, 3, 5, 0, 2, 4])
    i = nditer(a.reshape(2, 3)[:, ::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [4, 2, 0, 5, 3, 1])
    i = nditer(a.reshape(2, 3)[::-1, ::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [5, 3, 1, 4, 2, 0])
    # 2D reversed Fortran-order
    i = nditer(a.reshape(2, 3).copy(order='F')[::-1],
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [1, 0, 3, 2, 5, 4])
    i = nditer(a.reshape(2, 3).copy(order='F')[:, ::-1],
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [4, 5, 2, 3, 0, 1])
    i = nditer(a.reshape(2, 3).copy(order='F')[::-1, ::-1],
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i), [5, 4, 3, 2, 1, 0])

def test_iter_best_order_f_index_3d():
    # The Fortran index should be correct with any reordering

    a = arange(12)
    # 3D C-order
    i = nditer(a.reshape(2, 3, 2), ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [0, 6, 2, 8, 4, 10, 1, 7, 3, 9, 5, 11])
    # 3D Fortran-order
    i = nditer(a.reshape(2, 3, 2).copy(order='F'),
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    # 3D reversed C-order
    i = nditer(a.reshape(2, 3, 2)[::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [1, 7, 3, 9, 5, 11, 0, 6, 2, 8, 4, 10])
    i = nditer(a.reshape(2, 3, 2)[:, ::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [4, 10, 2, 8, 0, 6, 5, 11, 3, 9, 1, 7])
    i = nditer(a.reshape(2, 3, 2)[:,:, ::-1], ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [6, 0, 8, 2, 10, 4, 7, 1, 9, 3, 11, 5])
    # 3D reversed Fortran-order
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[::-1],
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10])
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[:, ::-1],
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [4, 5, 2, 3, 0, 1, 10, 11, 8, 9, 6, 7])
    i = nditer(a.reshape(2, 3, 2).copy(order='F')[:,:, ::-1],
                                    ['f_index'], [['readonly']])
    assert_equal(iter_indices(i),
                            [6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4, 5])

def test_iter_no_inner_full_coalesce():
    # Check no_inner iterators which coalesce into a single inner loop

    for shape in [(5,), (3, 4), (2, 3, 4), (2, 3, 4, 3), (2, 3, 2, 2, 3)]:
        size = np.prod(shape)
        a = arange(size)
        # Test each combination of forward and backwards indexing
        for dirs in range(2**len(shape)):
            dirs_index = [slice(None)]*len(shape)
            for bit in range(len(shape)):
                if ((2**bit) & dirs):
                    dirs_index[bit] = slice(None, None, -1)
            dirs_index = tuple(dirs_index)

            aview = a.reshape(shape)[dirs_index]
            # C-order
            i = nditer(aview, ['external_loop'], [['readonly']])
            assert_equal(i.ndim, 1)
            assert_equal(i[0].shape, (size,))
            # Fortran-order
            i = nditer(aview.T, ['external_loop'], [['readonly']])
            assert_equal(i.ndim, 1)
            assert_equal(i[0].shape, (size,))
            # Other order
            if len(shape) > 2:
                i = nditer(aview.swapaxes(0, 1),
                                    ['external_loop'], [['readonly']])
                assert_equal(i.ndim, 1)
                assert_equal(i[0].shape, (size,))

def test_iter_no_inner_dim_coalescing():
    # Check no_inner iterators whose dimensions may not coalesce completely

    # Skipping the last element in a dimension prevents coalescing
    # with the next-bigger dimension
    a = arange(24).reshape(2, 3, 4)[:,:, :-1]
    i = nditer(a, ['external_loop'], [['readonly']])
    assert_equal(i.ndim, 2)
    assert_equal(i[0].shape, (3,))
    a = arange(24).reshape(2, 3, 4)[:, :-1,:]
    i = nditer(a, ['external_loop'], [['readonly']])
    assert_equal(i.ndim, 2)
    assert_equal(i[0].shape, (8,))
    a = arange(24).reshape(2, 3, 4)[:-1,:,:]
    i = nditer(a, ['external_loop'], [['readonly']])
    assert_equal(i.ndim, 1)
    assert_equal(i[0].shape, (12,))

    # Even with lots of 1-sized dimensions, should still coalesce
    a = arange(24).reshape(1, 1, 2, 1, 1, 3, 1, 1, 4, 1, 1)
    i = nditer(a, ['external_loop'], [['readonly']])
    assert_equal(i.ndim, 1)
    assert_equal(i[0].shape, (24,))

def test_iter_dim_coalescing():
    # Check that the correct number of dimensions are coalesced

    # Tracking a multi-index disables coalescing
    a = arange(24).reshape(2, 3, 4)
    i = nditer(a, ['multi_index'], [['readonly']])
    assert_equal(i.ndim, 3)

    # A tracked index can allow coalescing if it's compatible with the array
    a3d = arange(24).reshape(2, 3, 4)
    i = nditer(a3d, ['c_index'], [['readonly']])
    assert_equal(i.ndim, 1)
    i = nditer(a3d.swapaxes(0, 1), ['c_index'], [['readonly']])
    assert_equal(i.ndim, 3)
    i = nditer(a3d.T, ['c_index'], [['readonly']])
    assert_equal(i.ndim, 3)
    i = nditer(a3d.T, ['f_index'], [['readonly']])
    assert_equal(i.ndim, 1)
    i = nditer(a3d.T.swapaxes(0, 1), ['f_index'], [['readonly']])
    assert_equal(i.ndim, 3)

    # When C or F order is forced, coalescing may still occur
    a3d = arange(24).reshape(2, 3, 4)
    i = nditer(a3d, order='C')
    assert_equal(i.ndim, 1)
    i = nditer(a3d.T, order='C')
    assert_equal(i.ndim, 3)
    i = nditer(a3d, order='F')
    assert_equal(i.ndim, 3)
    i = nditer(a3d.T, order='F')
    assert_equal(i.ndim, 1)
    i = nditer(a3d, order='A')
    assert_equal(i.ndim, 1)
    i = nditer(a3d.T, order='A')
    assert_equal(i.ndim, 1)

def test_iter_broadcasting():
    # Standard NumPy broadcasting rules

    # 1D with scalar
    i = nditer([arange(6), np.int32(2)], ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 6)
    assert_equal(i.shape, (6,))

    # 2D with scalar
    i = nditer([arange(6).reshape(2, 3), np.int32(2)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 6)
    assert_equal(i.shape, (2, 3))
    # 2D with 1D
    i = nditer([arange(6).reshape(2, 3), arange(3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 6)
    assert_equal(i.shape, (2, 3))
    i = nditer([arange(2).reshape(2, 1), arange(3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 6)
    assert_equal(i.shape, (2, 3))
    # 2D with 2D
    i = nditer([arange(2).reshape(2, 1), arange(3).reshape(1, 3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 6)
    assert_equal(i.shape, (2, 3))

    # 3D with scalar
    i = nditer([np.int32(2), arange(24).reshape(4, 2, 3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    # 3D with 1D
    i = nditer([arange(3), arange(24).reshape(4, 2, 3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    i = nditer([arange(3), arange(8).reshape(4, 2, 1)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    # 3D with 2D
    i = nditer([arange(6).reshape(2, 3), arange(24).reshape(4, 2, 3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    i = nditer([arange(2).reshape(2, 1), arange(24).reshape(4, 2, 3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    i = nditer([arange(3).reshape(1, 3), arange(8).reshape(4, 2, 1)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    # 3D with 3D
    i = nditer([arange(2).reshape(1, 2, 1), arange(3).reshape(1, 1, 3),
                        arange(4).reshape(4, 1, 1)],
                        ['multi_index'], [['readonly']]*3)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    i = nditer([arange(6).reshape(1, 2, 3), arange(4).reshape(4, 1, 1)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))
    i = nditer([arange(24).reshape(4, 2, 3), arange(12).reshape(4, 1, 3)],
                        ['multi_index'], [['readonly']]*2)
    assert_equal(i.itersize, 24)
    assert_equal(i.shape, (4, 2, 3))

def test_iter_itershape():
    # Check that allocated outputs work with a specified shape
    a = np.arange(6, dtype='i2').reshape(2, 3)
    i = nditer([a, None], [], [['readonly'], ['writeonly', 'allocate']],
                            op_axes=[[0, 1, None], None],
                            itershape=(-1, -1, 4))
    assert_equal(i.operands[1].shape, (2, 3, 4))
    assert_equal(i.operands[1].strides, (24, 8, 2))

    i = nditer([a.T, None], [], [['readonly'], ['writeonly', 'allocate']],
                            op_axes=[[0, 1, None], None],
                            itershape=(-1, -1, 4))
    assert_equal(i.operands[1].shape, (3, 2, 4))
    assert_equal(i.operands[1].strides, (8, 24, 2))

    i = nditer([a.T, None], [], [['readonly'], ['writeonly', 'allocate']],
                            order='F',
                            op_axes=[[0, 1, None], None],
                            itershape=(-1, -1, 4))
    assert_equal(i.operands[1].shape, (3, 2, 4))
    assert_equal(i.operands[1].strides, (2, 6, 12))

    # If we specify 1 in the itershape, it shouldn't allow broadcasting
    # of that dimension to a bigger value
    assert_raises(ValueError, nditer, [a, None], [],
                            [['readonly'], ['writeonly', 'allocate']],
                            op_axes=[[0, 1, None], None],
                            itershape=(-1, 1, 4))
    # Test bug that for no op_axes but itershape, they are NULLed correctly
    i = np.nditer([np.ones(2), None, None], itershape=(2,))

def test_iter_broadcasting_errors():
    # Check that errors are thrown for bad broadcasting shapes

    # 1D with 1D
    assert_raises(ValueError, nditer, [arange(2), arange(3)],
                    [], [['readonly']]*2)
    # 2D with 1D
    assert_raises(ValueError, nditer,
                    [arange(6).reshape(2, 3), arange(2)],
                    [], [['readonly']]*2)
    # 2D with 2D
    assert_raises(ValueError, nditer,
                    [arange(6).reshape(2, 3), arange(9).reshape(3, 3)],
                    [], [['readonly']]*2)
    assert_raises(ValueError, nditer,
                    [arange(6).reshape(2, 3), arange(4).reshape(2, 2)],
                    [], [['readonly']]*2)
    # 3D with 3D
    assert_raises(ValueError, nditer,
                    [arange(36).reshape(3, 3, 4), arange(24).reshape(2, 3, 4)],
                    [], [['readonly']]*2)
    assert_raises(ValueError, nditer,
                    [arange(8).reshape(2, 4, 1), arange(24).reshape(2, 3, 4)],
                    [], [['readonly']]*2)

    # Verify that the error message mentions the right shapes
    try:
        nditer([arange(2).reshape(1, 2, 1),
                arange(3).reshape(1, 3),
                arange(6).reshape(2, 3)],
               [],
               [['readonly'], ['readonly'], ['writeonly', 'no_broadcast']])
        raise AssertionError('Should have raised a broadcast error')
    except ValueError as e:
        msg = str(e)
        # The message should contain the shape of the 3rd operand
        assert_(msg.find('(2,3)') >= 0,
                'Message "%s" doesn\'t contain operand shape (2,3)' % msg)
        # The message should contain the broadcast shape
        assert_(msg.find('(1,2,3)') >= 0,
                'Message "%s" doesn\'t contain broadcast shape (1,2,3)' % msg)

    try:
        nditer([arange(6).reshape(2, 3), arange(2)],
               [],
               [['readonly'], ['readonly']],
               op_axes=[[0, 1], [0, np.newaxis]],
               itershape=(4, 3))
        raise AssertionError('Should have raised a broadcast error')
    except ValueError as e:
        msg = str(e)
        # The message should contain "shape->remappedshape" for each operand
        assert_(msg.find('(2,3)->(2,3)') >= 0,
            'Message "%s" doesn\'t contain operand shape (2,3)->(2,3)' % msg)
        assert_(msg.find('(2,)->(2,newaxis)') >= 0,
                ('Message "%s" doesn\'t contain remapped operand shape' +
                '(2,)->(2,newaxis)') % msg)
        # The message should contain the itershape parameter
        assert_(msg.find('(4,3)') >= 0,
                'Message "%s" doesn\'t contain itershape parameter (4,3)' % msg)

    try:
        nditer([np.zeros((2, 1, 1)), np.zeros((2,))],
               [],
               [['writeonly', 'no_broadcast'], ['readonly']])
        raise AssertionError('Should have raised a broadcast error')
    except ValueError as e:
        msg = str(e)
        # The message should contain the shape of the bad operand
        assert_(msg.find('(2,1,1)') >= 0,
            'Message "%s" doesn\'t contain operand shape (2,1,1)' % msg)
        # The message should contain the broadcast shape
        assert_(msg.find('(2,1,2)') >= 0,
                'Message "%s" doesn\'t contain the broadcast shape (2,1,2)' % msg)

def test_iter_flags_errors():
    # Check that bad combinations of flags produce errors

    a = arange(6)

    # Not enough operands
    assert_raises(ValueError, nditer, [], [], [])
    # Too many operands
    assert_raises(ValueError, nditer, [a]*100, [], [['readonly']]*100)
    # Bad global flag
    assert_raises(ValueError, nditer, [a], ['bad flag'], [['readonly']])
    # Bad op flag
    assert_raises(ValueError, nditer, [a], [], [['readonly', 'bad flag']])
    # Bad order parameter
    assert_raises(ValueError, nditer, [a], [], [['readonly']], order='G')
    # Bad casting parameter
    assert_raises(ValueError, nditer, [a], [], [['readonly']], casting='noon')
    # op_flags must match ops
    assert_raises(ValueError, nditer, [a]*3, [], [['readonly']]*2)
    # Cannot track both a C and an F index
    assert_raises(ValueError, nditer, a,
                ['c_index', 'f_index'], [['readonly']])
    # Inner iteration and multi-indices/indices are incompatible
    assert_raises(ValueError, nditer, a,
                ['external_loop', 'multi_index'], [['readonly']])
    assert_raises(ValueError, nditer, a,
                ['external_loop', 'c_index'], [['readonly']])
    assert_raises(ValueError, nditer, a,
                ['external_loop', 'f_index'], [['readonly']])
    # Must specify exactly one of readwrite/readonly/writeonly per operand
    assert_raises(ValueError, nditer, a, [], [[]])
    assert_raises(ValueError, nditer, a, [], [['readonly', 'writeonly']])
    assert_raises(ValueError, nditer, a, [], [['readonly', 'readwrite']])
    assert_raises(ValueError, nditer, a, [], [['writeonly', 'readwrite']])
    assert_raises(ValueError, nditer, a,
                [], [['readonly', 'writeonly', 'readwrite']])
    # Python scalars are always readonly
    assert_raises(TypeError, nditer, 1.5, [], [['writeonly']])
    assert_raises(TypeError, nditer, 1.5, [], [['readwrite']])
    # Array scalars are always readonly
    assert_raises(TypeError, nditer, np.int32(1), [], [['writeonly']])
    assert_raises(TypeError, nditer, np.int32(1), [], [['readwrite']])
    # Check readonly array
    a.flags.writeable = False
    assert_raises(ValueError, nditer, a, [], [['writeonly']])
    assert_raises(ValueError, nditer, a, [], [['readwrite']])
    a.flags.writeable = True
    # Multi-indices available only with the multi_index flag
    i = nditer(arange(6), [], [['readonly']])
    assert_raises(ValueError, lambda i:i.multi_index, i)
    # Index available only with an index flag
    assert_raises(ValueError, lambda i:i.index, i)
    # GotoCoords and GotoIndex incompatible with buffering or no_inner

    def assign_multi_index(i):
        i.multi_index = (0,)

    def assign_index(i):
        i.index = 0

    def assign_iterindex(i):
        i.iterindex = 0

    def assign_iterrange(i):
        i.iterrange = (0, 1)
    i = nditer(arange(6), ['external_loop'])
    assert_raises(ValueError, assign_multi_index, i)
    assert_raises(ValueError, assign_index, i)
    assert_raises(ValueError, assign_iterindex, i)
    assert_raises(ValueError, assign_iterrange, i)
    i = nditer(arange(6), ['buffered'])
    assert_raises(ValueError, assign_multi_index, i)
    assert_raises(ValueError, assign_index, i)
    assert_raises(ValueError, assign_iterrange, i)
    # Can't iterate if size is zero
    assert_raises(ValueError, nditer, np.array([]))

def test_iter_slice():
    a, b, c = np.arange(3), np.arange(3), np.arange(3.)
    i = nditer([a, b, c], [], ['readwrite'])
    i[0:2] = (3, 3)
    assert_equal(a, [3, 1, 2])
    assert_equal(b, [3, 1, 2])
    assert_equal(c, [0, 1, 2])
    i[1] = 12
    assert_equal(i[0:2], [3, 12])

def test_iter_nbo_align_contig():
    # Check that byte order, alignment, and contig changes work

    # Byte order change by requesting a specific dtype
    a = np.arange(6, dtype='f4')
    au = a.byteswap().newbyteorder()
    assert_(a.dtype.byteorder != au.dtype.byteorder)
    i = nditer(au, [], [['readwrite', 'updateifcopy']],
                        casting='equiv',
                        op_dtypes=[np.dtype('f4')])
    assert_equal(i.dtypes[0].byteorder, a.dtype.byteorder)
    assert_equal(i.operands[0].dtype.byteorder, a.dtype.byteorder)
    assert_equal(i.operands[0], a)
    i.operands[0][:] = 2
    i = None
    assert_equal(au, [2]*6)

    # Byte order change by requesting NBO
    a = np.arange(6, dtype='f4')
    au = a.byteswap().newbyteorder()
    assert_(a.dtype.byteorder != au.dtype.byteorder)
    i = nditer(au, [], [['readwrite', 'updateifcopy', 'nbo']], casting='equiv')
    assert_equal(i.dtypes[0].byteorder, a.dtype.byteorder)
    assert_equal(i.operands[0].dtype.byteorder, a.dtype.byteorder)
    assert_equal(i.operands[0], a)
    i.operands[0][:] = 2
    i = None
    assert_equal(au, [2]*6)

    # Unaligned input
    a = np.zeros((6*4+1,), dtype='i1')[1:]
    a.dtype = 'f4'
    a[:] = np.arange(6, dtype='f4')
    assert_(not a.flags.aligned)
    # Without 'aligned', shouldn't copy
    i = nditer(a, [], [['readonly']])
    assert_(not i.operands[0].flags.aligned)
    assert_equal(i.operands[0], a)
    # With 'aligned', should make a copy
    i = nditer(a, [], [['readwrite', 'updateifcopy', 'aligned']])
    assert_(i.operands[0].flags.aligned)
    assert_equal(i.operands[0], a)
    i.operands[0][:] = 3
    i = None
    assert_equal(a, [3]*6)

    # Discontiguous input
    a = arange(12)
    # If it is contiguous, shouldn't copy
    i = nditer(a[:6], [], [['readonly']])
    assert_(i.operands[0].flags.contiguous)
    assert_equal(i.operands[0], a[:6])
    # If it isn't contiguous, should buffer
    i = nditer(a[::2], ['buffered', 'external_loop'],
                        [['readonly', 'contig']],
                        buffersize=10)
    assert_(i[0].flags.contiguous)
    assert_equal(i[0], a[::2])

def test_iter_array_cast():
    # Check that arrays are cast as requested

    # No cast 'f4' -> 'f4'
    a = np.arange(6, dtype='f4').reshape(2, 3)
    i = nditer(a, [], [['readwrite']], op_dtypes=[np.dtype('f4')])
    assert_equal(i.operands[0], a)
    assert_equal(i.operands[0].dtype, np.dtype('f4'))

    # Byte-order cast '<f4' -> '>f4'
    a = np.arange(6, dtype='<f4').reshape(2, 3)
    i = nditer(a, [], [['readwrite', 'updateifcopy']],
            casting='equiv',
            op_dtypes=[np.dtype('>f4')])
    assert_equal(i.operands[0], a)
    assert_equal(i.operands[0].dtype, np.dtype('>f4'))

    # Safe case 'f4' -> 'f8'
    a = np.arange(24, dtype='f4').reshape(2, 3, 4).swapaxes(1, 2)
    i = nditer(a, [], [['readonly', 'copy']],
            casting='safe',
            op_dtypes=[np.dtype('f8')])
    assert_equal(i.operands[0], a)
    assert_equal(i.operands[0].dtype, np.dtype('f8'))
    # The memory layout of the temporary should match a (a is (48,4,16))
    # except negative strides get flipped to positive strides.
    assert_equal(i.operands[0].strides, (96, 8, 32))
    a = a[::-1,:, ::-1]
    i = nditer(a, [], [['readonly', 'copy']],
            casting='safe',
            op_dtypes=[np.dtype('f8')])
    assert_equal(i.operands[0], a)
    assert_equal(i.operands[0].dtype, np.dtype('f8'))
    assert_equal(i.operands[0].strides, (96, 8, 32))

    # Same-kind cast 'f8' -> 'f4' -> 'f8'
    a = np.arange(24, dtype='f8').reshape(2, 3, 4).T
    i = nditer(a, [],
            [['readwrite', 'updateifcopy']],
            casting='same_kind',
            op_dtypes=[np.dtype('f4')])
    assert_equal(i.operands[0], a)
    assert_equal(i.operands[0].dtype, np.dtype('f4'))
    assert_equal(i.operands[0].strides, (4, 16, 48))
    # Check that UPDATEIFCOPY is activated
    i.operands[0][2, 1, 1] = -12.5
    assert_(a[2, 1, 1] != -12.5)
    i = None
    assert_equal(a[2, 1, 1], -12.5)

    a = np.arange(6, dtype='i4')[::-2]
    i = nditer(a, [],
            [['writeonly', 'updateifcopy']],
            casting='unsafe',
            op_dtypes=[np.dtype('f4')])
    assert_equal(i.operands[0].dtype, np.dtype('f4'))
    # Even though the stride was negative in 'a', it
    # becomes positive in the temporary
    assert_equal(i.operands[0].strides, (4,))
    i.operands[0][:] = [1, 2, 3]
    i = None
    assert_equal(a, [1, 2, 3])

def test_iter_array_cast_errors():
    # Check that invalid casts are caught

    # Need to enable copying for casts to occur
    assert_raises(TypeError, nditer, arange(2, dtype='f4'), [],
                [['readonly']], op_dtypes=[np.dtype('f8')])
    # Also need to allow casting for casts to occur
    assert_raises(TypeError, nditer, arange(2, dtype='f4'), [],
                [['readonly', 'copy']], casting='no',
                op_dtypes=[np.dtype('f8')])
    assert_raises(TypeError, nditer, arange(2, dtype='f4'), [],
                [['readonly', 'copy']], casting='equiv',
                op_dtypes=[np.dtype('f8')])
    assert_raises(TypeError, nditer, arange(2, dtype='f8'), [],
                [['writeonly', 'updateifcopy']],
                casting='no',
                op_dtypes=[np.dtype('f4')])
    assert_raises(TypeError, nditer, arange(2, dtype='f8'), [],
                [['writeonly', 'updateifcopy']],
                casting='equiv',
                op_dtypes=[np.dtype('f4')])
    # '<f4' -> '>f4' should not work with casting='no'
    assert_raises(TypeError, nditer, arange(2, dtype='<f4'), [],
                [['readonly', 'copy']], casting='no',
                op_dtypes=[np.dtype('>f4')])
    # 'f4' -> 'f8' is a safe cast, but 'f8' -> 'f4' isn't
    assert_raises(TypeError, nditer, arange(2, dtype='f4'), [],
                [['readwrite', 'updateifcopy']],
                casting='safe',
                op_dtypes=[np.dtype('f8')])
    assert_raises(TypeError, nditer, arange(2, dtype='f8'), [],
                [['readwrite', 'updateifcopy']],
                casting='safe',
                op_dtypes=[np.dtype('f4')])
    # 'f4' -> 'i4' is neither a safe nor a same-kind cast
    assert_raises(TypeError, nditer, arange(2, dtype='f4'), [],
                [['readonly', 'copy']],
                casting='same_kind',
                op_dtypes=[np.dtype('i4')])
    assert_raises(TypeError, nditer, arange(2, dtype='i4'), [],
                [['writeonly', 'updateifcopy']],
                casting='same_kind',
                op_dtypes=[np.dtype('f4')])

def test_iter_scalar_cast():
    # Check that scalars are cast as requested

    # No cast 'f4' -> 'f4'
    i = nditer(np.float32(2.5), [], [['readonly']],
                    op_dtypes=[np.dtype('f4')])
    assert_equal(i.dtypes[0], np.dtype('f4'))
    assert_equal(i.value.dtype, np.dtype('f4'))
    assert_equal(i.value, 2.5)
    # Safe cast 'f4' -> 'f8'
    i = nditer(np.float32(2.5), [],
                    [['readonly', 'copy']],
                    casting='safe',
                    op_dtypes=[np.dtype('f8')])
    assert_equal(i.dtypes[0], np.dtype('f8'))
    assert_equal(i.value.dtype, np.dtype('f8'))
    assert_equal(i.value, 2.5)
    # Same-kind cast 'f8' -> 'f4'
    i = nditer(np.float64(2.5), [],
                    [['readonly', 'copy']],
                    casting='same_kind',
                    op_dtypes=[np.dtype('f4')])
    assert_equal(i.dtypes[0], np.dtype('f4'))
    assert_equal(i.value.dtype, np.dtype('f4'))
    assert_equal(i.value, 2.5)
    # Unsafe cast 'f8' -> 'i4'
    i = nditer(np.float64(3.0), [],
                    [['readonly', 'copy']],
                    casting='unsafe',
                    op_dtypes=[np.dtype('i4')])
    assert_equal(i.dtypes[0], np.dtype('i4'))
    assert_equal(i.value.dtype, np.dtype('i4'))
    assert_equal(i.value, 3)
    # Readonly scalars may be cast even without setting COPY or BUFFERED
    i = nditer(3, [], [['readonly']], op_dtypes=[np.dtype('f8')])
    assert_equal(i[0].dtype, np.dtype('f8'))
    assert_equal(i[0], 3.)

def test_iter_scalar_cast_errors():
    # Check that invalid casts are caught

    # Need to allow copying/buffering for write casts of scalars to occur
    assert_raises(TypeError, nditer, np.float32(2), [],
                [['readwrite']], op_dtypes=[np.dtype('f8')])
    assert_raises(TypeError, nditer, 2.5, [],
                [['readwrite']], op_dtypes=[np.dtype('f4')])
    # 'f8' -> 'f4' isn't a safe cast if the value would overflow
    assert_raises(TypeError, nditer, np.float64(1e60), [],
                [['readonly']],
                casting='safe',
                op_dtypes=[np.dtype('f4')])
    # 'f4' -> 'i4' is neither a safe nor a same-kind cast
    assert_raises(TypeError, nditer, np.float32(2), [],
                [['readonly']],
                casting='same_kind',
                op_dtypes=[np.dtype('i4')])

def test_iter_object_arrays_basic():
    # Check that object arrays work

    obj = {'a':3,'b':'d'}
    a = np.array([[1, 2, 3], None, obj, None], dtype='O')
    if HAS_REFCOUNT:
        rc = sys.getrefcount(obj)

    # Need to allow references for object arrays
    assert_raises(TypeError, nditer, a)
    if HAS_REFCOUNT:
        assert_equal(sys.getrefcount(obj), rc)

    i = nditer(a, ['refs_ok'], ['readonly'])
    vals = [x_[()] for x_ in i]
    assert_equal(np.array(vals, dtype='O'), a)
    vals, i, x = [None]*3
    if HAS_REFCOUNT:
        assert_equal(sys.getrefcount(obj), rc)

    i = nditer(a.reshape(2, 2).T, ['refs_ok', 'buffered'],
                        ['readonly'], order='C')
    assert_(i.iterationneedsapi)
    vals = [x_[()] for x_ in i]
    assert_equal(np.array(vals, dtype='O'), a.reshape(2, 2).ravel(order='F'))
    vals, i, x = [None]*3
    if HAS_REFCOUNT:
        assert_equal(sys.getrefcount(obj), rc)

    i = nditer(a.reshape(2, 2).T, ['refs_ok', 'buffered'],
                        ['readwrite'], order='C')
    for x in i:
        x[...] = None
    vals, i, x = [None]*3
    if HAS_REFCOUNT:
        assert_(sys.getrefcount(obj) == rc-1)
    assert_equal(a, np.array([None]*4, dtype='O'))

def test_iter_object_arrays_conversions():
    # Conversions to/from objects
    a = np.arange(6, dtype='O')
    i = nditer(a, ['refs_ok', 'buffered'], ['readwrite'],
                    casting='unsafe', op_dtypes='i4')
    for x in i:
        x[...] += 1
    assert_equal(a, np.arange(6)+1)

    a = np.arange(6, dtype='i4')
    i = nditer(a, ['refs_ok', 'buffered'], ['readwrite'],
                    casting='unsafe', op_dtypes='O')
    for x in i:
        x[...] += 1
    assert_equal(a, np.arange(6)+1)

    # Non-contiguous object array
    a = np.zeros((6,), dtype=[('p', 'i1'), ('a', 'O')])
    a = a['a']
    a[:] = np.arange(6)
    i = nditer(a, ['refs_ok', 'buffered'], ['readwrite'],
                    casting='unsafe', op_dtypes='i4')
    for x in i:
        x[...] += 1
    assert_equal(a, np.arange(6)+1)

    #Non-contiguous value array
    a = np.zeros((6,), dtype=[('p', 'i1'), ('a', 'i4')])
    a = a['a']
    a[:] = np.arange(6) + 98172488
    i = nditer(a, ['refs_ok', 'buffered'], ['readwrite'],
                    casting='unsafe', op_dtypes='O')
    ob = i[0][()]
    if HAS_REFCOUNT:
        rc = sys.getrefcount(ob)
    for x in i:
        x[...] += 1
    if HAS_REFCOUNT:
        assert_(sys.getrefcount(ob) == rc-1)
    assert_equal(a, np.arange(6)+98172489)

def test_iter_common_dtype():
    # Check that the iterator finds a common data type correctly

    i = nditer([array([3], dtype='f4'), array([0], dtype='f8')],
                    ['common_dtype'],
                    [['readonly', 'copy']]*2,
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('f8'))
    assert_equal(i.dtypes[1], np.dtype('f8'))
    i = nditer([array([3], dtype='i4'), array([0], dtype='f4')],
                    ['common_dtype'],
                    [['readonly', 'copy']]*2,
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('f8'))
    assert_equal(i.dtypes[1], np.dtype('f8'))
    i = nditer([array([3], dtype='f4'), array(0, dtype='f8')],
                    ['common_dtype'],
                    [['readonly', 'copy']]*2,
                    casting='same_kind')
    assert_equal(i.dtypes[0], np.dtype('f4'))
    assert_equal(i.dtypes[1], np.dtype('f4'))
    i = nditer([array([3], dtype='u4'), array(0, dtype='i4')],
                    ['common_dtype'],
                    [['readonly', 'copy']]*2,
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('u4'))
    assert_equal(i.dtypes[1], np.dtype('u4'))
    i = nditer([array([3], dtype='u4'), array(-12, dtype='i4')],
                    ['common_dtype'],
                    [['readonly', 'copy']]*2,
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('i8'))
    assert_equal(i.dtypes[1], np.dtype('i8'))
    i = nditer([array([3], dtype='u4'), array(-12, dtype='i4'),
                 array([2j], dtype='c8'), array([9], dtype='f8')],
                    ['common_dtype'],
                    [['readonly', 'copy']]*4,
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('c16'))
    assert_equal(i.dtypes[1], np.dtype('c16'))
    assert_equal(i.dtypes[2], np.dtype('c16'))
    assert_equal(i.dtypes[3], np.dtype('c16'))
    assert_equal(i.value, (3, -12, 2j, 9))

    # When allocating outputs, other outputs aren't factored in
    i = nditer([array([3], dtype='i4'), None, array([2j], dtype='c16')], [],
                    [['readonly', 'copy'],
                     ['writeonly', 'allocate'],
                     ['writeonly']],
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('i4'))
    assert_equal(i.dtypes[1], np.dtype('i4'))
    assert_equal(i.dtypes[2], np.dtype('c16'))
    # But, if common data types are requested, they are
    i = nditer([array([3], dtype='i4'), None, array([2j], dtype='c16')],
                    ['common_dtype'],
                    [['readonly', 'copy'],
                     ['writeonly', 'allocate'],
                     ['writeonly']],
                    casting='safe')
    assert_equal(i.dtypes[0], np.dtype('c16'))
    assert_equal(i.dtypes[1], np.dtype('c16'))
    assert_equal(i.dtypes[2], np.dtype('c16'))

def test_iter_op_axes():
    # Check that custom axes work

    # Reverse the axes
    a = arange(6).reshape(2, 3)
    i = nditer([a, a.T], [], [['readonly']]*2, op_axes=[[0, 1], [1, 0]])
    assert_(all([x == y for (x, y) in i]))
    a = arange(24).reshape(2, 3, 4)
    i = nditer([a.T, a], [], [['readonly']]*2, op_axes=[[2, 1, 0], None])
    assert_(all([x == y for (x, y) in i]))

    # Broadcast 1D to any dimension
    a = arange(1, 31).reshape(2, 3, 5)
    b = arange(1, 3)
    i = nditer([a, b], [], [['readonly']]*2, op_axes=[None, [0, -1, -1]])
    assert_equal([x*y for (x, y) in i], (a*b.reshape(2, 1, 1)).ravel())
    b = arange(1, 4)
    i = nditer([a, b], [], [['readonly']]*2, op_axes=[None, [-1, 0, -1]])
    assert_equal([x*y for (x, y) in i], (a*b.reshape(1, 3, 1)).ravel())
    b = arange(1, 6)
    i = nditer([a, b], [], [['readonly']]*2,
                            op_axes=[None, [np.newaxis, np.newaxis, 0]])
    assert_equal([x*y for (x, y) in i], (a*b.reshape(1, 1, 5)).ravel())

    # Inner product-style broadcasting
    a = arange(24).reshape(2, 3, 4)
    b = arange(40).reshape(5, 2, 4)
    i = nditer([a, b], ['multi_index'], [['readonly']]*2,
                            op_axes=[[0, 1, -1, -1], [-1, -1, 0, 1]])
    assert_equal(i.shape, (2, 3, 5, 2))

    # Matrix product-style broadcasting
    a = arange(12).reshape(3, 4)
    b = arange(20).reshape(4, 5)
    i = nditer([a, b], ['multi_index'], [['readonly']]*2,
                            op_axes=[[0, -1], [-1, 1]])
    assert_equal(i.shape, (3, 5))

def test_iter_op_axes_errors():
    # Check that custom axes throws errors for bad inputs

    # Wrong number of items in op_axes
    a = arange(6).reshape(2, 3)
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[0], [1], [0]])
    # Out of bounds items in op_axes
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[2, 1], [0, 1]])
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[0, 1], [2, -1]])
    # Duplicate items in op_axes
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[0, 0], [0, 1]])
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[0, 1], [1, 1]])

    # Different sized arrays in op_axes
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[0, 1], [0, 1, 0]])

    # Non-broadcastable dimensions in the result
    assert_raises(ValueError, nditer, [a, a], [], [['readonly']]*2,
                                    op_axes=[[0, 1], [1, 0]])

def test_iter_copy():
    # Check that copying the iterator works correctly
    a = arange(24).reshape(2, 3, 4)

    # Simple iterator
    i = nditer(a)
    j = i.copy()
    assert_equal([x[()] for x in i], [x[()] for x in j])

    i.iterindex = 3
    j = i.copy()
    assert_equal([x[()] for x in i], [x[()] for x in j])

    # Buffered iterator
    i = nditer(a, ['buffered', 'ranged'], order='F', buffersize=3)
    j = i.copy()
    assert_equal([x[()] for x in i], [x[()] for x in j])

    i.iterindex = 3
    j = i.copy()
    assert_equal([x[()] for x in i], [x[()] for x in j])

    i.iterrange = (3, 9)
    j = i.copy()
    assert_equal([x[()] for x in i], [x[()] for x in j])

    i.iterrange = (2, 18)
    next(i)
    next(i)
    j = i.copy()
    assert_equal([x[()] for x in i], [x[()] for x in j])

    # Casting iterator
    i = nditer(a, ['buffered'], order='F', casting='unsafe',
                op_dtypes='f8', buffersize=5)
    j = i.copy()
    i = None
    assert_equal([x[()] for x in j], a.ravel(order='F'))

    a = arange(24, dtype='<i4').reshape(2, 3, 4)
    i = nditer(a, ['buffered'], order='F', casting='unsafe',
                op_dtypes='>f8', buffersize=5)
    j = i.copy()
    i = None
    assert_equal([x[()] for x in j], a.ravel(order='F'))

def test_iter_allocate_output_simple():
    # Check that the iterator will properly allocate outputs

    # Simple case
    a = arange(6)
    i = nditer([a, None], [], [['readonly'], ['writeonly', 'allocate']],
                        op_dtypes=[None, np.dtype('f4')])
    assert_equal(i.operands[1].shape, a.shape)
    assert_equal(i.operands[1].dtype, np.dtype('f4'))

def test_iter_allocate_output_buffered_readwrite():
    # Allocated output with buffering + delay_bufalloc

    a = arange(6)
    i = nditer([a, None], ['buffered', 'delay_bufalloc'],
                        [['readonly'], ['allocate', 'readwrite']])
    i.operands[1][:] = 1
    i.reset()
    for x in i:
        x[1][...] += x[0][...]
    assert_equal(i.operands[1], a+1)

def test_iter_allocate_output_itorder():
    # The allocated output should match the iteration order

    # C-order input, best iteration order
    a = arange(6, dtype='i4').reshape(2, 3)
    i = nditer([a, None], [], [['readonly'], ['writeonly', 'allocate']],
                        op_dtypes=[None, np.dtype('f4')])
    assert_equal(i.operands[1].shape, a.shape)
    assert_equal(i.operands[1].strides, a.strides)
    assert_equal(i.operands[1].dtype, np.dtype('f4'))
    # F-order input, best iteration order
    a = arange(24, dtype='i4').reshape(2, 3, 4).T
    i = nditer([a, None], [], [['readonly'], ['writeonly', 'allocate']],
                        op_dtypes=[None, np.dtype('f4')])
    assert_equal(i.operands[1].shape, a.shape)
    assert_equal(i.operands[1].strides, a.strides)
    assert_equal(i.operands[1].dtype, np.dtype('f4'))
    # Non-contiguous input, C iteration order
    a = arange(24, dtype='i4').reshape(2, 3, 4).swapaxes(0, 1)
    i = nditer([a, None], [],
                        [['readonly'], ['writeonly', 'allocate']],
                        order='C',
                        op_dtypes=[None, np.dtype('f4')])
    assert_equal(i.operands[1].shape, a.shape)
    assert_equal(i.operands[1].strides, (32, 16, 4))
    assert_equal(i.operands[1].dtype, np.dtype('f4'))

def test_iter_allocate_output_opaxes():
    # Specifing op_axes should work

    a = arange(24, dtype='i4').reshape(2, 3, 4)
    i = nditer([None, a], [], [['writeonly', 'allocate'], ['readonly']],
                        op_dtypes=[np.dtype('u4'), None],
                        op_axes=[[1, 2, 0], None])
    assert_equal(i.operands[0].shape, (4, 2, 3))
    assert_equal(i.operands[0].strides, (4, 48, 16))
    assert_equal(i.operands[0].dtype, np.dtype('u4'))

def test_iter_allocate_output_types_promotion():
    # Check type promotion of automatic outputs

    i = nditer([array([3], dtype='f4'), array([0], dtype='f8'), None], [],
                    [['readonly']]*2+[['writeonly', 'allocate']])
    assert_equal(i.dtypes[2], np.dtype('f8'))
    i = nditer([array([3], dtype='i4'), array([0], dtype='f4'), None], [],
                    [['readonly']]*2+[['writeonly', 'allocate']])
    assert_equal(i.dtypes[2], np.dtype('f8'))
    i = nditer([array([3], dtype='f4'), array(0, dtype='f8'), None], [],
                    [['readonly']]*2+[['writeonly', 'allocate']])
    assert_equal(i.dtypes[2], np.dtype('f4'))
    i = nditer([array([3], dtype='u4'), array(0, dtype='i4'), None], [],
                    [['readonly']]*2+[['writeonly', 'allocate']])
    assert_equal(i.dtypes[2], np.dtype('u4'))
    i = nditer([array([3], dtype='u4'), array(-12, dtype='i4'), None], [],
                    [['readonly']]*2+[['writeonly', 'allocate']])
    assert_equal(i.dtypes[2], np.dtype('i8'))

def test_iter_allocate_output_types_byte_order():
    # Verify the rules for byte order changes

    # When there's just one input, the output type exactly matches
    a = array([3], dtype='u4').newbyteorder()
    i = nditer([a, None], [],
                    [['readonly'], ['writeonly', 'allocate']])
    assert_equal(i.dtypes[0], i.dtypes[1])
    # With two or more inputs, the output type is in native byte order
    i = nditer([a, a, None], [],
                    [['readonly'], ['readonly'], ['writeonly', 'allocate']])
    assert_(i.dtypes[0] != i.dtypes[2])
    assert_equal(i.dtypes[0].newbyteorder('='), i.dtypes[2])

def test_iter_allocate_output_types_scalar():
    # If the inputs are all scalars, the output should be a scalar

    i = nditer([None, 1, 2.3, np.float32(12), np.complex128(3)], [],
                [['writeonly', 'allocate']] + [['readonly']]*4)
    assert_equal(i.operands[0].dtype, np.dtype('complex128'))
    assert_equal(i.operands[0].ndim, 0)

def test_iter_allocate_output_subtype():
    # Make sure that the subtype with priority wins

    # matrix vs ndarray
    a = np.matrix([[1, 2], [3, 4]])
    b = np.arange(4).reshape(2, 2).T
    i = nditer([a, b, None], [],
                    [['readonly'], ['readonly'], ['writeonly', 'allocate']])
    assert_equal(type(a), type(i.operands[2]))
    assert_(type(b) != type(i.operands[2]))
    assert_equal(i.operands[2].shape, (2, 2))

    # matrix always wants things to be 2D
    b = np.arange(4).reshape(1, 2, 2)
    assert_raises(RuntimeError, nditer, [a, b, None], [],
                    [['readonly'], ['readonly'], ['writeonly', 'allocate']])
    # but if subtypes are disabled, the result can still work
    i = nditer([a, b, None], [],
            [['readonly'], ['readonly'], ['writeonly', 'allocate', 'no_subtype']])
    assert_equal(type(b), type(i.operands[2]))
    assert_(type(a) != type(i.operands[2]))
    assert_equal(i.operands[2].shape, (1, 2, 2))

def test_iter_allocate_output_errors():
    # Check that the iterator will throw errors for bad output allocations

    # Need an input if no output data type is specified
    a = arange(6)
    assert_raises(TypeError, nditer, [a, None], [],
                        [['writeonly'], ['writeonly', 'allocate']])
    # Allocated output should be flagged for writing
    assert_raises(ValueError, nditer, [a, None], [],
                        [['readonly'], ['allocate', 'readonly']])
    # Allocated output can't have buffering without delayed bufalloc
    assert_raises(ValueError, nditer, [a, None], ['buffered'],
                                            ['allocate', 'readwrite'])
    # Must specify at least one input
    assert_raises(ValueError, nditer, [None, None], [],
                        [['writeonly', 'allocate'],
                         ['writeonly', 'allocate']],
                        op_dtypes=[np.dtype('f4'), np.dtype('f4')])
    # If using op_axes, must specify all the axes
    a = arange(24, dtype='i4').reshape(2, 3, 4)
    assert_raises(ValueError, nditer, [a, None], [],
                        [['readonly'], ['writeonly', 'allocate']],
                        op_dtypes=[None, np.dtype('f4')],
                        op_axes=[None, [0, np.newaxis, 1]])
    # If using op_axes, the axes must be within bounds
    assert_raises(ValueError, nditer, [a, None], [],
                        [['readonly'], ['writeonly', 'allocate']],
                        op_dtypes=[None, np.dtype('f4')],
                        op_axes=[None, [0, 3, 1]])
    # If using op_axes, there can't be duplicates
    assert_raises(ValueError, nditer, [a, None], [],
                        [['readonly'], ['writeonly', 'allocate']],
                        op_dtypes=[None, np.dtype('f4')],
                        op_axes=[None, [0, 2, 1, 0]])

def test_iter_remove_axis():
    a = arange(24).reshape(2, 3, 4)

    i = nditer(a, ['multi_index'])
    i.remove_axis(1)
    assert_equal([x for x in i], a[:, 0,:].ravel())

    a = a[::-1,:,:]
    i = nditer(a, ['multi_index'])
    i.remove_axis(0)
    assert_equal([x for x in i], a[0,:,:].ravel())

def test_iter_remove_multi_index_inner_loop():
    # Check that removing multi-index support works

    a = arange(24).reshape(2, 3, 4)

    i = nditer(a, ['multi_index'])
    assert_equal(i.ndim, 3)
    assert_equal(i.shape, (2, 3, 4))
    assert_equal(i.itviews[0].shape, (2, 3, 4))

    # Removing the multi-index tracking causes all dimensions to coalesce
    before = [x for x in i]
    i.remove_multi_index()
    after = [x for x in i]

    assert_equal(before, after)
    assert_equal(i.ndim, 1)
    assert_raises(ValueError, lambda i:i.shape, i)
    assert_equal(i.itviews[0].shape, (24,))

    # Removing the inner loop means there's just one iteration
    i.reset()
    assert_equal(i.itersize, 24)
    assert_equal(i[0].shape, tuple())
    i.enable_external_loop()
    assert_equal(i.itersize, 24)
    assert_equal(i[0].shape, (24,))
    assert_equal(i.value, arange(24))

def test_iter_iterindex():
    # Make sure iterindex works

    buffersize = 5
    a = arange(24).reshape(4, 3, 2)
    for flags in ([], ['buffered']):
        i = nditer(a, flags, buffersize=buffersize)
        assert_equal(iter_iterindices(i), list(range(24)))
        i.iterindex = 2
        assert_equal(iter_iterindices(i), list(range(2, 24)))

        i = nditer(a, flags, order='F', buffersize=buffersize)
        assert_equal(iter_iterindices(i), list(range(24)))
        i.iterindex = 5
        assert_equal(iter_iterindices(i), list(range(5, 24)))

        i = nditer(a[::-1], flags, order='F', buffersize=buffersize)
        assert_equal(iter_iterindices(i), list(range(24)))
        i.iterindex = 9
        assert_equal(iter_iterindices(i), list(range(9, 24)))

        i = nditer(a[::-1, ::-1], flags, order='C', buffersize=buffersize)
        assert_equal(iter_iterindices(i), list(range(24)))
        i.iterindex = 13
        assert_equal(iter_iterindices(i), list(range(13, 24)))

        i = nditer(a[::1, ::-1], flags, buffersize=buffersize)
        assert_equal(iter_iterindices(i), list(range(24)))
        i.iterindex = 23
        assert_equal(iter_iterindices(i), list(range(23, 24)))
        i.reset()
        i.iterindex = 2
        assert_equal(iter_iterindices(i), list(range(2, 24)))

def test_iter_iterrange():
    # Make sure getting and resetting the iterrange works

    buffersize = 5
    a = arange(24, dtype='i4').reshape(4, 3, 2)
    a_fort = a.ravel(order='F')

    i = nditer(a, ['ranged'], ['readonly'], order='F',
                buffersize=buffersize)
    assert_equal(i.iterrange, (0, 24))
    assert_equal([x[()] for x in i], a_fort)
    for r in [(0, 24), (1, 2), (3, 24), (5, 5), (0, 20), (23, 24)]:
        i.iterrange = r
        assert_equal(i.iterrange, r)
        assert_equal([x[()] for x in i], a_fort[r[0]:r[1]])

    i = nditer(a, ['ranged', 'buffered'], ['readonly'], order='F',
                op_dtypes='f8', buffersize=buffersize)
    assert_equal(i.iterrange, (0, 24))
    assert_equal([x[()] for x in i], a_fort)
    for r in [(0, 24), (1, 2), (3, 24), (5, 5), (0, 20), (23, 24)]:
        i.iterrange = r
        assert_equal(i.iterrange, r)
        assert_equal([x[()] for x in i], a_fort[r[0]:r[1]])

    def get_array(i):
        val = np.array([], dtype='f8')
        for x in i:
            val = np.concatenate((val, x))
        return val

    i = nditer(a, ['ranged', 'buffered', 'external_loop'],
                ['readonly'], order='F',
                op_dtypes='f8', buffersize=buffersize)
    assert_equal(i.iterrange, (0, 24))
    assert_equal(get_array(i), a_fort)
    for r in [(0, 24), (1, 2), (3, 24), (5, 5), (0, 20), (23, 24)]:
        i.iterrange = r
        assert_equal(i.iterrange, r)
        assert_equal(get_array(i), a_fort[r[0]:r[1]])

def test_iter_buffering():
    # Test buffering with several buffer sizes and types
    arrays = []
    # F-order swapped array
    arrays.append(np.arange(24,
                    dtype='c16').reshape(2, 3, 4).T.newbyteorder().byteswap())
    # Contiguous 1-dimensional array
    arrays.append(np.arange(10, dtype='f4'))
    # Unaligned array
    a = np.zeros((4*16+1,), dtype='i1')[1:]
    a.dtype = 'i4'
    a[:] = np.arange(16, dtype='i4')
    arrays.append(a)
    # 4-D F-order array
    arrays.append(np.arange(120, dtype='i4').reshape(5, 3, 2, 4).T)
    for a in arrays:
        for buffersize in (1, 2, 3, 5, 8, 11, 16, 1024):
            vals = []
            i = nditer(a, ['buffered', 'external_loop'],
                           [['readonly', 'nbo', 'aligned']],
                           order='C',
                           casting='equiv',
                           buffersize=buffersize)
            while not i.finished:
                assert_(i[0].size <= buffersize)
                vals.append(i[0].copy())
                i.iternext()
            assert_equal(np.concatenate(vals), a.ravel(order='C'))

def test_iter_write_buffering():
    # Test that buffering of writes is working

    # F-order swapped array
    a = np.arange(24).reshape(2, 3, 4).T.newbyteorder().byteswap()
    i = nditer(a, ['buffered'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='equiv',
                   order='C',
                   buffersize=16)
    x = 0
    while not i.finished:
        i[0] = x
        x += 1
        i.iternext()
    assert_equal(a.ravel(order='C'), np.arange(24))

def test_iter_buffering_delayed_alloc():
    # Test that delaying buffer allocation works

    a = np.arange(6)
    b = np.arange(1, dtype='f4')
    i = nditer([a, b], ['buffered', 'delay_bufalloc', 'multi_index', 'reduce_ok'],
                    ['readwrite'],
                    casting='unsafe',
                    op_dtypes='f4')
    assert_(i.has_delayed_bufalloc)
    assert_raises(ValueError, lambda i:i.multi_index, i)
    assert_raises(ValueError, lambda i:i[0], i)
    assert_raises(ValueError, lambda i:i[0:2], i)

    def assign_iter(i):
        i[0] = 0
    assert_raises(ValueError, assign_iter, i)

    i.reset()
    assert_(not i.has_delayed_bufalloc)
    assert_equal(i.multi_index, (0,))
    assert_equal(i[0], 0)
    i[1] = 1
    assert_equal(i[0:2], [0, 1])
    assert_equal([[x[0][()], x[1][()]] for x in i], list(zip(range(6), [1]*6)))

def test_iter_buffered_cast_simple():
    # Test that buffering can handle a simple cast

    a = np.arange(10, dtype='f4')
    i = nditer(a, ['buffered', 'external_loop'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='same_kind',
                   op_dtypes=[np.dtype('f8')],
                   buffersize=3)
    for v in i:
        v[...] *= 2

    assert_equal(a, 2*np.arange(10, dtype='f4'))

def test_iter_buffered_cast_byteswapped():
    # Test that buffering can handle a cast which requires swap->cast->swap

    a = np.arange(10, dtype='f4').newbyteorder().byteswap()
    i = nditer(a, ['buffered', 'external_loop'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='same_kind',
                   op_dtypes=[np.dtype('f8').newbyteorder()],
                   buffersize=3)
    for v in i:
        v[...] *= 2

    assert_equal(a, 2*np.arange(10, dtype='f4'))

    with suppress_warnings() as sup:
        sup.filter(np.ComplexWarning)

        a = np.arange(10, dtype='f8').newbyteorder().byteswap()
        i = nditer(a, ['buffered', 'external_loop'],
                       [['readwrite', 'nbo', 'aligned']],
                       casting='unsafe',
                       op_dtypes=[np.dtype('c8').newbyteorder()],
                       buffersize=3)
        for v in i:
            v[...] *= 2

        assert_equal(a, 2*np.arange(10, dtype='f8'))

def test_iter_buffered_cast_byteswapped_complex():
    # Test that buffering can handle a cast which requires swap->cast->copy

    a = np.arange(10, dtype='c8').newbyteorder().byteswap()
    a += 2j
    i = nditer(a, ['buffered', 'external_loop'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='same_kind',
                   op_dtypes=[np.dtype('c16')],
                   buffersize=3)
    for v in i:
        v[...] *= 2
    assert_equal(a, 2*np.arange(10, dtype='c8') + 4j)

    a = np.arange(10, dtype='c8')
    a += 2j
    i = nditer(a, ['buffered', 'external_loop'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='same_kind',
                   op_dtypes=[np.dtype('c16').newbyteorder()],
                   buffersize=3)
    for v in i:
        v[...] *= 2
    assert_equal(a, 2*np.arange(10, dtype='c8') + 4j)

    a = np.arange(10, dtype=np.clongdouble).newbyteorder().byteswap()
    a += 2j
    i = nditer(a, ['buffered', 'external_loop'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='same_kind',
                   op_dtypes=[np.dtype('c16')],
                   buffersize=3)
    for v in i:
        v[...] *= 2
    assert_equal(a, 2*np.arange(10, dtype=np.clongdouble) + 4j)

    a = np.arange(10, dtype=np.longdouble).newbyteorder().byteswap()
    i = nditer(a, ['buffered', 'external_loop'],
                   [['readwrite', 'nbo', 'aligned']],
                   casting='same_kind',
                   op_dtypes=[np.dtype('f4')],
                   buffersize=7)
    for v in i:
        v[...] *= 2
    assert_equal(a, 2*np.arange(10, dtype=np.longdouble))

def test_iter_buffered_cast_structured_type():
    # Tests buffering of structured types

    # simple -> struct type (duplicates the value)
    sdt = [('a', 'f4'), ('b', 'i8'), ('c', 'c8', (2, 3)), ('d', 'O')]
    a = np.arange(3, dtype='f4') + 0.5
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt)
    vals = [np.array(x) for x in i]
    assert_equal(vals[0]['a'], 0.5)
    assert_equal(vals[0]['b'], 0)
    assert_equal(vals[0]['c'], [[(0.5)]*3]*2)
    assert_equal(vals[0]['d'], 0.5)
    assert_equal(vals[1]['a'], 1.5)
    assert_equal(vals[1]['b'], 1)
    assert_equal(vals[1]['c'], [[(1.5)]*3]*2)
    assert_equal(vals[1]['d'], 1.5)
    assert_equal(vals[0].dtype, np.dtype(sdt))

    # object -> struct type
    sdt = [('a', 'f4'), ('b', 'i8'), ('c', 'c8', (2, 3)), ('d', 'O')]
    a = np.zeros((3,), dtype='O')
    a[0] = (0.5, 0.5, [[0.5, 0.5, 0.5], [0.5, 0.5, 0.5]], 0.5)
    a[1] = (1.5, 1.5, [[1.5, 1.5, 1.5], [1.5, 1.5, 1.5]], 1.5)
    a[2] = (2.5, 2.5, [[2.5, 2.5, 2.5], [2.5, 2.5, 2.5]], 2.5)
    if HAS_REFCOUNT:
        rc = sys.getrefcount(a[0])
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt)
    vals = [x.copy() for x in i]
    assert_equal(vals[0]['a'], 0.5)
    assert_equal(vals[0]['b'], 0)
    assert_equal(vals[0]['c'], [[(0.5)]*3]*2)
    assert_equal(vals[0]['d'], 0.5)
    assert_equal(vals[1]['a'], 1.5)
    assert_equal(vals[1]['b'], 1)
    assert_equal(vals[1]['c'], [[(1.5)]*3]*2)
    assert_equal(vals[1]['d'], 1.5)
    assert_equal(vals[0].dtype, np.dtype(sdt))
    vals, i, x = [None]*3
    if HAS_REFCOUNT:
        assert_equal(sys.getrefcount(a[0]), rc)

    # struct type -> simple (takes the first value)
    sdt = [('a', 'f4'), ('b', 'i8'), ('d', 'O')]
    a = np.array([(5.5, 7, 'test'), (8, 10, 11)], dtype=sdt)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes='i4')
    assert_equal([x_[()] for x_ in i], [5, 8])

    # struct type -> struct type (field-wise copy)
    sdt1 = [('a', 'f4'), ('b', 'i8'), ('d', 'O')]
    sdt2 = [('d', 'u2'), ('a', 'O'), ('b', 'f8')]
    a = np.array([(1, 2, 3), (4, 5, 6)], dtype=sdt1)
    # New in 1.12: This behavior changes in 1.13, test for dep warning
    with assert_warns(FutureWarning):
        i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                        casting='unsafe',
                        op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    assert_equal([np.array(x_) for x_ in i],
                 [np.array((3, 1, 2), dtype=sdt2),
                  np.array((6, 4, 5), dtype=sdt2)])

    # struct type -> struct type (field gets discarded)
    sdt1 = [('a', 'f4'), ('b', 'i8'), ('d', 'O')]
    sdt2 = [('b', 'O'), ('a', 'f8')]
    a = np.array([(1, 2, 3), (4, 5, 6)], dtype=sdt1)
    # New in 1.12: This behavior changes in 1.13, test for dep warning
    with assert_warns(FutureWarning):
        i = nditer(a, ['buffered', 'refs_ok'], ['readwrite'],
                        casting='unsafe',
                        op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    vals = []
    for x in i:
        vals.append(np.array(x))
        x['a'] = x['b']+3
    assert_equal(vals, [np.array((2, 1), dtype=sdt2),
                     np.array((5, 4), dtype=sdt2)])
    assert_equal(a, np.array([(5, 2, None), (8, 5, None)], dtype=sdt1))

    # struct type -> struct type (structured field gets discarded)
    sdt1 = [('a', 'f4'), ('b', 'i8'), ('d', [('a', 'i2'), ('b', 'i4')])]
    sdt2 = [('b', 'O'), ('a', 'f8')]
    a = np.array([(1, 2, (0, 9)), (4, 5, (20, 21))], dtype=sdt1)
    # New in 1.12: This behavior changes in 1.13, test for dep warning
    with assert_warns(FutureWarning):
        i = nditer(a, ['buffered', 'refs_ok'], ['readwrite'],
                        casting='unsafe',
                        op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    vals = []
    for x in i:
        vals.append(np.array(x))
        x['a'] = x['b']+3
    assert_equal(vals, [np.array((2, 1), dtype=sdt2),
                     np.array((5, 4), dtype=sdt2)])
    assert_equal(a, np.array([(5, 2, (0, 0)), (8, 5, (0, 0))], dtype=sdt1))

    # struct type -> struct type (structured field w/ ref gets discarded)
    sdt1 = [('a', 'f4'), ('b', 'i8'), ('d', [('a', 'i2'), ('b', 'O')])]
    sdt2 = [('b', 'O'), ('a', 'f8')]
    a = np.array([(1, 2, (0, 9)), (4, 5, (20, 21))], dtype=sdt1)
    # New in 1.12: This behavior changes in 1.13, test for dep warning
    with assert_warns(FutureWarning):
        i = nditer(a, ['buffered', 'refs_ok'], ['readwrite'],
                        casting='unsafe',
                        op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    vals = []
    for x in i:
        vals.append(np.array(x))
        x['a'] = x['b']+3
    assert_equal(vals, [np.array((2, 1), dtype=sdt2),
                     np.array((5, 4), dtype=sdt2)])
    assert_equal(a, np.array([(5, 2, (0, None)), (8, 5, (0, None))], dtype=sdt1))

    # struct type -> struct type back (structured field w/ ref gets discarded)
    sdt1 = [('b', 'O'), ('a', 'f8')]
    sdt2 = [('a', 'f4'), ('b', 'i8'), ('d', [('a', 'i2'), ('b', 'O')])]
    a = np.array([(1, 2), (4, 5)], dtype=sdt1)
    # New in 1.12: This behavior changes in 1.13, test for dep warning
    with assert_warns(FutureWarning):
        i = nditer(a, ['buffered', 'refs_ok'], ['readwrite'],
                        casting='unsafe',
                        op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    vals = []
    for x in i:
        vals.append(np.array(x))
        assert_equal(x['d'], np.array((0, None), dtype=[('a', 'i2'), ('b', 'O')]))
        x['a'] = x['b']+3
    assert_equal(vals, [np.array((2, 1, (0, None)), dtype=sdt2),
                     np.array((5, 4, (0, None)), dtype=sdt2)])
    assert_equal(a, np.array([(1, 4), (4, 7)], dtype=sdt1))

def test_iter_buffered_cast_subarray():
    # Tests buffering of subarrays

    # one element -> many (copies it to all)
    sdt1 = [('a', 'f4')]
    sdt2 = [('a', 'f8', (3, 2, 2))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    for x, count in zip(i, list(range(6))):
        assert_(np.all(x['a'] == count))

    # one element -> many -> back (copies it to all)
    sdt1 = [('a', 'O', (1, 1))]
    sdt2 = [('a', 'O', (3, 2, 2))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'][:, 0, 0] = np.arange(6)
    i = nditer(a, ['buffered', 'refs_ok'], ['readwrite'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_(np.all(x['a'] == count))
        x['a'][0] += 2
        count += 1
    assert_equal(a['a'], np.arange(6).reshape(6, 1, 1)+2)

    # many -> one element -> back (copies just element 0)
    sdt1 = [('a', 'O', (3, 2, 2))]
    sdt2 = [('a', 'O', (1,))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'][:, 0, 0, 0] = np.arange(6)
    i = nditer(a, ['buffered', 'refs_ok'], ['readwrite'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'], count)
        x['a'] += 2
        count += 1
    assert_equal(a['a'], np.arange(6).reshape(6, 1, 1, 1)*np.ones((1, 3, 2, 2))+2)

    # many -> one element -> back (copies just element 0)
    sdt1 = [('a', 'f8', (3, 2, 2))]
    sdt2 = [('a', 'O', (1,))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'][:, 0, 0, 0] = np.arange(6)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'], count)
        count += 1

    # many -> one element (copies just element 0)
    sdt1 = [('a', 'O', (3, 2, 2))]
    sdt2 = [('a', 'f4', (1,))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'][:, 0, 0, 0] = np.arange(6)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'], count)
        count += 1

    # many -> matching shape (straightforward copy)
    sdt1 = [('a', 'O', (3, 2, 2))]
    sdt2 = [('a', 'f4', (3, 2, 2))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6*3*2*2).reshape(6, 3, 2, 2)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'], a[count]['a'])
        count += 1

    # vector -> smaller vector (truncates)
    sdt1 = [('a', 'f8', (6,))]
    sdt2 = [('a', 'f4', (2,))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6*6).reshape(6, 6)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'], a[count]['a'][:2])
        count += 1

    # vector -> bigger vector (pads with zeros)
    sdt1 = [('a', 'f8', (2,))]
    sdt2 = [('a', 'f4', (6,))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6*2).reshape(6, 2)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'][:2], a[count]['a'])
        assert_equal(x['a'][2:], [0, 0, 0, 0])
        count += 1

    # vector -> matrix (broadcasts)
    sdt1 = [('a', 'f8', (2,))]
    sdt2 = [('a', 'f4', (2, 2))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6*2).reshape(6, 2)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'][0], a[count]['a'])
        assert_equal(x['a'][1], a[count]['a'])
        count += 1

    # vector -> matrix (broadcasts and zero-pads)
    sdt1 = [('a', 'f8', (2, 1))]
    sdt2 = [('a', 'f4', (3, 2))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6*2).reshape(6, 2, 1)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'][:2, 0], a[count]['a'][:, 0])
        assert_equal(x['a'][:2, 1], a[count]['a'][:, 0])
        assert_equal(x['a'][2,:], [0, 0])
        count += 1

    # matrix -> matrix (truncates and zero-pads)
    sdt1 = [('a', 'f8', (2, 3))]
    sdt2 = [('a', 'f4', (3, 2))]
    a = np.zeros((6,), dtype=sdt1)
    a['a'] = np.arange(6*2*3).reshape(6, 2, 3)
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe',
                    op_dtypes=sdt2)
    assert_equal(i[0].dtype, np.dtype(sdt2))
    count = 0
    for x in i:
        assert_equal(x['a'][:2, 0], a[count]['a'][:, 0])
        assert_equal(x['a'][:2, 1], a[count]['a'][:, 1])
        assert_equal(x['a'][2,:], [0, 0])
        count += 1

def test_iter_buffering_badwriteback():
    # Writing back from a buffer cannot combine elements

    # a needs write buffering, but had a broadcast dimension
    a = np.arange(6).reshape(2, 3, 1)
    b = np.arange(12).reshape(2, 3, 2)
    assert_raises(ValueError, nditer, [a, b],
                  ['buffered', 'external_loop'],
                  [['readwrite'], ['writeonly']],
                  order='C')

    # But if a is readonly, it's fine
    nditer([a, b], ['buffered', 'external_loop'],
           [['readonly'], ['writeonly']],
           order='C')

    # If a has just one element, it's fine too (constant 0 stride, a reduction)
    a = np.arange(1).reshape(1, 1, 1)
    nditer([a, b], ['buffered', 'external_loop', 'reduce_ok'],
           [['readwrite'], ['writeonly']],
           order='C')

    # check that it fails on other dimensions too
    a = np.arange(6).reshape(1, 3, 2)
    assert_raises(ValueError, nditer, [a, b],
                  ['buffered', 'external_loop'],
                  [['readwrite'], ['writeonly']],
                  order='C')
    a = np.arange(4).reshape(2, 1, 2)
    assert_raises(ValueError, nditer, [a, b],
                  ['buffered', 'external_loop'],
                  [['readwrite'], ['writeonly']],
                  order='C')

def test_iter_buffering_string():
    # Safe casting disallows shrinking strings
    a = np.array(['abc', 'a', 'abcd'], dtype=np.bytes_)
    assert_equal(a.dtype, np.dtype('S4'))
    assert_raises(TypeError, nditer, a, ['buffered'], ['readonly'],
                  op_dtypes='S2')
    i = nditer(a, ['buffered'], ['readonly'], op_dtypes='S6')
    assert_equal(i[0], asbytes('abc'))
    assert_equal(i[0].dtype, np.dtype('S6'))

    a = np.array(['abc', 'a', 'abcd'], dtype=np.unicode)
    assert_equal(a.dtype, np.dtype('U4'))
    assert_raises(TypeError, nditer, a, ['buffered'], ['readonly'],
                    op_dtypes='U2')
    i = nditer(a, ['buffered'], ['readonly'], op_dtypes='U6')
    assert_equal(i[0], sixu('abc'))
    assert_equal(i[0].dtype, np.dtype('U6'))

def test_iter_buffering_growinner():
    # Test that the inner loop grows when no buffering is needed
    a = np.arange(30)
    i = nditer(a, ['buffered', 'growinner', 'external_loop'],
                           buffersize=5)
    # Should end up with just one inner loop here
    assert_equal(i[0].size, a.size)


@dec.slow
def test_iter_buffered_reduce_reuse():
    # large enough array for all views, including negative strides.
    a = np.arange(2*3**5)[3**5:3**5+1]
    flags = ['buffered', 'delay_bufalloc', 'multi_index', 'reduce_ok', 'refs_ok']
    op_flags = [('readonly',), ('readwrite', 'allocate')]
    op_axes_list = [[(0, 1, 2), (0, 1, -1)], [(0, 1, 2), (0, -1, -1)]]
    # wrong dtype to force buffering
    op_dtypes = [np.float, a.dtype]

    def get_params():
        for xs in range(-3**2, 3**2 + 1):
            for ys in range(xs, 3**2 + 1):
                for op_axes in op_axes_list:
                    # last stride is reduced and because of that not
                    # important for this test, as it is the inner stride.
                    strides = (xs * a.itemsize, ys * a.itemsize, a.itemsize)
                    arr = np.lib.stride_tricks.as_strided(a, (3, 3, 3), strides)

                    for skip in [0, 1]:
                        yield arr, op_axes, skip

    for arr, op_axes, skip in get_params():
        nditer2 = np.nditer([arr.copy(), None],
                            op_axes=op_axes, flags=flags, op_flags=op_flags,
                            op_dtypes=op_dtypes)
        nditer2.operands[-1][...] = 0
        nditer2.reset()
        nditer2.iterindex = skip

        for (a2_in, b2_in) in nditer2:
            b2_in += a2_in.astype(np.int_)

        comp_res = nditer2.operands[-1]

        for bufsize in range(0, 3**3):
            nditer1 = np.nditer([arr, None],
                                op_axes=op_axes, flags=flags, op_flags=op_flags,
                                buffersize=bufsize, op_dtypes=op_dtypes)
            nditer1.operands[-1][...] = 0
            nditer1.reset()
            nditer1.iterindex = skip

            for (a1_in, b1_in) in nditer1:
                b1_in += a1_in.astype(np.int_)

            res = nditer1.operands[-1]
            assert_array_equal(res, comp_res)


def test_iter_no_broadcast():
    # Test that the no_broadcast flag works
    a = np.arange(24).reshape(2, 3, 4)
    b = np.arange(6).reshape(2, 3, 1)
    c = np.arange(12).reshape(3, 4)

    nditer([a, b, c], [],
           [['readonly', 'no_broadcast'],
            ['readonly'], ['readonly']])
    assert_raises(ValueError, nditer, [a, b, c], [],
                  [['readonly'], ['readonly', 'no_broadcast'], ['readonly']])
    assert_raises(ValueError, nditer, [a, b, c], [],
                  [['readonly'], ['readonly'], ['readonly', 'no_broadcast']])

def test_iter_nested_iters_basic():
    # Test nested iteration basic usage
    a = arange(12).reshape(2, 3, 2)

    i, j = np.nested_iters(a, [[0], [1, 2]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]])

    i, j = np.nested_iters(a, [[0, 1], [2]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]])

    i, j = np.nested_iters(a, [[0, 2], [1]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 2, 4], [1, 3, 5], [6, 8, 10], [7, 9, 11]])

def test_iter_nested_iters_reorder():
    # Test nested iteration basic usage
    a = arange(12).reshape(2, 3, 2)

    # In 'K' order (default), it gets reordered
    i, j = np.nested_iters(a, [[0], [2, 1]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]])

    i, j = np.nested_iters(a, [[1, 0], [2]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]])

    i, j = np.nested_iters(a, [[2, 0], [1]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 2, 4], [1, 3, 5], [6, 8, 10], [7, 9, 11]])

    # In 'C' order, it doesn't
    i, j = np.nested_iters(a, [[0], [2, 1]], order='C')
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 2, 4, 1, 3, 5], [6, 8, 10, 7, 9, 11]])

    i, j = np.nested_iters(a, [[1, 0], [2]], order='C')
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1], [6, 7], [2, 3], [8, 9], [4, 5], [10, 11]])

    i, j = np.nested_iters(a, [[2, 0], [1]], order='C')
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 2, 4], [6, 8, 10], [1, 3, 5], [7, 9, 11]])

def test_iter_nested_iters_flip_axes():
    # Test nested iteration with negative axes
    a = arange(12).reshape(2, 3, 2)[::-1, ::-1, ::-1]

    # In 'K' order (default), the axes all get flipped
    i, j = np.nested_iters(a, [[0], [1, 2]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]])

    i, j = np.nested_iters(a, [[0, 1], [2]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11]])

    i, j = np.nested_iters(a, [[0, 2], [1]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 2, 4], [1, 3, 5], [6, 8, 10], [7, 9, 11]])

    # In 'C' order, flipping axes is disabled
    i, j = np.nested_iters(a, [[0], [1, 2]], order='C')
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[11, 10, 9, 8, 7, 6], [5, 4, 3, 2, 1, 0]])

    i, j = np.nested_iters(a, [[0, 1], [2]], order='C')
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[11, 10], [9, 8], [7, 6], [5, 4], [3, 2], [1, 0]])

    i, j = np.nested_iters(a, [[0, 2], [1]], order='C')
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[11, 9, 7], [10, 8, 6], [5, 3, 1], [4, 2, 0]])

def test_iter_nested_iters_broadcast():
    # Test nested iteration with broadcasting
    a = arange(2).reshape(2, 1)
    b = arange(3).reshape(1, 3)

    i, j = np.nested_iters([a, b], [[0], [1]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[[0, 0], [0, 1], [0, 2]], [[1, 0], [1, 1], [1, 2]]])

    i, j = np.nested_iters([a, b], [[1], [0]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[[0, 0], [1, 0]], [[0, 1], [1, 1]], [[0, 2], [1, 2]]])

def test_iter_nested_iters_dtype_copy():
    # Test nested iteration with a copy to change dtype

    # copy
    a = arange(6, dtype='i4').reshape(2, 3)
    i, j = np.nested_iters(a, [[0], [1]],
                        op_flags=['readonly', 'copy'],
                        op_dtypes='f8')
    assert_equal(j[0].dtype, np.dtype('f8'))
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1, 2], [3, 4, 5]])
    vals = None

    # updateifcopy
    a = arange(6, dtype='f4').reshape(2, 3)
    i, j = np.nested_iters(a, [[0], [1]],
                        op_flags=['readwrite', 'updateifcopy'],
                        casting='same_kind',
                        op_dtypes='f8')
    assert_equal(j[0].dtype, np.dtype('f8'))
    for x in i:
        for y in j:
            y[...] += 1
    assert_equal(a, [[0, 1, 2], [3, 4, 5]])
    i, j, x, y = (None,)*4  # force the updateifcopy
    assert_equal(a, [[1, 2, 3], [4, 5, 6]])

def test_iter_nested_iters_dtype_buffered():
    # Test nested iteration with buffering to change dtype

    a = arange(6, dtype='f4').reshape(2, 3)
    i, j = np.nested_iters(a, [[0], [1]],
                        flags=['buffered'],
                        op_flags=['readwrite'],
                        casting='same_kind',
                        op_dtypes='f8')
    assert_equal(j[0].dtype, np.dtype('f8'))
    for x in i:
        for y in j:
            y[...] += 1
    assert_equal(a, [[1, 2, 3], [4, 5, 6]])

def test_iter_reduction_error():

    a = np.arange(6)
    assert_raises(ValueError, nditer, [a, None], [],
                    [['readonly'], ['readwrite', 'allocate']],
                    op_axes=[[0], [-1]])

    a = np.arange(6).reshape(2, 3)
    assert_raises(ValueError, nditer, [a, None], ['external_loop'],
                    [['readonly'], ['readwrite', 'allocate']],
                    op_axes=[[0, 1], [-1, -1]])

def test_iter_reduction():
    # Test doing reductions with the iterator

    a = np.arange(6)
    i = nditer([a, None], ['reduce_ok'],
                    [['readonly'], ['readwrite', 'allocate']],
                    op_axes=[[0], [-1]])
    # Need to initialize the output operand to the addition unit
    i.operands[1][...] = 0
    # Do the reduction
    for x, y in i:
        y[...] += x
    # Since no axes were specified, should have allocated a scalar
    assert_equal(i.operands[1].ndim, 0)
    assert_equal(i.operands[1], np.sum(a))

    a = np.arange(6).reshape(2, 3)
    i = nditer([a, None], ['reduce_ok', 'external_loop'],
                    [['readonly'], ['readwrite', 'allocate']],
                    op_axes=[[0, 1], [-1, -1]])
    # Need to initialize the output operand to the addition unit
    i.operands[1][...] = 0
    # Reduction shape/strides for the output
    assert_equal(i[1].shape, (6,))
    assert_equal(i[1].strides, (0,))
    # Do the reduction
    for x, y in i:
        y[...] += x
    # Since no axes were specified, should have allocated a scalar
    assert_equal(i.operands[1].ndim, 0)
    assert_equal(i.operands[1], np.sum(a))

    # This is a tricky reduction case for the buffering double loop
    # to handle
    a = np.ones((2, 3, 5))
    it1 = nditer([a, None], ['reduce_ok', 'external_loop'],
                    [['readonly'], ['readwrite', 'allocate']],
                    op_axes=[None, [0, -1, 1]])
    it2 = nditer([a, None], ['reduce_ok', 'external_loop',
                            'buffered', 'delay_bufalloc'],
                    [['readonly'], ['readwrite', 'allocate']],
                    op_axes=[None, [0, -1, 1]], buffersize=10)
    it1.operands[1].fill(0)
    it2.operands[1].fill(0)
    it2.reset()
    for x in it1:
        x[1][...] += x[0]
    for x in it2:
        x[1][...] += x[0]
    assert_equal(it1.operands[1], it2.operands[1])
    assert_equal(it2.operands[1].sum(), a.size)

def test_iter_buffering_reduction():
    # Test doing buffered reductions with the iterator

    a = np.arange(6)
    b = np.array(0., dtype='f8').byteswap().newbyteorder()
    i = nditer([a, b], ['reduce_ok', 'buffered'],
                    [['readonly'], ['readwrite', 'nbo']],
                    op_axes=[[0], [-1]])
    assert_equal(i[1].dtype, np.dtype('f8'))
    assert_(i[1].dtype != b.dtype)
    # Do the reduction
    for x, y in i:
        y[...] += x
    # Since no axes were specified, should have allocated a scalar
    assert_equal(b, np.sum(a))

    a = np.arange(6).reshape(2, 3)
    b = np.array([0, 0], dtype='f8').byteswap().newbyteorder()
    i = nditer([a, b], ['reduce_ok', 'external_loop', 'buffered'],
                    [['readonly'], ['readwrite', 'nbo']],
                    op_axes=[[0, 1], [0, -1]])
    # Reduction shape/strides for the output
    assert_equal(i[1].shape, (3,))
    assert_equal(i[1].strides, (0,))
    # Do the reduction
    for x, y in i:
        y[...] += x
    assert_equal(b, np.sum(a, axis=1))

    # Iterator inner double loop was wrong on this one
    p = np.arange(2) + 1
    it = np.nditer([p, None],
            ['delay_bufalloc', 'reduce_ok', 'buffered', 'external_loop'],
            [['readonly'], ['readwrite', 'allocate']],
            op_axes=[[-1, 0], [-1, -1]],
            itershape=(2, 2))
    it.operands[1].fill(0)
    it.reset()
    assert_equal(it[0], [1, 2, 1, 2])

    # Iterator inner loop should take argument contiguity into account
    x = np.ones((7, 13, 8), np.int8)[4:6,1:11:6,1:5].transpose(1, 2, 0)
    x[...] = np.arange(x.size).reshape(x.shape)
    y_base = np.arange(4*4, dtype=np.int8).reshape(4, 4)
    y_base_copy = y_base.copy()
    y = y_base[::2,:,None]

    it = np.nditer([y, x],
                   ['buffered', 'external_loop', 'reduce_ok'],
                   [['readwrite'], ['readonly']])
    for a, b in it:
        a.fill(2)

    assert_equal(y_base[1::2], y_base_copy[1::2])
    assert_equal(y_base[::2], 2)

def test_iter_buffering_reduction_reuse_reduce_loops():
    # There was a bug triggering reuse of the reduce loop inappropriately,
    # which caused processing to happen in unnecessarily small chunks
    # and overran the buffer.

    a = np.zeros((2, 7))
    b = np.zeros((1, 7))
    it = np.nditer([a, b], flags=['reduce_ok', 'external_loop', 'buffered'],
                    op_flags=[['readonly'], ['readwrite']],
                    buffersize=5)

    bufsizes = []
    for x, y in it:
        bufsizes.append(x.shape[0])
    assert_equal(bufsizes, [5, 2, 5, 2])
    assert_equal(sum(bufsizes), a.size)

def test_iter_writemasked_badinput():
    a = np.zeros((2, 3))
    b = np.zeros((3,))
    m = np.array([[True, True, False], [False, True, False]])
    m2 = np.array([True, True, False])
    m3 = np.array([0, 1, 1], dtype='u1')
    mbad1 = np.array([0, 1, 1], dtype='i1')
    mbad2 = np.array([0, 1, 1], dtype='f4')

    # Need an 'arraymask' if any operand is 'writemasked'
    assert_raises(ValueError, nditer, [a, m], [],
                    [['readwrite', 'writemasked'], ['readonly']])

    # A 'writemasked' operand must not be readonly
    assert_raises(ValueError, nditer, [a, m], [],
                    [['readonly', 'writemasked'], ['readonly', 'arraymask']])

    # 'writemasked' and 'arraymask' may not be used together
    assert_raises(ValueError, nditer, [a, m], [],
                    [['readonly'], ['readwrite', 'arraymask', 'writemasked']])

    # 'arraymask' may only be specified once
    assert_raises(ValueError, nditer, [a, m, m2], [],
                    [['readwrite', 'writemasked'],
                     ['readonly', 'arraymask'],
                     ['readonly', 'arraymask']])

    # An 'arraymask' with nothing 'writemasked' also doesn't make sense
    assert_raises(ValueError, nditer, [a, m], [],
                    [['readwrite'], ['readonly', 'arraymask']])

    # A writemasked reduction requires a similarly smaller mask
    assert_raises(ValueError, nditer, [a, b, m], ['reduce_ok'],
                    [['readonly'],
                     ['readwrite', 'writemasked'],
                     ['readonly', 'arraymask']])
    # But this should work with a smaller/equal mask to the reduction operand
    np.nditer([a, b, m2], ['reduce_ok'],
                    [['readonly'],
                     ['readwrite', 'writemasked'],
                     ['readonly', 'arraymask']])
    # The arraymask itself cannot be a reduction
    assert_raises(ValueError, nditer, [a, b, m2], ['reduce_ok'],
                    [['readonly'],
                     ['readwrite', 'writemasked'],
                     ['readwrite', 'arraymask']])

    # A uint8 mask is ok too
    np.nditer([a, m3], ['buffered'],
                    [['readwrite', 'writemasked'],
                     ['readonly', 'arraymask']],
                    op_dtypes=['f4', None],
                    casting='same_kind')
    # An int8 mask isn't ok
    assert_raises(TypeError, np.nditer, [a, mbad1], ['buffered'],
                    [['readwrite', 'writemasked'],
                     ['readonly', 'arraymask']],
                    op_dtypes=['f4', None],
                    casting='same_kind')
    # A float32 mask isn't ok
    assert_raises(TypeError, np.nditer, [a, mbad2], ['buffered'],
                    [['readwrite', 'writemasked'],
                     ['readonly', 'arraymask']],
                    op_dtypes=['f4', None],
                    casting='same_kind')

def test_iter_writemasked():
    a = np.zeros((3,), dtype='f8')
    msk = np.array([True, True, False])

    # When buffering is unused, 'writemasked' effectively does nothing.
    # It's up to the user of the iterator to obey the requested semantics.
    it = np.nditer([a, msk], [],
                [['readwrite', 'writemasked'],
                 ['readonly', 'arraymask']])
    for x, m in it:
        x[...] = 1
    # Because we violated the semantics, all the values became 1
    assert_equal(a, [1, 1, 1])

    # Even if buffering is enabled, we still may be accessing the array
    # directly.
    it = np.nditer([a, msk], ['buffered'],
                [['readwrite', 'writemasked'],
                 ['readonly', 'arraymask']])
    for x, m in it:
        x[...] = 2.5
    # Because we violated the semantics, all the values became 2.5
    assert_equal(a, [2.5, 2.5, 2.5])

    # If buffering will definitely happening, for instance because of
    # a cast, only the items selected by the mask will be copied back from
    # the buffer.
    it = np.nditer([a, msk], ['buffered'],
                [['readwrite', 'writemasked'],
                 ['readonly', 'arraymask']],
                op_dtypes=['i8', None],
                casting='unsafe')
    for x, m in it:
        x[...] = 3
    # Even though we violated the semantics, only the selected values
    # were copied back
    assert_equal(a, [3, 3, 2.5])

def test_iter_non_writable_attribute_deletion():
    it = np.nditer(np.ones(2))
    attr = ["value", "shape", "operands", "itviews", "has_delayed_bufalloc",
            "iterationneedsapi", "has_multi_index", "has_index", "dtypes",
            "ndim", "nop", "itersize", "finished"]

    for s in attr:
        assert_raises(AttributeError, delattr, it, s)


def test_iter_writable_attribute_deletion():
    it = np.nditer(np.ones(2))
    attr = [ "multi_index", "index", "iterrange", "iterindex"]
    for s in attr:
        assert_raises(AttributeError, delattr, it, s)


def test_iter_element_deletion():
    it = np.nditer(np.ones(3))
    try:
        del it[1]
        del it[1:2]
    except TypeError:
        pass
    except:
        raise AssertionError

def test_iter_allocated_array_dtypes():
    # If the dtype of an allocated output has a shape, the shape gets
    # tacked onto the end of the result.
    it = np.nditer(([1, 3, 20], None), op_dtypes=[None, ('i4', (2,))])
    for a, b in it:
        b[0] = a - 1
        b[1] = a + 1
    assert_equal(it.operands[1], [[0, 2], [2, 4], [19, 21]])

    # Make sure this works for scalars too
    it = np.nditer((10, 2, None), op_dtypes=[None, None, ('i4', (2, 2))])
    for a, b, c in it:
        c[0, 0] = a - b
        c[0, 1] = a + b
        c[1, 0] = a * b
        c[1, 1] = a / b
    assert_equal(it.operands[2], [[8, 12], [20, 5]])


def test_0d_iter():
    # Basic test for iteration of 0-d arrays:
    i = nditer([2, 3], ['multi_index'], [['readonly']]*2)
    assert_equal(i.ndim, 0)
    assert_equal(next(i), (2, 3))
    assert_equal(i.multi_index, ())
    assert_equal(i.iterindex, 0)
    assert_raises(StopIteration, next, i)
    # test reset:
    i.reset()
    assert_equal(next(i), (2, 3))
    assert_raises(StopIteration, next, i)

    # test forcing to 0-d
    i = nditer(np.arange(5), ['multi_index'], [['readonly']], op_axes=[()])
    assert_equal(i.ndim, 0)
    assert_equal(len(i), 1)
    # note that itershape=(), still behaves like None due to the conversions

    # Test a more complex buffered casting case (same as another test above)
    sdt = [('a', 'f4'), ('b', 'i8'), ('c', 'c8', (2, 3)), ('d', 'O')]
    a = np.array(0.5, dtype='f4')
    i = nditer(a, ['buffered', 'refs_ok'], ['readonly'],
                    casting='unsafe', op_dtypes=sdt)
    vals = next(i)
    assert_equal(vals['a'], 0.5)
    assert_equal(vals['b'], 0)
    assert_equal(vals['c'], [[(0.5)]*3]*2)
    assert_equal(vals['d'], 0.5)


def test_0d_nested_iter():
    a = np.arange(12).reshape(2, 3, 2)
    i, j = np.nested_iters(a, [[], [1, 0, 2]])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]])

    i, j = np.nested_iters(a, [[1, 0, 2], []])
    vals = []
    for x in i:
        vals.append([y for y in j])
    assert_equal(vals, [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11]])

    i, j, k = np.nested_iters(a, [[2, 0], [], [1]])
    vals = []
    for x in i:
        for y in j:
            vals.append([z for z in k])
    assert_equal(vals, [[0, 2, 4], [1, 3, 5], [6, 8, 10], [7, 9, 11]])


def test_iter_too_large():
    # The total size of the iterator must not exceed the maximum intp due
    # to broadcasting. Dividing by 1024 will keep it small enough to
    # give a legal array.
    size = np.iinfo(np.intp).max // 1024
    arr = np.lib.stride_tricks.as_strided(np.zeros(1), (size,), (0,))
    assert_raises(ValueError, nditer, (arr, arr[:, None]))
    # test the same for multiindex. That may get more interesting when
    # removing 0 dimensional axis is allowed (since an iterator can grow then)
    assert_raises(ValueError, nditer,
                  (arr, arr[:, None]), flags=['multi_index'])


def test_iter_too_large_with_multiindex():
    # When a multi index is being tracked, the error is delayed this
    # checks the delayed error messages and getting below that by
    # removing an axis.
    base_size = 2**10
    num = 1
    while base_size**num < np.iinfo(np.intp).max:
        num += 1

    shape_template = [1, 1] * num
    arrays = []
    for i in range(num):
        shape = shape_template[:]
        shape[i * 2] = 2**10
        arrays.append(np.empty(shape))
    arrays = tuple(arrays)

    # arrays are now too large to be broadcast. The different modes test
    # different nditer functionality with or without GIL.
    for mode in range(6):
        assert_raises(ValueError, test_nditer_too_large, arrays, -1, mode)
    # but if we do nothing with the nditer, it can be constructed:
    test_nditer_too_large(arrays, -1, 7)

    # When an axis is removed, things should work again (half the time):
    for i in range(num):
        for mode in range(6):
            # an axis with size 1024 is removed:
            test_nditer_too_large(arrays, i*2, mode)
            # an axis with size 1 is removed:
            assert_raises(ValueError, test_nditer_too_large,
                          arrays, i*2 + 1, mode)


if __name__ == "__main__":
    run_module_suite()
