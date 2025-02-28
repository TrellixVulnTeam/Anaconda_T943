#! /usr/bin/env python
# ============================================================
# Copyright (c) 2012, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
# Written by Joel Bernier <bernier2@llnl.gov> and others.
# LLNL-CODE-529294.
# All rights reserved.
#
# This file is part of HEXRD. For details on dowloading the source,
# see the file COPYING.
#
# Please also see the file LICENSE.
#
# This program is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License (as published by the Free Software
# Foundation) version 2.1 dated February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the terms and conditions of the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program (see file LICENSE); if not, write to
# the Free Software Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA 02111-1307 USA or visit <http://www.gnu.org/licenses/>.
# ============================================================

import sys
import numpy as np
#np.seterr(invalid='ignore')

import scipy.sparse as sparse


from hexrd import matrixutil as mutil

from numpy import float_ as nFloat
from numpy import int_ as nInt

from hexrd.xrd import distortion as dFuncs
from hexrd import USE_NUMBA

if USE_NUMBA:
    import numba


# ######################################################################
# Module Data

epsf      = np.finfo(float).eps      # ~2.2e-16
ten_epsf  = 10 * epsf                # ~2.2e-15
sqrt_epsf = np.sqrt(epsf)            # ~1.5e-8

periodDict   = {'degrees': 360.0, 'radians': 2*np.pi}
angularUnits = 'radians'        # module-level angle units
d2r          = np.pi/180.0

# basis vectors
I3 = np.eye(3)                                 # (3, 3) identity
Xl = np.array([[1., 0., 0.]], order='C').T     # X in the lab frame
Yl = np.array([[0., 1., 0.]], order='C').T     # Y in the lab frame
Zl = np.array([[0., 0., 1.]], order='C').T     # Z in the lab frame

zeroVec = np.zeros(3, order='C')

# reference beam direction and eta=0 ref in LAB FRAME for standard geometry
bVec_ref = -Zl
eta_ref  =  Xl

# reference stretch
vInv_ref = np.array([[1., 1., 1., 0., 0., 0.]], order='C').T

# distortion for warping detector coords
dFunc_ref   = dFuncs.GE_41RT
dParams_ref = [0., 0., 0., 2., 2., 2]

#
# ######################################################################

# ######################################################################
# Funtions

def makeGVector(hkl, bMat):
    """
    take a CRYSTAL RELATIVE B matrix onto a list of hkls to output unit
    reciprocal lattice vectors (a.k.a. lattice plane normals)

    Required Arguments:
    hkls -- (3, n) ndarray of n hstacked reciprocal lattice vector component
            triplets
    bMat -- (3, 3) ndarray representing the matirix taking reciprocal lattice
            vectors to the crystal reference frame

    Output:
    gVecs -- (3, n) ndarray of n unit reciprocal lattice vectors
             (a.k.a. lattice plane normals)

    To Do:
    * might benefit from some assert statements to catch improperly shaped
      input.
    """
    assert hkl.shape[0] == 3, 'hkl input must be (3, n)'
    return unitVector(np.dot(bMat, hkl))


if USE_NUMBA:
    @numba.njit
    def _anglesToGVecHelper(angs, out):
        #gVec_e = np.vstack([[np.cos(0.5*angs[:, 0]) * np.cos(angs[:, 1])],
        #                    [np.cos(0.5*angs[:, 0]) * np.sin(angs[:, 1])],
        #                    [np.sin(0.5*angs[:, 0])]])
        n = angs.shape[0]
        for i in range(n):
            ca0 = np.cos(0.5*angs[i, 0])
            sa0 = np.sin(0.5*angs[i, 0])
            ca1 = np.cos(angs[i, 1])
            sa1 = np.sin(angs[i, 1])
            out[i, 0] = ca0 * ca1
            out[i, 1] = ca0 * sa1
            out[i, 2] = sa0


    def anglesToGVec(angs, bHat_l, eHat_l, rMat_s=I3, rMat_c=I3):
        """
        from 'eta' frame out to lab (with handy kwargs to go to crystal or sample)
        """
        rMat_e = makeEtaFrameRotMat(bHat_l, eHat_l)
        gVec_e = np.empty((angs.shape[0], 3))
        _anglesToGVecHelper(angs, gVec_e)
        mat = np.dot(rMat_c.T, np.dot(rMat_s.T, rMat_e))
        return np.dot(mat, gVec_e.T)
else:
    def anglesToGVec(angs, bHat_l, eHat_l, rMat_s=I3, rMat_c=I3):
         """
         from 'eta' frame out to lab (with handy kwargs to go to crystal or sample)
         """
         rMat_e = makeEtaFrameRotMat(bHat_l, eHat_l)
         gVec_e = np.vstack([[np.cos(0.5*angs[:, 0]) * np.cos(angs[:, 1])],
                             [np.cos(0.5*angs[:, 0]) * np.sin(angs[:, 1])],
                             [np.sin(0.5*angs[:, 0])]])
         mat = np.dot(rMat_c.T, np.dot(rMat_s.T, rMat_e))
         return np.dot(mat, gVec_e)

