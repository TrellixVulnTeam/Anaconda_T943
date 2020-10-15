import numpy as np
from scipy import optimize as opt
from hexrd.constants import *
from hexrd import USE_NUMBA
if USE_NUMBA:
    import numba

def dummy(xy_in, params, invert=False):
    """
    """
    return xy_in

def newton(x0, f, fp, extra, prec=3e-16, maxiter=100):
    for i in range(maxiter):
        x = x0 - f(x0, *extra) / fp(x0, *extra)
        relerr = np.max(np.abs(x - x0)) / np.max(np.abs(x))
        if relerr < prec:
            # print 'stopping at %d iters' % i
            return x
        x0 = x
    return x0

if USE_NUMBA:
    @numba.njit
    def _ge_41rt_inverse_distortion(out, in_, rhoMax, params):
        maxiter = 100
        prec = epsf

        p0, p1, p2, p3, p4, p5 = params[0:6]
        rxi = 1.0/rhoMax
        for el in range(len(in_)):
            xi, yi = in_[el, 0:2]
            ri = np.sqrt(xi*xi + yi*yi)
            if ri < sqrt_epsf:
                ri_inv = 0.0
            else:
                ri_inv = 1.0/ri
            sinni = yi*ri_inv
            cosni = xi*ri_inv
            ro = ri
            cos2ni = cosni*cosni - sinni*sinni
            sin2ni = 2*sinni*cosni
            cos4ni = cos2ni*cos2ni - sin2ni*sin2ni
            for i in range(maxiter): # newton solver iteration
                ratio = ri*rxi
                fx = (p0*ratio**p3*cos2ni +
                      p1*ratio**p4*cos4ni +
                      p2*ratio**p5 + 1)*ri - ro # f(x)
                fxp = (p0*ratio**p3*cos2ni*(p3+1) +
                       p1*ratio**p4*cos4ni*(p4+1) +
                       p2*ratio**p5*(p5+1) + 1) # f'(x)

                delta = fx/fxp
                ri = ri - delta
                if np.abs(delta) <= prec*np.abs(ri): # convergence check for newton
                    break

            xi = ri*cosni
            yi = ri*sinni
            out[el, 0] = xi
            out[el, 1] = yi

        return out


    @numba.njit
    def _ge_41rt_distortion(out, in_, rhoMax, params):
        p0, p1, p2, p3, p4, p5 = params[0:6]
        rxi = 1.0/rhoMax

        for el in range(len(in_)):
            xi, yi = in_[el, 0:2]
            ri = np.sqrt(xi*xi + yi*yi)
            if ri < sqrt_epsf:
                ri_inv = 0.0
            else:
                ri_inv = 1.0/ri
            sinni = yi*ri_inv
            cosni = xi*ri_inv
            cos2ni = cosni*cosni - sinni*sinni
            sin2ni = 2*sinni*cosni
            cos4ni = cos2ni*cos2ni - sin2ni*sin2ni
            ratio = ri*rxi

            ri = (p0*ratio**p3*cos2ni + p1*ratio**p4*cos4ni + p2*ratio**p5 + 1)*ri
            xi = ri*cosni
            yi = ri*sinni
            out[el, 0] = xi
            out[el, 1] = yi

        return out
else:
    # non-numba versions for the direct and inverse distortion
    def _ge_41rt_inverse_distortion(out, in_, rhoMax, params):
        maxiter = 100
        prec = epsf

        p0, p1, p2, p3, p4, p5 = params[0:6]
        rxi = 1.0/rhoMax

        xi, yi = in_[:, 0], in_[:,1]
        ri = np.sqrt(xi*xi + yi*yi)
        if ri < sqrt_epsf:
            ri_inv = 0.0
        else:
            ri_inv = 1.0/ri
        sinni = yi*ri_inv
        cosni = xi*ri_inv
        ro = ri
        cos2ni = cosni*cosni - sinni*sinni
        sin2ni = 2*sinni*cosni
        cos4ni = cos2ni*cos2ni - sin2ni*sin2ni

        for i in range(maxiter): # newton solver iteration
            ratio = ri*rxi
            fx = (p0*ratio**p3*cos2ni +
                  p1*ratio**p4*cos4ni +
                  p2*ratio**p5 + 1)*ri - ro # f(x)
            fxp = (p0*ratio**p3*cos2ni*(p3+1) +
                   p1*ratio**p4*cos4ni*(p4+1) +
                   p2*ratio**p5*(p5+1) + 1) # f'(x)

            delta = fx/fxp
            ri = ri - delta

            if np.max(np.abs(delta/ri)) <= prec: # convergence check for newton
                break

        out[:, 0] = ri*cosni
        out[:, 1] = ri*sinni

        return out

    def _ge_41rt_distortion(out, in_, rhoMax, params):
        p0, p1, p2, p3, p4, p5 = params[0:6]
        rxi = 1.0/rhoMax

        xi, yi = in_[:, 0], in_[:,1]
        ri = np.sqrt(xi*xi + yi*yi)
        if ri < sqrt_epsf:
            ri_inv = 0.0
        else:
            ri_inv = 1.0/ri
        sinni = yi*ri_inv
        cosni = xi*ri_inv
        cos2ni = cosni*cosni - sinni*sinni
        sin2ni = 2*sinni*cosni
        cos4ni = cos2ni*cos2ni - sin2ni*sin2ni
        ratio = ri*rxi

        ri = (p0*ratio**p3*cos2ni + p1*ratio**p4*cos4ni + p2*ratio**p5 + 1)*ri
        out[:,0] = ri*cosni
        out[:,1] = ri*sinni

        return out

def inverse_distortion_numpy(rho0, eta0, rhoMax, params):
    rhoSclFuncInv = lambda ri, ni, ro, rx, p: \
        (p[0]*(ri/rx)**p[3] * np.cos(2.0 * ni) + \
         p[1]*(ri/rx)**p[4] * np.cos(4.0 * ni) + \
         p[2]*(ri/rx)**p[5] + 1)*ri - ro

    rhoSclFIprime = lambda ri, ni, ro, rx, p: \
        p[0]*(ri/rx)**p[3] * np.cos(2.0 * ni) * (p[3] + 1) + \
        p[1]*(ri/rx)**p[4] * np.cos(4.0 * ni) * (p[4] + 1) + \
        p[2]*(ri/rx)**p[5] * (p[5] + 1) + 1

    return newton(rho0, rhoSclFuncInv, rhoSclFIprime,
                  (eta0, rho0, rhoMax, params))

def GE_41RT(xy_in, params, invert=False):
    """
    Apply radial distortion to polar coordinates on GE detector

    xin, yin are 1D arrays or scalars, assumed to be relative to self.xc, self.yc
    Units are [mm, radians].  This is the power-law based function of Bernier.

    Available Keyword Arguments :

    invert = True or >False< :: apply inverse warping
    """

    if params[0] == 0 and params[1] == 0 and params[2] ==0:
        return xy_in
    else:
        rhoMax = 204.8
        xy_out = np.empty_like(xy_in)
        if invert:
            _ge_41rt_inverse_distortion(xy_out, xy_in, float(rhoMax), np.asarray(params))
            #rhoOut = inverse_distortion_numpy(rhoOut, rho0, eta0, rhoMax, params)
        else:
            _ge_41rt_distortion(xy_out, xy_in, float(rhoMax), np.asarray(params))

        return xy_out
