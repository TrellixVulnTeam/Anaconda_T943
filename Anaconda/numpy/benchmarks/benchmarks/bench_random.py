from __future__ import absolute_import, division, print_function

from .common import Benchmark

import numpy as np
from numpy.lib import NumpyVersion


class Random(Benchmark):
    params = ['normal', 'uniform', 'weibull 1', 'binomial 10 0.5',
              'poisson 10']

    def setup(self, name):
        items = name.split()
        name = items.pop(0)
        params = [float(x) for x in items]

        self.func = getattr(np.random, name)
        self.params = tuple(params) + ((100, 100),)

    def time_rng(self, name):
        self.func(*self.params)


class Shuffle(Benchmark):
    def setup(self):
        self.a = np.arange(100000)

    def time_100000(self):
        np.random.shuffle(self.a)


class Randint(Benchmark):

    def time_randint_fast(self):
        """Compare to uint32 below"""
        np.random.randint(0, 2**30, size=10**5)

    def time_randint_slow(self):
        """Compare to uint32 below"""
        np.random.randint(0, 2**30 + 1, size=10**5)


class Randint_dtype(Benchmark):
    high = {
        'bool': 1,
        'uint8': 2**7,
        'uint16': 2**15,
        'uint32': 2**31,
        'uint64': 2**63
        }

    param_names = ['dtype']
    params = ['bool', 'uint8', 'uint16', 'uint32', 'uint64']

    def setup(self, name):
        if NumpyVersion(np.__version__) < '1.11.0.dev0':
            raise NotImplementedError

    def time_randint_fast(self, name):
        high = self.high[name]
        np.random.randint(0, high, size=10**5, dtype=name)

    def time_randint_slow(self, name):
        high = self.high[name]
        np.random.randint(0, high + 1, size=10**5, dtype=name)