def gvecToDetectorXY(gVec_c,
                     rMat_d, rMat_s, rMat_c,
                     tVec_d, tVec_s, tVec_c,
                     beamVec=bVec_ref):
    """
    Takes a list of unit reciprocal lattice vectors in crystal frame to the
    specified detector-relative frame, subject to the conditions:

    1) the reciprocal lattice vector must be able to satisfy a bragg condition
    2) the associated diffracted beam must intersect the detector plane

    Required Arguments:
    gVec_c -- (3, n) ndarray of n reciprocal lattice vectors in the CRYSTAL FRAME
    rMat_d -- (3, 3) ndarray, the COB taking DETECTOR FRAME components to LAB FRAME
    rMat_s -- (3, 3) ndarray, the COB taking SAMPLE FRAME components to LAB FRAME
    rMat_c -- (3, 3) ndarray, the COB taking CRYSTAL FRAME components to SAMPLE FRAME
    tVec_d -- (3, 1) ndarray, the translation vector connecting LAB to DETECTOR
    tVec_s -- (3, 1) ndarray, the translation vector connecting LAB to SAMPLE
    tVec_c -- (3, 1) ndarray, the translation vector connecting SAMPLE to CRYSTAL

    Outputs:
    (3, m) ndarray containing the intersections of m <= n diffracted beams
    associated with gVecs
    """
    ztol = epsf

    nVec_l = np.dot(rMat_d, Zl)                # detector plane normal
    bHat_l = unitVector(beamVec.reshape(3, 1)) # make sure beam vector is unit
    P0_l   = tVec_s + np.dot(rMat_s, tVec_c)   # origin of CRYSTAL FRAME
    P3_l   = tVec_d                            # origin of DETECTOR FRAME


    # form unit reciprocal lattice vectors in lab frame (w/o translation)
    gVec_l = np.dot(rMat_s, np.dot(rMat_c, unitVector(gVec_c)))

    # dot with beam vector (upstream direction)
    bDot   = np.dot(-bHat_l.T, gVec_l).squeeze()

    # see who can diffract; initialize output array with NaNs
    canDiffract = np.atleast_1d( np.logical_and( bDot >= ztol, bDot <= 1. - ztol ) )
    npts        = sum(canDiffract)
    retval      = np.nan * np.ones_like(gVec_l)
    if np.any(canDiffract):
        # subset of admissable reciprocal lattice vectors
        adm_gVec_l = gVec_l[:, canDiffract].reshape(3, npts)

        # initialize diffracted beam vector array
        dVec_l = np.empty((3, npts))
        for ipt in range(npts):
            dVec_l[:, ipt] = np.dot(makeBinaryRotMat(adm_gVec_l[:, ipt]), -bHat_l).squeeze()
            pass

        # ###############################################################
        # displacement vector calculation

        # first check for non-instersections
        denom = np.dot(nVec_l.T, dVec_l).flatten()
        dzero = abs(denom) < ztol
        denom[dzero] = 1.          # mitigate divide-by-zero
        cantIntersect = denom > 0. # index to dVec_l that can't hit det

        # displacement scaling (along dVec_l)
        u = np.dot(nVec_l.T, P3_l - P0_l).flatten() / denom

        # filter out non-intersections, fill with NaNs
        u[np.logical_or(dzero, cantIntersect)] = np.nan

        # diffracted beam points IN DETECTOR FRAME
        P2_l = P0_l + np.tile(u, (3, 1)) * dVec_l
        P2_d = np.dot(rMat_d.T, P2_l - tVec_d)

        # put feasible transformed gVecs into return array
        retval[:, canDiffract] = P2_d
        pass
    return retval[:2, :].T

def detectorXYToGvec(xy_det,
                     rMat_d, rMat_s,
                     tVec_d, tVec_s, tVec_c,
                     distortion=(dFunc_ref, dParams_ref),
                     beamVec=bVec_ref, etaVec=eta_ref,
                     output_ref=False):
    """
    Takes a list cartesian (x, y) pairs in the detector coordinates and calculates
    the associated reciprocal lattice (G) vectors and (bragg angle, azimuth) pairs
    with respect to the specified beam and azimth (eta) reference directions

    Required Arguments:
    xy_det -- (n, 2) ndarray or list-like input of n detector (x, y) points
    rMat_d -- (3, 3) ndarray, the COB taking DETECTOR FRAME components to LAB FRAME
    rMat_s -- (3, 3) ndarray, the COB taking SAMPLE FRAME components to LAB FRAME
    tVec_d -- (3, 1) ndarray, the translation vector connecting LAB to DETECTOR
    tVec_s -- (3, 1) ndarray, the translation vector connecting LAB to SAMPLE
    tVec_c -- (3, 1) ndarray, the translation vector connecting SAMPLE to CRYSTAL

    Optional Keyword Arguments:
    beamVec -- (3, 1) mdarray containing the incident beam direction components in the LAB FRAME
    etaVec  -- (3, 1) mdarray containing the reference azimuth direction components in the LAB FRAME

    Outputs:
    (n, 2) ndarray containing the (tTh, eta) pairs associated with each (x, y)
    (3, n) ndarray containing the associated G vector directions in the LAB FRAME
    associated with gVecs
    """
    npts   = len(xy_det)                       # number of input (x, y) pairs
    bHat_l = unitVector(beamVec.reshape(3, 1)) # make sure beam direction is a unit vector
    eHat_l = unitVector(etaVec.reshape(3, 1))  # make sure eta=0 direction is a unit vector

    xy_det = distortion[0](xy_det, distortion[1])

    # form in-plane vectors for detector points list in DETECTOR FRAME
    P2_d = np.hstack([np.atleast_2d(xy_det), np.zeros((npts, 1))]).T

    # in LAB FRAME
    P2_l = np.dot(rMat_d, P2_d) + tVec_d
    P0_l = tVec_s + np.dot(rMat_s, tVec_c)   # origin of CRYSTAL FRAME

    # diffraction unit vector components in LAB FRAME
    dHat_l = unitVector(P2_l - P0_l)

    # ###############################################################
    # generate output

    # DEBUGGING
    assert abs(np.dot(bHat_l.T, eHat_l)) < 1. - sqrt_epsf, "eta ref and beam cannot be parallel!"

    rMat_e = makeEtaFrameRotMat(bHat_l, eHat_l)
    dHat_e = np.dot(rMat_e.T, dHat_l)

    tTh = np.arccos(np.dot(bHat_l.T, dHat_l)).flatten()
    eta = np.arctan2(dHat_e[1, :], dHat_e[0, :]).flatten()

    # angles for reference frame
    dHat_ref_l = unitVector(P2_l)
    dHat_ref_e = np.dot(rMat_e.T, dHat_ref_l)
    tTh_ref = np.arccos(np.dot(bHat_l.T, unitVector(P2_l))).flatten()
    eta_ref = np.arctan2(dHat_ref_e[1, :], dHat_ref_e[0, :]).flatten()

    # get G-vectors by rotating d by 90-theta about b x d (numpy 'cross' works on row vectors)
    n_g = unitVector(np.cross(bHat_l.T, dHat_l.T).T)

    gVec_l = rotate_vecs_about_axis(0.5 * (np.pi - tTh), n_g, dHat_l)

    if output_ref:
        return (tTh_ref, eta_ref), (tTh, eta), gVec_l
    return (tTh, eta), gVec_l

def oscillAnglesOfHKLs(hkls, chi, rMat_c, bMat, wavelength,
                       vInv=vInv_ref, beamVec=bVec_ref, etaVec=eta_ref):
    """
    Takes a list of unit reciprocal lattice vectors in crystal frame to the
    specified detector-relative frame, subject to the conditions:

    1) the reciprocal lattice vector must be able to satisfy a bragg condition
    2) the associated diffracted beam must intersect the detector plane

    Required Arguments:
    hkls       -- (3, n) ndarray of n reciprocal lattice vectors in the CRYSTAL FRAME
    chi        -- float representing the inclination angle of the oscillation axis (std coords)
    rMat_c     -- (3, 3) ndarray, the COB taking CRYSTAL FRAME components to SAMPLE FRAME
    bMat       -- (3, 3) ndarray, the COB taking RECIPROCAL LATTICE components to CRYSTAL FRAME
    wavelength -- float representing the x-ray wavelength in Angstroms

    Optional Keyword Arguments:
    beamVec -- (3, 1) ndarray containing the incident beam direction components in the LAB FRAME
    etaVec  -- (3, 1) ndarray containing the reference azimuth direction components in the LAB FRAME
    vInv    -- (6, 1) ndarray containing the indep. components of the inverse left stretch tensor
                      in the SAMPLE FRAME in the Mandel-Voigt notation
    Outputs:
    ome0 -- (3, n) ndarray containing the feasible (tTh, eta, ome) triplets for each input hkl (first solution)
    ome1 -- (3, n) ndarray containing the feasible (tTh, eta, ome) triplets for each input hkl (second solution)

    Notes:
    ------------------------------------------------------------------------
    The reciprocal lattice vector, G, will satisfy the the Bragg condition
    when:

        b.T * G / ||G|| = -sin(theta)

    where b is the incident beam direction (k_i) and theta is the Bragg
    angle consistent with G and the specified wavelength. The components of
    G in the lab frame in this case are obtained using the crystal
    orientation, Rc, and the single-parameter oscillation matrix, Rs(ome):

        Rs(ome) * Rc * G / ||G||

    The equation above can be rearranged to yeild an expression of the form:

        a*sin(ome) + b*cos(ome) = c

    which is solved using the relation:

        a*sin(x) + b*cos(x) = sqrt(a**2 + b**2) * sin(x + alpha)

        --> sin(x + alpha) = c / sqrt(a**2 + b**2)

    where:

        alpha = arctan2(b, a)

     The solutions are:

                /
                |       arcsin(c / sqrt(a**2 + b**2)) - alpha
            x = <
                |  pi - arcsin(c / sqrt(a**2 + b**2)) - alpha
                \

    There is a double root in the case the reflection is tangent to the
    Debye-Scherrer cone (c**2 = a**2 + b**2), and no solution if the
    Laue condition cannot be satisfied (filled with NaNs in the results
    array here)
    """
    gVec_c = np.dot(bMat, hkls)                     # reciprocal lattice vectors in CRYSTAL frame
    vMat_s = mutil.vecMVToSymm(vInv)                # stretch tensor in SAMPLE frame
    gVec_s = np.dot(vMat_s, np.dot(rMat_c, gVec_c)) # reciprocal lattice vectors in SAMPLE frame
    gHat_s = unitVector(gVec_s)                     # unit reciprocal lattice vectors in SAMPLE frame
    gHat_c = np.dot(rMat_c.T, gHat_s)               # unit reciprocal lattice vectors in CRYSTAL frame
    bHat_l = unitVector(beamVec.reshape(3, 1))      # make sure beam direction is a unit vector
    eHat_l = unitVector(etaVec.reshape(3, 1))       # make sure eta=0 direction is a unit vector
    sintht = 0.5 * wavelength * columnNorm(gVec_s)  # sin of the Bragg angle assoc. with wavelength
    cchi = np.cos(chi); schi = np.sin(chi)          # sin and cos of the oscillation axis tilt

    # coefficients for harmonic equation
    a = gHat_s[2, :]*bHat_l[0] + schi*gHat_s[0, :]*bHat_l[1] - cchi*gHat_s[0, :]*bHat_l[2]
    b = gHat_s[0, :]*bHat_l[0] - schi*gHat_s[2, :]*bHat_l[1] + cchi*gHat_s[2, :]*bHat_l[2]
    c =                -sintht - cchi*gHat_s[1, :]*bHat_l[1] - schi*gHat_s[1, :]*bHat_l[2]

    # should all be 1-d: a = a.flatten(); b = b.flatten(); c = c.flatten()

    # form solution
    abMag    = np.sqrt(a*a + b*b); assert np.all(abMag > 0), "Beam vector specification is infealible!"
    phaseAng = np.arctan2(b, a)
    rhs      = c / abMag; rhs[abs(rhs) > 1.] = np.nan
    rhsAng   = np.arcsin(rhs) # verified will give NaN for abs(rhs) >  1. + 0.5*epsf

    # write ome angle output arrays (NaNs persist here)
    ome0 =         rhsAng - phaseAng
    ome1 = np.pi - rhsAng - phaseAng

    goodOnes_s = -np.isnan(ome0)

    # DEBUGGING
    assert np.all(np.isnan(ome0) == np.isnan(ome1)), "infeasible hkls do not match for ome0, ome1!"

    # do etas -- ONLY COMPUTE IN CASE CONSISTENT REFERENCE COORDINATES
    if abs(np.dot(bHat_l.T, eHat_l)) < 1. - sqrt_epsf and np.any(goodOnes_s):
        eta0 = np.nan * np.ones_like(ome0)
        eta1 = np.nan * np.ones_like(ome1)

        # make eta basis COB with beam antiparallel with Z
        rMat_e = makeEtaFrameRotMat(bHat_l, eHat_l)

        goodOnes   = np.tile(goodOnes_s, (1, 2)).flatten()

        numGood_s  = sum(goodOnes_s)
        numGood    = 2 * numGood_s
        tmp_eta    = np.empty(numGood)
        tmp_gvec   = np.tile(gHat_c, (1, 2))[:, goodOnes]
        allome     = np.hstack([ome0, ome1])

        for i in range(numGood):
            rMat_s = makeOscillRotMat([chi, allome[goodOnes][i]])
    	    gVec_e = np.dot(rMat_e.T,
                np.dot(rMat_s,
                       np.dot(rMat_c, tmp_gvec[:, i].reshape(3, 1)
                       ) ) )
            tmp_eta[i] = np.arctan2(gVec_e[1], gVec_e[0])
            pass
        eta0[goodOnes_s] = tmp_eta[:numGood_s]
        eta1[goodOnes_s] = tmp_eta[numGood_s:]

        # make assoc tTh array
        tTh  = 2.*np.arcsin(sintht).flatten()
        tTh0 = tTh; tTh0[-goodOnes_s] = np.nan
        retval = (np.vstack([tTh0.flatten(), eta0.flatten(), ome0.flatten()]),
                  np.vstack([tTh0.flatten(), eta1.flatten(), ome1.flatten()]),)
    else:
        retval = (ome0.flatten(), ome1.flatten())
        pass
    return retval

def polarRebin(thisFrame,
               npdiv        = 2,
               mmPerPixel   = (0.2, 0.2),
               convertToTTh = False,
               rMat_d       = I3,
               tVec_d       = np.r_[0., 0., -1000.],
               beamVec      = bVec_ref,
               etaVec       = eta_ref,
               rhoRange     = np.r_[20, 200],
               numRho       = 1000,
               etaRange     = (d2r*np.r_[-5, 355]),
               numEta       = 36,
               verbose      = True,
               log          = None
               ):
    """
    Caking algorithm

    INPUTS

    thisFrame
    npdiv=2, pixel subdivision (n x n) to determine bin membership
    rhoRange=[100, 1000] - radial range in pixels
    numRho=1200 - number of radial bins
    etaRange=np.pi*np.r_[-5, 355]/180. -- range of eta
    numEta=36 - number of eta subdivisions
    ROI=None - region of interest (four vector)
    corrected=False - uses 2-theta instead of rho
    verbose=True,

    """

    startEta = etaRange[0]
    stopEta  = etaRange[1]

    startRho = rhoRange[0]
    stopRho  = rhoRange[1]

    #nrows = thisFrame.shape[0]   # total number of rows in the full image
    #ncols = thisFrame.shape[1]   # total number of columns in the full image

    subPixArea = 1/float(npdiv)**2 # areal rescaling for subpixel intensities

    # MASTER COORDINATES
    #   - in pixel indices, UPPER LEFT PIXEL is [0, 0] --> (row, col)
    #   - in fractional pixels, UPPER LEFT CORNER is [-0.5, -0.5] --> (row, col)
    #   - in cartesian frame, the LOWER LEFT CORNER is [0, 0] --> (col, row)
    x       = thisFrame[0, :, :].flatten()
    y       = thisFrame[1, :, :].flatten()
    roiData = thisFrame[2, :, :].flatten()

    # need rhos (or tThs) and etas)
    if convertToTTh:
        dAngs = detectorXYToGvec(np.vstack([x, y]).T,
                                 rMat_d, I3,
                                 tVec_d, zeroVec, zeroVec,
                                 beamVec=beamVec, etaVec=etaVec)
        rho = dAngs[0][0]       # this is tTh now
        eta = dAngs[0][1]
    else:
        # in here, we are vanilla cartesian
        rho = np.sqrt(x*x + y*y)
        eta = np.arctan2(y, x)
    eta = mapAngle(eta, [startEta, 2*np.pi + startEta], units='radians')

    # MAKE POLAR BIN CENTER ARRAY
    deltaEta = (stopEta - startEta) / float(numEta)
    deltaRho = (stopRho - startRho) / float(numRho)

    rowEta = startEta + deltaEta * ( np.arange(numEta) + 0.5 )
    colRho = startRho + deltaRho * ( np.arange(numRho) + 0.5 )

    # initialize output dictionary
    polImg = {}
    polImg['radius']    = colRho
    polImg['azimuth']   = rowEta
    polImg['intensity'] = np.zeros( (numEta, numRho) )
    polImg['deltaRho']  = deltaRho

    if verbose:
        msg = "INFO: Masking pixels\n"
        if log:
            log.write(msg)
        else:
            print msg
            pass

    rhoI = startRho - 10*deltaRho
    rhoF = stopRho  + 10*deltaRho
    inAnnulus = np.where( (rho >= rhoI) & (rho <= rhoF) )[0]
    for i in range(numEta):
        if verbose:
            msg = "INFO: Processing sector %d of %d\n" % (i+1, numEta)
            if log:
                log.write(msg)
            else:
                print msg
                pass

        # import pdb;pdb.set_trace()
        etaI1 = rowEta[i] - 10.5*deltaEta
        etaF1 = rowEta[i] + 10.5*deltaEta

        tmpEta = eta[ inAnnulus ]
        inSector = np.where( (tmpEta >= etaI1) & (tmpEta <= etaF1) )[0]

        nptsIn = len(inSector)

        tmpX = x[ inAnnulus[inSector] ]
        tmpY = y[ inAnnulus[inSector] ]
        tmpI = roiData[ inAnnulus[inSector] ]

        # subdivide pixels
        #   - note that these are in fractional pixel coordinates (centered)
        #   - must convert to working units (see 'self.pixelPitchUnits')
        subCrds    = (np.arange(npdiv) + 0.5) / npdiv

        intX, intY = np.meshgrid(subCrds, subCrds)

        intX = np.tile(intX.flatten(), (nptsIn, 1)).T.flatten()
        intY = np.tile(intY.flatten(), (nptsIn, 1)).T.flatten()

        # expand coords using pixel subdivision
        tmpX = np.tile(tmpX, (npdiv**2, 1)).flatten() + (intX - 0.5)*mmPerPixel[0]
        tmpY = np.tile(tmpY, (npdiv**2, 1)).flatten() + (intY - 0.5)*mmPerPixel[1]
        tmpI = np.tile(tmpI, (npdiv**2, 1)).flatten() / subPixArea

        if convertToTTh:
            dAngs = detectorXYToGvec(np.vstack([tmpX, tmpY]).T,
                                     rMat_d, I3,
                                     tVec_d, zeroVec, zeroVec,
                                     beamVec=beamVec, etaVec=etaVec)
            tmpRho = dAngs[0][0]       # this is tTh now
            tmpEta = dAngs[0][1]
        else:
            tmpRho = np.sqrt( tmpX*tmpX + tmpY*tmpY )
            tmpEta = np.arctan2(tmpY, tmpX)
        tmpEta = mapAngle(tmpEta, [startEta, 2*np.pi + startEta], units='radians')

        etaI2 = rowEta[i] - 0.5*deltaEta
        etaF2 = rowEta[i] + 0.5*deltaEta

        inSector2 = ( (tmpRho >= startRho) & (tmpRho <= stopRho) ) \
                    & ( (tmpEta >= etaI2) & (tmpEta <= etaF2) )

        tmpRho = tmpRho[inSector2]
        tmpI   = tmpI[inSector2]

        binId = np.floor( ( tmpRho - startRho ) / deltaRho )
        nSubpixelsIn = len(binId)

        if ( nSubpixelsIn > 0 ):
            tmpI  = sparse.csc_matrix( \
                    ( tmpI, (binId, np.arange(nSubpixelsIn)) ), shape=(numRho, nSubpixelsIn) )
            binId = sparse.csc_matrix( \
                    ( np.ones(nSubpixelsIn), (binId, np.arange(nSubpixelsIn)) ), shape=(numRho, nSubpixelsIn) )

            # Normalized contribution to the ith sector's radial bins
            binIdSum = np.asarray(binId.sum(1)).flatten()
            #if np.any(binIdSum <= 0):
            #    import string
            #    raise RuntimeError, 'got binId sum of '+string.join(np.array(binIdSum).flatten().astype(str), ',')
            #polImg['intensity'][i, :] = (tmpI.sum(1) / binIdSum).T
            whereNZ = np.asarray(np.not_equal(polImg['intensity'][i,:],binIdSum))
            polImg['intensity'][i,whereNZ] = np.asarray(tmpI.sum(1))[whereNZ].flatten()/binIdSum[whereNZ]

    return polImg

"""
#######################################################################
######                  Utility Functions                        ######
#######################################################################

"""

def arccosSafe(temp):
    """
    Protect against numbers slightly larger than 1 in magnitude due to round-off
    """
    temp = np.atleast_1d(temp)
    if np.any(abs(temp) > 1.00001):
        print >> sys.stderr, "attempt to take arccos of %s" % temp
        raise RuntimeError, "unrecoverable error"

    gte1 = temp >=  1.
    lte1 = temp <= -1.

    temp[gte1] =  1
    temp[lte1] = -1

    ang = np.arccos(temp)

    return ang

def angularDifference(angList0, angList1, units=angularUnits):
    """
    Do the proper (acute) angular difference in the context of a branch cut.

    *) Default angular range is [-pi, pi]
    """
    period = periodDict[units]
    # take difference as arrays
    diffAngles = np.atleast_1d(angList0) - np.atleast_1d(angList1)

    return abs(np.remainder(diffAngles + 0.5*period, period) - 0.5*period)

def mapAngle(ang, *args, **kwargs):
    """Utility routine to map an angle into a specified period

    actual function is mapAngle(ang[, range], units=angularUnits).  range is
    optional and defaults to the appropriate angle for the unit centered on 0.
    """
    units  = angularUnits
    period = periodDict[units]

    kwargKeys = kwargs.keys()
    for iArg in range(len(kwargKeys)):
        if kwargKeys[iArg] == 'units':
            units = kwargs[ kwargKeys[iArg] ]
        else:
            raise RuntimeError, "Unknown keyword argument: " + str(kwargKeys[iArg])

    try:
        period = periodDict[units.lower()]
    except:
        raise RuntimeError, "unknown angular units: " + str( kwargs[ kwargKeys[iArg] ] )

    ang = np.atleast_1d(nFloat( ang ) )

    # if we have a specified angular range, use that
    if len(args) > 0:
        angRange = np.atleast_1d(nFloat( args[0] ) )

        # divide of multiples of period
        ang = ang - nInt(ang / period) * period

        lb = angRange.min()
        ub = angRange.max()

        if abs(ub - lb) != period:
            raise RuntimeError, 'range is incomplete!'

        lbi = ang < lb
        while lbi.sum() > 0:
            ang[lbi] = ang[lbi] + period
            lbi = ang < lb
            pass
        ubi = ang > ub
        while ubi.sum() > 0:
            ang[ubi] = ang[ubi] - period
            ubi = ang > ub
            pass
        retval = ang
    else:
        retval = np.mod(ang + 0.5*period, period) - 0.5*period
    return retval

def reg_grid_indices(edges, points_1d):
    """
    get indices in a 1-d regular grid.

    edges are just that:

    point:            x (2.5)
                      |
    edges:   |1    |2    |3    |4    |5
             -------------------------
    indices: |  0  |  1  |  2  |  3  |
             -------------------------

    above the deltas are + and the index for the point is 1

    point:                  x (2.5)
                            |
    edges:   |5    |4    |3    |2    |1
             -------------------------
    indices: |  0  |  1  |  2  |  3  |
             -------------------------

    here the deltas are - and the index for the point is 2

    * can handle grids with +/- deltas
    * be careful when using with a cyclical angular array!  edges and points
      must be mapped to the same branch cut, and
      abs(edges[0] - edges[-1]) = 2*pi
    """
    ztol = 1e-12

    assert len(edges) >= 2, "must have at least 2 edges"

    points_1d = np.r_[points_1d].flatten()
    delta     = float(edges[1] - edges[0])

    on_last_rhs = points_1d >= edges[-1] - ztol
    points_1d[on_last_rhs] = points_1d[on_last_rhs] - ztol

    if delta > 0:
        on_last_rhs = points_1d >= edges[-1] - ztol
        points_1d[on_last_rhs] = points_1d[on_last_rhs] - ztol
        idx = np.floor( (points_1d - edges[0]) / delta )
    elif delta < 0:
        on_last_rhs = points_1d <= edges[-1] + ztol
        points_1d[on_last_rhs] = points_1d[on_last_rhs] + ztol
        idx = np.ceil( (points_1d - edges[0]) / delta ) - 1
    else:
        raise RuntimeError, "edges array gives delta of 0"
    # if np.any(np.logical_or(idx < 0, idx > len(edges) - 1)):
    #     raise RuntimeWarning, "some input points are outside the grid"
    return np.array(idx, dtype=int)

def columnNorm(a):
    """
    normalize array of column vectors (hstacked, axis = 0)
    """
    if len(a.shape) > 2:
        raise RuntimeError, "incorrect shape: arg must be 1-d or 2-d, yours is %d" %(len(a.shape))

    cnrma = np.sqrt(sum(np.asarray(a)**2, 0))

    return cnrma

def rowNorm(a):
    """
    normalize array of row vectors (vstacked, axis = 1)
    """
    if len(a.shape) > 2:
        raise RuntimeError, "incorrect shape: arg must be 1-d or 2-d, yours is %d" %(len(a.shape))

    cnrma = np.sqrt(sum(np.asarray(a)**2, 1))

    return cnrma


if USE_NUMBA:
    @numba.njit
    def _unitVectorSingle(a, b):
        n = a.shape[0]
        nrm = 0.0
        for i in range(n):
            nrm += a[i]*a[i]
        nrm = np.sqrt(nrm)
        # prevent divide by zero
        if nrm > epsf:
            for i in range(n):
                b[i] = a[i] / nrm
        else:
            for i in range(n):
                b[i] = a[i]

    @numba.njit
    def _unitVectorMulti(a, b):
        n = a.shape[0]
        m = a.shape[1]
        for j in range(m):
            nrm = 0.0
            for i in range(n):
                nrm += a[i, j]*a[i, j]
            nrm = np.sqrt(nrm)
            # prevent divide by zero
            if nrm > epsf:
                for i in range(n):
                    b[i, j] = a[i, j] / nrm
            else:
                for i in range(n):
                    b[i, j] = a[i, j]
    

    def unitVector(a):
        """
        normalize array of column vectors (hstacked, axis = 0)
        """
        result = np.empty_like(a)
        if a.ndim == 1:
            _unitVectorSingle(a, result)
        elif a.ndim == 2:
            _unitVectorMulti(a, result)
        else:
            raise ValueError("incorrect arg shape; must be 1-d or 2-d, yours is %d-d" % (a.ndim))
        return result

else: # not USE_NUMBA
    def unitVector(a):
         """
         normalize array of column vectors (hstacked, axis = 0)
         """
         assert a.ndim in [1, 2], "incorrect arg shape; must be 1-d or 2-d, yours is %d-d" % (a.ndim)

         m = a.shape[0]; n = 1

         nrm = np.tile(np.sqrt(sum(np.asarray(a)**2, 0)), (m, n))

         # prevent divide by zero
         zchk = nrm <= epsf
         nrm[zchk] = 1.

         nrma = a/nrm

         return nrma


def makeDetectorRotMat(tiltAngles):
    """
    Form the (3, 3) tilt rotations from the tilt angle list:

    tiltAngles = [gamma_Xl, gamma_Yl, gamma_Zl] in radians
    """
    # form rMat_d from parameter list
    cos_gX = np.cos(tiltAngles[0]); sin_gX = np.sin(tiltAngles[0])
    cos_gY = np.cos(tiltAngles[1]); sin_gY = np.sin(tiltAngles[1])
    cos_gZ = np.cos(tiltAngles[2]); sin_gZ = np.sin(tiltAngles[2])
    rotXl = np.array([[     1.,      0.,      0.],
                      [     0.,  cos_gX, -sin_gX],
                      [     0.,  sin_gX,  cos_gX]])
    rotYl = np.array([[ cos_gY,      0.,  sin_gY],
                      [     0.,      1.,      0.],
                      [-sin_gY,      0.,  cos_gY]])
    rotZl = np.array([[ cos_gZ, -sin_gZ,      0.],
                      [ sin_gZ,  cos_gZ,      0.],
                      [     0.,      0.,      1.]])
    return np.dot(rotZl, np.dot(rotYl, rotXl))


def makeOscillRotMat(oscillAngles):
    """
    oscillAngles = [chi, ome]
    """
    cchi = np.cos(oscillAngles[0]); schi = np.sin(oscillAngles[0])
    come = np.cos(oscillAngles[1]); some = np.sin(oscillAngles[1])
    rchi = np.array([[   1.,    0.,    0.],
                     [   0.,  cchi, -schi],
                     [   0.,  schi,  cchi]])
    rome = np.array([[ come,    0.,  some],
                     [   0.,    1.,    0.],
                     [-some,    0.,  come]])
    return np.dot(rchi, rome)


def makeRotMatOfExpMap(expMap):
    """
    """
    expMap = np.asarray(expMap).flatten()
    phi = np.sqrt(expMap[0]*expMap[0] + expMap[1]*expMap[1] + expMap[2]*expMap[2])
    if phi > epsf:
        wMat = np.array([[        0., -expMap[2],  expMap[1]],
                         [ expMap[2],         0., -expMap[0]],
    	                 [-expMap[1],  expMap[0],         0.]])
    	rMat = \
          I3 \
          + ( np.sin(phi) / phi ) * wMat \
          + ( (1. - np.cos(phi)) / (phi*phi) ) * np.dot(wMat, wMat)
    else:
    	rMat = I3
    return rMat


def makeBinaryRotMat(axis):
    """
    """
    n = np.asarray(axis).flatten()
    assert len(n) == 3, 'Axis input does not have 3 components'
    return 2*np.dot(n.reshape(3, 1), n.reshape(1, 3)) - I3


if USE_NUMBA:
    @numba.njit
    def _makeEtaFrameRotMat(bHat_l, eHat_l, out):
        # bHat_l and eHat_l CANNOT have 0 magnitude!
        # must catch this case as well as colinear bHat_l/eHat_l elsewhere...
        bHat_mag = np.sqrt(bHat_l[0]**2 + bHat_l[1]**2 + bHat_l[2]**2)
        
        # assign Ze as -bHat_l
        for i in range(3):
            out[i, 2] = -bHat_l[i] / bHat_mag

        # find Ye as Ze ^ eHat_l
        Ye0 = out[1, 2]*eHat_l[2] - eHat_l[1]*out[2, 2]
        Ye1 = out[2, 2]*eHat_l[0] - eHat_l[2]*out[0, 2]
        Ye2 = out[0, 2]*eHat_l[1] - eHat_l[0]*out[1, 2]

        Ye_mag = np.sqrt(Ye0**2 + Ye1**2 + Ye2**2)

        out[0, 1] = Ye0 / Ye_mag
        out[1, 1] = Ye1 / Ye_mag
        out[2, 1] = Ye2 / Ye_mag

        # find Xe as Ye ^ Ze
        out[0, 0] = out[1, 1]*out[2, 2] - out[1, 2]*out[2, 1]
        out[1, 0] = out[2, 1]*out[0, 2] - out[2, 2]*out[0, 1]
        out[2, 0] = out[0, 1]*out[1, 2] - out[0, 2]*out[1, 1]


    def makeEtaFrameRotMat(bHat_l, eHat_l):
        """
        make eta basis COB matrix with beam antiparallel with Z

        takes components from ETA frame to LAB

        **NO EXCEPTION HANDLING FOR COLINEAR ARGS IN NUMBA VERSION!

        ...put checks for non-zero magnitudes and non-colinearity in wrapper?
        """
        result = np.empty((3,3))
        _makeEtaFrameRotMat(bHat_l.reshape(3), eHat_l.reshape(3), result)
        return result

else: # not USE_NUMBA
    def makeEtaFrameRotMat(bHat_l, eHat_l):
        """
        make eta basis COB matrix with beam antiparallel with Z
        
        takes components from ETA frame to LAB
        """
        # normalize input 
        bHat_l = unitVector(bHat_l.reshape(3, 1))
        eHat_l = unitVector(eHat_l.reshape(3, 1))

        # find Ye as cross(eHat_l, bHat_l), normalize if kosher
        Ye = np.cross(eHat_l.flatten(), bHat_l.flatten())
        if np.sqrt(np.sum(Ye*Ye)) < 1e-8:
            raise RuntimeError, "bHat_l and eHat_l must NOT be colinear!"
        Ye = unitVector(Ye.reshape(3, 1))
        
        # find Xe as cross(bHat_l, Ye)
        Xe = np.cross(bHat_l.flatten(), Ye.flatten()).reshape(3, 1)
        return np.hstack([Xe, Ye, -bHat_l])


def validateAngleRanges(angList, startAngs, stopAngs, ccw=True):
    """
    A better way to go.  find out if an angle is in the range
    CCW or CW from start to stop

    There is, of course, an ambigutiy if the start and stop angle are
    the same; we treat them as implying 2*pi having been mapped
    """
    # Prefer ravel over flatten because flatten never skips the copy
    angList   = np.asarray(angList).ravel()   # needs to have len
    startAngs = np.asarray(startAngs).ravel() # needs to have len
    stopAngs  = np.asarray(stopAngs).ravel()  # needs to have len

    n_ranges = len(startAngs)
    assert len(stopAngs) == n_ranges, "length of min and max angular limits must match!"

    # to avoid warnings in >=, <= later down, mark nans;
    # need these to trick output to False in the case of nan input
    nan_mask = np.isnan(angList)

    reflInRange = np.zeros(angList.shape, dtype=bool)

    # anonynmous func for zProjection
    zProj = lambda x, y: np.cos(x) * np.sin(y) - np.sin(x) * np.cos(y)

    # bin length for chunking
    binLen = np.pi / 2.

    # in plane vectors defining wedges
    x0 = np.vstack([np.cos(startAngs), np.sin(startAngs)])
    x1 = np.vstack([np.cos(stopAngs), np.sin(stopAngs)])

    # dot products
    dp = np.sum(x0 * x1, axis=0)
    if np.any(dp >= 1. - sqrt_epsf) and n_ranges > 1:
        # ambiguous case
        raise RuntimeError, "Improper usage; at least one of your ranges is alread 360 degrees!"
    elif dp[0] >= 1. - sqrt_epsf and n_ranges == 1:
        # trivial case!
        reflInRange = np.ones(angList.shape, dtype=bool)
        reflInRange[nan_mask] = False
    else:
        # solve for arc lengths
        # ...note: no zeros should have made it here
        a   = x0[0, :]*x1[1, :] - x0[1, :]*x1[0, :]
        b   = x0[0, :]*x1[0, :] + x0[1, :]*x1[1, :]
        phi = np.arctan2(b, a)

        arclen = 0.5*np.pi - phi          # these are clockwise
        cw_phis = arclen < 0
        arclen[cw_phis] = 2*np.pi + arclen[cw_phis]   # all positive (CW) now
        if not ccw:
            arclen= 2*np.pi - arclen

        if sum(arclen) > 2*np.pi:
            raise RuntimeWarning, "Specified angle ranges sum to > 360 degrees, which is suspect..."

        # check that there are no more thandp = np.zeros(n_ranges)
        for i in range(n_ranges):
            # number or subranges using 'binLen'
            numSubranges = int(np.ceil(arclen[i]/binLen))

            # check remaider
            binrem = np.remainder(arclen[i], binLen)
            if binrem == 0:
                finalBinLen = binLen
            else:
                finalBinLen = binrem

            # if clockwise, negate bin length
            if not ccw:
                 binLen      = -binLen
                 finalBinLen = -finalBinLen

            # Create sub ranges on the fly to avoid ambiguity in dot product
            # for wedges >= 180 degrees
            subRanges = np.array(\
                [startAngs[i] + binLen*j for j in range(numSubranges)] + \
                    [startAngs[i] + binLen*(numSubranges - 1) + finalBinLen])

            for k in range(numSubranges):
                zStart = zProj(angList, subRanges[k])
                zStop  = zProj(angList, subRanges[k + 1])
                if ccw:
                    zStart[nan_mask] =  999.
                    zStop[nan_mask]  = -999.
                    reflInRange = reflInRange | np.logical_and(zStart <= 0, zStop >= 0)
                else:
                    zStart[nan_mask] = -999.
                    zStop[nan_mask]  =  999.
                    reflInRange = reflInRange | np.logical_and(zStart >= 0, zStop <= 0)
    return reflInRange


def rotate_vecs_about_axis(angle, axis, vecs):
    """
    Rotate vectors about an axis

    INPUTS
    *angle* - array of angles (len == 1 or n)
    *axis*  - array of unit vectors (shape == (3, 1) or (3, n))
    *vec*   - array of vectors to be rotated (shape = (3, n))

    Quaternion formula:
    if we split v into parallel and perpedicular components w.r.t. the
    axis of quaternion q,

        v = a + n

    then the action of rotating the vector dot(R(q), v) becomes

        v_rot = (q0**2 - |q|**2)(a + n) + 2*dot(q, a)*q + 2*q0*cross(q, n)

    """
    angle   = np.atleast_1d(angle)
    #nvecs   = vecs.shape[1]                  # assume column vecs

    # quaternion components
    q0 = np.cos(0.5*angle)
    q1 = np.sin(0.5*angle)
    qv = np.tile(q1, (3, 1)) * axis

    # component perpendicular to axes (inherits shape of vecs)
    vp0 = vecs[0, :] - axis[0, :]*axis[0, :]*vecs[0, :] - axis[0, :]*axis[1, :]*vecs[1, :] - axis[0, :]*axis[2, :]*vecs[2, :]
    vp1 = vecs[1, :] - axis[1, :]*axis[1, :]*vecs[1, :] - axis[1, :]*axis[0, :]*vecs[0, :] - axis[1, :]*axis[2, :]*vecs[2, :]
    vp2 = vecs[2, :] - axis[2, :]*axis[2, :]*vecs[2, :] - axis[2, :]*axis[0, :]*vecs[0, :] - axis[2, :]*axis[1, :]*vecs[1, :]

    # dot product with components along; cross product with components normal
    qdota   = \
      ( axis[0, :]*vecs[0, :] + axis[1, :]*vecs[1, :] + axis[2, :]*vecs[2, :] ) * \
      ( axis[0, :] * qv[0, :] + axis[1, :] * qv[1, :] + axis[2, :] * qv[2, :] )
    qcrossn = np.vstack([qv[1, :]*vp2 - qv[2, :]*vp1,
                         qv[2, :]*vp0 - qv[0, :]*vp2,
                         qv[0, :]*vp1 - qv[1, :]*vp0])

    # quaternion formula
    v_rot = np.tile(q0*q0 - q1*q1, (3, 1)) * vecs \
      + 2. * np.tile(qdota, (3, 1)) * qv \
      + 2. * np.tile(q0, (3, 1)) * qcrossn
    return v_rot


def quat_product_matrix(q, mult='right'):
    """
    Form 4 x 4 array to perform the quaternion product

    USAGE
        qmat = quatProductMatrix(q, mult='right')

    INPUTS
        1) quats is (4,), an iterable representing a unit quaternion
           horizontally concatenated
        2) mult is a keyword arg, either 'left' or 'right', denoting
           the sense of the multiplication:

                       / quatProductMatrix(h, mult='right') * q
           q * h  --> <
                       \ quatProductMatrix(q, mult='left') * h

    OUTPUTS
        1) qmat is (4, 4), the left or right quaternion product
           operator

    NOTES
       *) This function is intended to replace a cross-product based
          routine for products of quaternions with large arrays of
          quaternions (e.g. applying symmetries to a large set of
          orientations).
    """
    if mult == 'right':
        qmat = np.array([[ q[0], -q[1], -q[2], -q[3]],
                         [ q[1],  q[0],  q[3], -q[2]],
                         [ q[2], -q[3],  q[0],  q[1]],
                         [ q[3],  q[2], -q[1],  q[0]],
                         ])
    elif mult == 'left':
        qmat = np.array([[ q[0], -q[1], -q[2], -q[3]],
                         [ q[1],  q[0], -q[3],  q[2]],
                         [ q[2],  q[3],  q[0], -q[1]],
                         [ q[3], -q[2],  q[1],  q[0]],
                         ])
    return qmat


def quat_distance(q1, q2, qsym):
    """
    """
    # qsym from PlaneData objects are (4, nsym)
    # convert symmetries to (4, 4) qprod matrices
    nsym = qsym.shape[1]
    rsym = np.zeros((nsym, 4, 4))
    for i in range(nsym):
        rsym[i, :, :] = quat_product_matrix(qsym[:, i], mult='right')

    # inverse of q1 in matrix form
    q1i = quat_product_matrix( np.r_[ 1, -1, -1, -1] * np.atleast_1d(q1).flatten(), mult='right' )

    # Do R * Gc, store as vstacked equivalent quaternions (nsym, 4)
    q2s = np.dot(rsym, q2)

    # Calculate the class of misorientations for full symmetrically equivalent
    # q1 and q2: (4, ) * (4, nsym)
    eqv_mis = np.dot(q1i, q2s.T)

    # find the largest scalar component
    q0_max = np.argmax(abs(eqv_mis[0, :]))

    # compute the distance
    qmin  = eqv_mis[:, q0_max]

    return 2 * arccosSafe( qmin[0] * np.sign(qmin[0]) )
