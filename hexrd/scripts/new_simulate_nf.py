"""
Refactor of simulate_nf so that an experiment is mocked up.

Also trying to minimize imports
"""

import sys
import logging

import numpy as np
import numba
import yaml
import argparse
import time
import itertools as it
from contextlib import contextmanager
import multiprocessing
# import of hexrd modules

from hexrd import matrixutil as mutil
from hexrd.xrd import transforms as xf
from hexrd.xrd import transforms_CAPI as xfcapi
from hexrd.xrd import rotations as rot # for rotMatOfQuat
from hexrd.xrd import xrdutil
import hexrd.gridutil as gridutil

from hexrd.xrd import material
from skimage.morphology import dilation as ski_dilation


# ==============================================================================
# %% SOME SCAFFOLDING
# ==============================================================================

class ProcessController(object):
    """This is a 'controller' that provides the necessary hooks to
    track the results of the process as well as to provide clues of
    the progress of the process"""

    def __init__(self, result_handler=None, progress_observer=None, ncpus = 1,
                 chunk_size = 100):
        self.rh = result_handler
        self.po = progress_observer
        self.ncpus = ncpus
        self.chunk_size = chunk_size
        self.limits = {}
        self.timing = []


    # progress handling --------------------------------------------------------

    def start(self, name, count):
        self.po.start(name, count)
        t = time.time()
        self.timing.append((name, count, t))


    def finish(self, name):
        t = time.time()
        self.po.finish()
        entry = self.timing.pop()
        assert name==entry[0]
        total = t - entry[2]
        logging.info("%s took %8.3fs (%8.6fs per item).", entry[0], total, total/entry[1])


    def update(self, value):
        self.po.update(value)

    # result handler -----------------------------------------------------------

    def handle_result(self, key, value):
        logging.debug("handle_result (%(key)s)", locals())
        self.rh.handle_result(key, value)

    # value limitting ----------------------------------------------------------
    def set_limit(self, key, limit_function):
        if key in self.limits:
            logging.warn("Overwritting limit funtion for '%(key)s'", locals())

        self.limits[key] = limit_function

    def limit(self, key, value):
        try:
            value = self.limits[key](value)
        except KeyError:
            pass
        except Exception:
            logging.warn("Could not apply limit to '%(key)s'", locals())

        return value

    # configuration  -----------------------------------------------------------
    def get_process_count(self):
        return self.ncpus

    def get_chunk_size(self):
        return self.chunk_size


def null_progress_observer():
    class NullProgressObserver(object):
        def start(self, name, count):
            pass

        def update(self, value):
            pass

        def finish(self):
            pass

    return NullProgressObserver()


def progressbar_progress_observer():
    from progressbar import ProgressBar, Percentage, Bar

    class ProgressBarProgressObserver(object):
        def start(self, name, count):
            self.pbar = ProgressBar(widgets=[name, Percentage(), Bar()],
                                    maxval=count)
            self.pbar.start()

        def update(self, value):
            self.pbar.update(value)

        def finish(self):
            self.pbar.finish()

    return ProgressBarProgressObserver()


def forgetful_result_handler():
    class ForgetfulResultHandler(object):
        def handle_result(self, key, value):
            pass # do nothing

    return ForgetfulResultHandler()


def saving_result_handler(filename):
    """returns a result handler that saves the resulting arrays into a file
    with name filename"""
    class SavingResultHandler(object):
        def __init__(self, file_name):
            self.filename = file_name
            self.arrays = {}

        def handle_result(self, key, value):
            self.arrays[key] = value

        def __del__(self):
            logging.debug("Writting arrays in %(filename)s", self.__dict__)
            try:
                np.savez_compressed(open(self.filename, "wb"), **self.arrays)
            except IOError:
                logging.error("Failed to write %(filename)s", self.__dict__)

    return SavingResultHandler(filename)


def checking_result_handler(filename):
    """returns a return handler that checks the results against a
    reference file.

    The Check will consider a FAIL either a result not present in the
    reference file (saved as a numpy savez or savez_compressed) or a
    result that differs. It will consider a PARTIAL PASS if the
    reference file has a shorter result, but the existing results
    match. A FULL PASS will happen when all existing results match

    """
    class CheckingResultHandler(object):
        def __init__(self, reference_file):
            """Checks the result against those save in 'reference_file'"""
            self.reference_results = np.load(open(reference_file, 'rb'))

        def handle_result(self, key, value):
            if key in ['experiment', 'image_stack']:
                return #ignore these

            try:
                reference = self.reference_results[key]
            except KeyError as e:
                logging.warning("%(key)s: %(e)s", locals())
                reference = None

            if reference is None:
                msg = "'{0}': No reference result."
                logging.warn(msg.format(key))

            try:
                if key=="confidence":
                    reference = reference.T
                    value = value.T

                check_len = min(len(reference), len(value))
                test_passed = np.allclose(value[:check_len], reference[:check_len])

                if not test_passed:
                    msg = "'{0}': FAIL"
                    logging.warn(msg.format(key))
                    lvl = logging.WARN
                elif len(value) > check_len:
                    msg = "'{0}': PARTIAL PASS"
                    lvl = logging.WARN
                else:
                    msg = "'{0}': FULL PASS"
                    lvl = logging.INFO
                logging.log(lvl, msg.format(key))
            except Exception as e:
                msg = "%(key)s: Failure trying to check the results.\n%(e)s"
                logging.error(msg, locals())

    return CheckingResultHandler(filename)


# ==============================================================================
# %% UTILITY FUNCTIONS
# ==============================================================================
def mockup_experiment():
    # user options
    # each grain is provided in the form of a quaternion.

    # The following array contains the quaternions for the array. Note that the
    # quaternions are in the columns, with the first row (row 0) being the real
    # part w. We assume that we are dealing with unit quaternions

    quats = np.array([[ 0.91836393,  0.90869942],
                      [ 0.33952917,  0.1834835 ],
                      [ 0.17216207,  0.10095837],
                      [ 0.10811041,  0.36111851]])

    n_grains = quats.shape[-1] # last dimension provides the number of grains
    phis = 2.*np.arccos(quats[0, :]) # phis are the angles for the quaternion
    ns = mutil.unitVector(quats[1:, :]) # ns contains the rotation axis as an unit vector
    exp_maps = np.array([phis[i]*ns[:, i] for i in range(n_grains)])
    rMat_c = rot.rotMatOfQuat(quats)

    cvec = np.arange(-25, 26)
    X, Y, Z = np.meshgrid(cvec, cvec, cvec)

    crd0 = 1e-3*np.vstack([X.flatten(), Y.flatten(), Z.flatten()]).T
    crd1 = crd0 + np.r_[0.100, 0.100, 0]
    crds = np.array([crd0, crd1])

    # make grain parameters
    grain_params = []
    for i in range(n_grains):
        for j in range(len(crd0)):
            grain_params.append(
                np.hstack([exp_maps[i, :], crds[i][j, :], xf.vInv_ref.flatten()])
            )

    # scan range and period
    ome_period = (0, 2*np.pi)
    ome_range = [ome_period,]
    ome_step = np.radians(1.)
    nframes = 0
    for i in range(len(ome_range)):
        del_ome = ome_range[i][1]-ome_range[i][0]
        nframes += int((ome_range[i][1]-ome_range[i][0])/ome_step)

    ome_edges = np.arange(nframes+1)*ome_step

    # instrument
    with open('./retiga.yml', 'r') as fildes:
        instr_cfg = yaml.load(fildes)

    tiltAngles = instr_cfg['detector']['transform']['tilt_angles']
    tVec_d = np.array(instr_cfg['detector']['transform']['t_vec_d']).reshape(3,1)
    chi = instr_cfg['oscillation_stage']['chi']
    tVec_s = np.array(instr_cfg['oscillation_stage']['t_vec_s']).reshape(3,1)
    rMat_d = xfcapi.makeDetectorRotMat(tiltAngles)
    rMat_s = xfcapi.makeOscillRotMat([chi, 0.])

    pixel_size = instr_cfg['detector']['pixels']['size']
    nrows = instr_cfg['detector']['pixels']['rows']
    ncols = instr_cfg['detector']['pixels']['columns']

    col_ps = pixel_size[1]
    row_ps = pixel_size[0]

    row_dim = row_ps*nrows # in mm
    col_dim = col_ps*ncols # in mm
    panel_dims = [(-0.5*ncols*col_ps, -0.5*nrows*row_ps),
                  ( 0.5*ncols*col_ps,  0.5*nrows*row_ps)]

    x_col_edges = col_ps * (np.arange(ncols + 1) - 0.5*ncols)
    y_row_edges = row_ps * (np.arange(nrows, -1, -1) - 0.5*nrows)
    #x_col_edges = np.arange(panel_dims[0][0], panel_dims[1][0] + 0.5*col_ps, col_ps)
    #y_row_edges = np.arange(panel_dims[0][1], panel_dims[1][1] + 0.5*row_ps, row_ps)
    rx, ry = np.meshgrid(x_col_edges, y_row_edges)

    gcrds = xfcapi.detectorXYToGvec(np.vstack([rx.flatten(), ry.flatten()]).T,
                                    rMat_d, rMat_s,
                                    tVec_d, tVec_s, np.zeros(3))

    max_pixel_tth = np.amax(gcrds[0][0])
    detector_params = np.hstack([tiltAngles, tVec_d.flatten(), chi,
                                 tVec_s.flatten()])
    distortion = None

    # a different parametrization for the sensor (makes for faster quantization)
    base = np.array([x_col_edges[0],
                     y_row_edges[0],
                     ome_edges[0]])
    deltas = np.array([x_col_edges[1] - x_col_edges[0],
                       y_row_edges[1] - y_row_edges[0],
                       ome_edges[1] - ome_edges[0]])
    inv_deltas = 1.0/deltas
    clip_vals = np.array([ncols, nrows])



    # dilation
    max_diameter = np.sqrt(3)*0.005
    row_dilation = np.ceil(0.5 * max_diameter/row_ps)
    col_dilation = np.ceil(0.5 * max_diameter/col_ps)

    # crystallography data
    from hexrd import valunits
    gold = material.Material('gold')
    gold.sgnum = 225
    gold.latticeParameters = [4.0782, ]
    gold.hklMax = 200
    gold.beamEnergy = valunits.valWUnit("wavelength", "ENERGY", 52, "keV")
    gold.planeData.exclusions = None
    gold.planeData.tThMax = max_pixel_tth #note this comes from info in the detector


    ns = argparse.Namespace()
    # grains related information
    ns.n_grains = n_grains # this can be derived from other values...
    ns.rMat_c = rMat_c # n_grains rotation matrices (one per grain)
    ns.exp_maps = exp_maps # n_grains exp_maps -angle * rotation axis- (one per grain)

    ns.plane_data = gold.planeData
    ns.detector_params = detector_params
    ns.pixel_size = pixel_size
    ns.ome_range = ome_range
    ns.ome_period = ome_period
    ns.x_col_edges = x_col_edges
    ns.y_row_edges = y_row_edges
    ns.ome_edges = ome_edges
    ns.ncols = ncols
    ns.nrows = nrows
    ns.nframes = nframes # used only in simulate...
    ns.rMat_d = rMat_d
    ns.tVec_d = tVec_d
    ns.chi = chi # note this is used to compute S... why is it needed?
    ns.tVec_s = tVec_s
    # ns.rMat_s = rMat_s
    # ns.tVec_s = tVec_s
    ns.rMat_c = rMat_c
    ns.row_dilation = row_dilation
    ns.col_dilation = col_dilation
    ns.distortion = distortion
    ns.panel_dims = panel_dims # used only in simulate...
    ns.base = base
    ns.inv_deltas = inv_deltas
    ns.clip_vals = clip_vals

    return grain_params, ns


# ==============================================================================
# %% OPTIMIZED BITS
# ==============================================================================
@numba.njit
def _v3_dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

@numba.njit
def _m33_v3_multiply(m, v, dst):
    v0 = v[0]; v1 = v[1]; v2 = v[2]
    dst[0] = m[0, 0]*v0 + m[0, 1]*v1 + m[0, 2]*v2
    dst[1] = m[1, 0]*v0 + m[1, 1]*v1 + m[1, 2]*v2
    dst[2] = m[2, 0]*v0 + m[2, 1]*v1 + m[2, 2]*v2

    return dst


@numba.njit
def __anglesToGVec(angs, rMat_ss, rMat_c):
    result = np.empty_like(angs)
    tmp_g = np.empty((3,))
    for i in range(len(angs)):
        cx = np.cos(0.5*angs[i,0])
        sx = np.sin(0.5*angs[i,0])
        cy = np.cos(angs[i,1])
        sy = np.sin(angs[i,1])
        tmp_g[0] = cx*cy
        tmp_g[1] = cx*sy
        tmp_g[2] = sx
        np.dot(rMat_c, np.dot(rMat_ss[i], tmp_g), out=result[i])

    return result

@numba.njit
def _anglesToGVec(angs, rMat_ss, rMat_c):
    """From a set of angles return them in crystal space"""
    result = np.empty_like(angs)
    for i in range(len(angs)):
        cx = np.cos(0.5*angs[i, 0])
        sx = np.sin(0.5*angs[i, 0])
        cy = np.cos(angs[i,1])
        sy = np.sin(angs[i,1])
        g0 = cx*cy
        g1 = cx*sy
        g2 = sx

        t0_0 = rMat_ss[ i, 0, 0]*g0 + rMat_ss[ i, 1, 0]*g1 + rMat_ss[ i, 2, 0]*g2
        t0_1 = rMat_ss[ i, 0, 1]*g0 + rMat_ss[ i, 1, 1]*g1 + rMat_ss[ i, 2, 1]*g2
        t0_2 = rMat_ss[ i, 0, 2]*g0 + rMat_ss[ i, 1, 2]*g1 + rMat_ss[ i, 2, 2]*g2

        result[i, 0] = rMat_c[0, 0]*t0_0 + rMat_c[ 1, 0]*t0_1 + rMat_c[ 2, 0]*t0_2
        result[i, 1] = rMat_c[0, 1]*t0_0 + rMat_c[ 1, 1]*t0_1 + rMat_c[ 2, 1]*t0_2
        result[i, 2] = rMat_c[0, 2]*t0_0 + rMat_c[ 1, 2]*t0_1 + rMat_c[ 2, 2]*t0_2

    return result


@numba.njit
def _filter_nans(tmp_xys):
    result = np.empty_like(tmp_xys)

    pivot = 0
    for i in range(len(tmp_xys)):
        if np.isfinite(tmp_xys[i, 0]) and np.isfinite(tmp_xys[i,1]):
            result[pivot, 0] = tmp_xys[i, 0]
            result[pivot, 1] = tmp_xys[i, 1]
            pivot += 1

    return result[0:pivot,:]


def _opt_project_on_detector(angs, rD, rC, gVec_cs, rMat_ss, tD, tC, tS, distortion):
    tmp_xys = xfcapi.gvecToDetectorXYArray(gVec_cs, rD, rMat_ss, rC, tD, tS, tC)

    # do not filter nans, let the code after it handle that.
    # filter nans...
    #tmp_xys = _filter_nans(tmp_xys)

    if distortion is not None and len(distortion) > 0:
        tmp_xys = distortion[0](tmp_xys, distortion[1], invert=True)

    return tmp_xys, None

# ==============================================================================
# %% DIFFRACTION SIMULATION
# ==============================================================================

def get_simulate_diffractions(grain_params, experiment,
                              cache_file='gold_cubes.npy',
                              controller=None):
    """getter functions that handles the caching of the simulation"""
    try:
        image_stack = np.load(cache_file)
    except Exception:
        image_stack = simulate_diffractions(grain_params, experiment,
                                            controller=controller)
        np.save(cache_file, image_stack)

    controller.handle_result('image_stack', image_stack)

    return image_stack


@numba.njit
def _write_pixels(coords, angles, image, base, inv_deltas, clip_vals):
    count = len(coords)
    for i in range(count):
        x = int(np.floor((coords[i, 0] - base[0]) * inv_deltas[0]))

        if x < 0 or x >= clip_vals[0]:
            continue

        y = int(np.floor((coords[i, 1] - base[1]) * inv_deltas[1]))

        if y < 0 or y >= clip_vals[1]:
            continue

        z = int(np.floor((angles[i] - base[2]) * inv_deltas[2]))

        image[z, y, x] = True


def simulate_diffractions(grain_params, experiment, controller):
    """actual forward simulation of the diffraction"""

    image_stack = np.zeros((experiment.nframes, experiment.nrows, experiment.ncols), dtype=bool)
    count = len(grain_params)
    subprocess = 'simulate diffractions'

    _project = xrdutil._project_on_detector_plane
    rD = experiment.rMat_d
    chi = experiment.chi
    tD = experiment.tVec_d
    tS = experiment.tVec_s
    distortion = experiment.distortion

    eta_range = [(-np.pi, np.pi), ]
    ome_range = experiment.ome_range
    ome_period = (-np.pi, np.pi)

    full_hkls = xrdutil._fetch_hkls_from_planedata(experiment.plane_data)
    bMat = experiment.plane_data.latVecOps['B']
    wlen = experiment.plane_data.wavelength

    controller.start(subprocess, count)
    for i in range(count):
        rC = xfcapi.makeRotMatOfExpMap(grain_params[i][0:3])
        tC = np.ascontiguousarray(grain_params[i][3:6])
        vInv_s = np.ascontiguousarray(grain_params[i][6:12])
        ang_list = np.vstack(xfcapi.oscillAnglesOfHKLs(full_hkls[:, 1:], chi,
                                                       rC, bMat, wlen,
                                                       vInv=vInv_s))
        # hkls not needed here
        all_angs, _ = xrdutil._filter_hkls_eta_ome(full_hkls, ang_list,
                                                   eta_range, ome_range)
        all_angs[:, 2] =xf.mapAngle(all_angs[:, 2], ome_period)


        det_xy, _ = _project(all_angs, rD, rC, chi, tD,
                             tC, tS, distortion)

        _write_pixels(det_xy, all_angs[:,2], image_stack, experiment.base,
                      experiment.inv_deltas, experiment.clip_vals)

        controller.update(i+1)

    controller.finish(subprocess)
    return image_stack


# ==============================================================================
# %% ORIENTATION TESTING
# ==============================================================================


def _grand_loop(image_stack, all_angles, test_crds, experiment, controller):
    n_grains = experiment.n_grains
    n_coords = controller.limit('coords', len(test_crds))

    confidence = np.empty((n_grains, n_coords))
    subprocess = 'grand_loop'

    _project = xrdutil._project_on_detector_plane

    controller.start(subprocess, n_coords * n_grains)
    for icrd in range(n_coords):
        for igrn in range(n_grains):
            angles = all_angles[igrn]
            det_xy, rMat_ss = _project(angles,
                                       experiment.rMat_d,
                                       experiment.rMat_c[igrn],
                                       experiment.chi,
                                       experiment.tVec_d,
                                       test_crds[icrd],
                                       experiment.tVec_s,
                                       experiment.distortion)
            indices = _quant_and_clip(det_xy, angles[:,2],
                                      experiment.base,
                                      experiment.inv_deltas,
                                      experiment.clip_vals)
            col_indices = indices[:, 0]
            row_indices = indices[:, 1]
            frame_indices = indices[:, 2]
            confidence[igrn, icrd] = _confidence_check(image_stack,
                                                       frame_indices,
                                                       row_indices,
                                                       col_indices,
                                                       experiment.row_dilation,
                                                       experiment.col_dilation,
                                                       experiment.nrows,
                                                       experiment.ncols)
        controller.update(icrd*n_grains)
    controller.finish(subprocess)
    controller.handle_result("confidence", confidence)


@numba.njit
def _v3_normalized(src, dst):
    v0 = src[0]
    v1 = src[1]
    v2 = src[2]
    sqr_norm = v0*v0 + v1*v1 + v2*v2
    inv_norm = 1.0 if sqr_norm == 0.0 else 1./np.sqrt(sqr_norm)

    dst[0] = v0 * inv_norm
    dst[1] = v1 * inv_norm
    dst[2] = v2 * inv_norm

    return dst

@numba.njit
def _make_binary_rot_mat(src, dst):
    v0 = src[0]; v1 = src[1]; v2 = src[2]

    dst[0,0] = 2.0*v0*v0 - 1.0
    dst[0,1] = 2.0*v0*v1
    dst[0,2] = 2.0*v0*v2
    dst[1,0] = 2.0*v1*v0
    dst[1,1] = 2.0*v1*v1 - 1.0
    dst[1,2] = 2.0*v1*v2
    dst[2,0] = 2.0*v2*v0
    dst[2,1] = 2.0*v2*v1
    dst[2,2] = 2.0*v2*v2 - 1.0

    return dst


# tC varies per coord
# gvec_cs, rSm varies per grain
#
# gvec_cs
beam = xf.bVec_ref[:, 0]
Z_l = xf.Zl[:,0]
@numba.jit()
def _gvec_to_detector_array(vG_sn, rD, rSn, rC, tD, tS, tC):
    """ beamVec is the beam vector: (0, 0, -1) in this case """
    ztol = xrdutil.epsf
    p3_l = np.empty((3,))
    tmp_vec = np.empty((3,))
    vG_l = np.empty((3,))
    tD_l = np.empty((3,))
    norm_vG_s = np.empty((3,))
    norm_beam = np.empty((3,))
    tZ_l = np.empty((3,))
    brMat = np.empty((3,3))
    result = np.empty((len(rSn), 2))

    _v3_normalized(beam, norm_beam)
    _m33_v3_multiply(rD, Z_l, tZ_l)

    for i in xrange(len(rSn)):
        _m33_v3_multiply(rSn[i], tC, p3_l)
        p3_l += tS
        p3_minus_p1_l = tD - p3_l

        num = _v3_dot(tZ_l, p3_minus_p1_l)
        _v3_normalized(vG_sn[i], norm_vG_s)

        _m33_v3_multiply(rC, norm_vG_s, tmp_vec)
        _m33_v3_multiply(rSn[i], tmp_vec, vG_l)

        bDot = -_v3_dot(norm_beam, vG_l)

        if bDot < ztol or bDot > 1.0 - ztol:
            result[i, 0] = np.nan
            result[i, 1] = np.nan
            continue

        _make_binary_rot_mat(vG_l, brMat)
        _m33_v3_multiply(brMat, norm_beam, tD_l)
        denom = _v3_dot(tZ_l, tD_l)

        if denom < ztol:
            result[i, 0] = np.nan
            result[i, 1] = np.nan
            continue

        u = num/denom
        tmp_res = u*tD_l - p3_minus_p1_l
        result[i,0] = _v3_dot(tmp_res, rD[:,0])
        result[i,1] = _v3_dot(tmp_res, rD[:,1])

    return result

def _grand_loop_inner(confidence, image_stack, angles, precomp, coords,
                      experiment, start=0, stop=None):
    n_coords = len(coords)
    n_angles = len(angles)
    rD = experiment.rMat_d
    rCn = experiment.rMat_c
    tD = experiment.tVec_d[:,0]
    tS = experiment.tVec_s[:,0]
    distortion = experiment.distortion
    _to_detector = xfcapi.gvecToDetectorXYArray
    #_to_detector = _gvec_to_detector_array
    stop = stop if stop is not None else n_coords

    distortion_fn = None
    if distortion is not None and len(distortion > 0):
        distortion_fn, distortion_args = distortion

    if distortion_fn is None:
        for igrn in xrange(n_angles):
            angs = angles[igrn]; rC = rCn[igrn]; gvec_cs, rMat_ss = precomp[igrn]
            for icrd in xrange(start, stop):
                det_xy = _to_detector(gvec_cs, rD, rMat_ss, rC, tD, tS, coords[icrd])
                c = _quant_and_clip_confidence(det_xy, angs[:,2],
                                               image_stack, experiment.base,
                                               experiment.inv_deltas,
                                               experiment.clip_vals)
                confidence[igrn, icrd] = c
    else:
        for igrn in xrange(n_angles):
            angs = angles[igrn]; rC = rCn[igrn]; gvec_cs, rMat_ss = precomp[igrn]
            for icrd in xrange(start, stop):
                det_xy = _to_detector(gvec_cs, rD, rMat_ss, rC, tD, tS, coords[icrd])
                det_xy = distortion_fn(tmp_xys, distortion_args, invert=True)
                c = _quant_and_clip_confidence(det_xy, angs[:,2],
                                               image_stack, experiment.base,
                                               experiment.inv_deltas,
                                               experiment.clip_vals)
                confidence[igrn, icrd] = c

    return stop - start

def _grand_loop_precomp(image_stack, all_angles, test_crds, experiment, controller):
    """grand loop precomputing the grown image stack"""
    subprocess = 'dilate image_stack'

    dilation_shape = np.ones((2*experiment.row_dilation + 1,
                              2*experiment.col_dilation + 1),
                             dtype=np.uint8)
    image_stack_dilated = np.empty_like(image_stack)
    n_images = len(image_stack)
    controller.start(subprocess, n_images)
    for i_image in range(n_images):
        ski_dilation(image_stack[i_image], dilation_shape, out=image_stack_dilated[i_image])
        controller.update(i_image+1)
    controller.finish(subprocess)

    n_grains = experiment.n_grains
    n_coords = controller.limit('coords', len(test_crds))
    _project = xrdutil._project_on_detector_plane
    chunk_size = controller.get_chunk_size()
    ncpus = controller.get_process_count()

    # precompute per-grain stuff
    subprocess = 'precompute gVec_cs'
    controller.start(subprocess, len(all_angles))
    gvec_cs_precomp = []
    for i, angs in enumerate(all_angles):
        rMat_ss = xfcapi.makeOscillRotMatArray(experiment.chi, angs[:,2])
        gvec_cs = _anglesToGVec(angs, rMat_ss, experiment.rMat_c[i])
        gvec_cs_precomp.append((gvec_cs, rMat_ss))
    controller.finish(subprocess)

    # split on coords
    chunks = xrange(0, n_coords, chunk_size)
    subprocess = 'grand_loop'
    controller.start(subprocess, n_coords)
    finished = 0
    ncpus = min(ncpus, len(chunks))

    if ncpus > 1:
        shared_arr = multiprocessing.Array('d', n_grains * n_coords)
        confidence = np.ctypeslib.as_array(shared_arr.get_obj()).reshape(n_grains, n_coords)
        with multiproc_state(chunk_size, confidence, image_stack_dilated, all_angles,
                             gvec_cs_precomp, test_crds, experiment):
            pool = multiprocessing.Pool(ncpus)
            for count in pool.imap_unordered(multiproc_inner_loop, chunks):
                finished += count
                controller.update(finished)
            del pool
    else:
        confidence = np.empty((n_grains, n_coords))
        for chunk_start in chunks:
            chunk_stop = min(n_coords, chunk_start+chunk_size)
            count =_grand_loop_inner(confidence, image_stack_dilated,
                                     all_angles, gvec_cs_precomp, test_crds,
                                     experiment, start=chunk_start,
                                     stop=chunk_stop)
            finished += count
            controller.update(finished)

    controller.finish(subprocess)
    controller.handle_result("confidence", confidence)


def multiproc_inner_loop(chunk):
    chunk_size = _mp_state[0]
    n_coords = len(_mp_state[5])
    chunk_stop = min(n_coords, chunk+chunk_size)
    return _grand_loop_inner(*_mp_state[1:], start=chunk, stop=chunk_stop)

@contextmanager
def multiproc_state(*args): #chunk_size, confidence, image_stack, angles, coords, experiment):
    # save = ( chunk_size,
    #          confidence,
    #          image_stack,
    #          angles,
    #          coords,
    #          experiment )
    global _mp_state
    _mp_state = args
    yield
    del(_mp_state)


def test_orientations(image_stack, grain_params, experiment,
                      controller):

    # this should be parametrized somehow and be part of "experiment"
    panel_buffer = 0.05
    all_angles=evaluate_diffraction_angles(experiment,
                                           controller)
    # test grid
    # cvec_s = 0.001 * np.arange(-250, 251)[::5]
    cvec_s = np.linspace(-0.25, 0.25, 101)
    Xs, Ys, Zs = np.meshgrid(cvec_s, cvec_s, cvec_s)
    test_crds = np.vstack([Xs.flatten(), Ys.flatten(), Zs.flatten()]).T

    # compute required dilation

    # projection function

    # a more parametric description of the sensor:
    _grand_loop_precomp(image_stack, all_angles, test_crds, experiment, controller)


def evaluate_diffraction_angles(experiment , controller=None):
    panel_dims_expanded = [(-10, -10), (10, 10)]
    subprocess='evaluate diffraction angles'
    pbar = controller.start(subprocess,
                            len(experiment.exp_maps))
    all_angles = []
    ref_gparams = np.array([0., 0., 0., 1., 1., 1., 0., 0., 0.])
    for i, exp_map in enumerate(experiment.exp_maps):
        gparams = np.hstack([exp_map, ref_gparams])
        sim_results = xrdutil.simulateGVecs(experiment.plane_data,
                                            experiment.detector_params,
                                            gparams,
                                            panel_dims=panel_dims_expanded,
                                            pixel_pitch=experiment.pixel_size,
                                            ome_range=experiment.ome_range,
                                            ome_period=experiment.ome_period,
                                            distortion=None)
        all_angles.append(sim_results[2])
        controller.update(i+1)
        pass
    controller.finish(subprocess)

    return all_angles


@numba.jit
def _check_with_dilation(image_stack,
                         frame_index, row_index, col_index,
                         row_dilation, col_dilation, nrows, ncols):
    min_row = max(row_index-row_dilation, 0)
    max_row = min(row_index+row_dilation + 1, nrows)
    min_col = max(col_index-col_dilation, 0)
    max_col = min(col_index+col_dilation + 1, ncols)

    for r in range(min_row, max_row):
        for c in range(min_col, max_col):
            if image_stack[frame_index, r, c]:
                return 1.0 # found, win!
    return 0.0 # not found, lose!


@numba.jit
def _confidence_check(image_stack,
                      frame_indices, row_indices, col_indices,
                      row_dilation, col_dilation, nrows, ncols):
    count = len(frame_indices)
    acc_confidence = 0.0
    for current in range(count):
        val = _check_with_dilation(image_stack, frame_indices[current],
                                   row_indices[current], col_indices[current],
                                   row_dilation, col_dilation, nrows, ncols)
        acc_confidence += val

    return acc_confidence/float(count)

@numba.jit
def _confidence_check_dilated(image_stack_dilated,
                              frame_indices, row_indices, col_indices):
    count = len(frame_indices)
    acc_confidence = 0.0
    for current in range(count):
        acc_confidence += image_stack_dilated[frame_indices[current],
                                              row_indices[current],
                                              col_indices[current]]

    return acc_confidence/float(count)


@numba.njit
def _quant_and_clip(coords, angles, base, inv_deltas, clip_vals):
    """quantize and clip the parametric coordinates in coords + angles

    coords - (..., 2) array: input 2d parametric coordinates
    angles - (...) array: additional dimension for coordinates
    base   - (3,) array: base value for quantization (for each dimension)
    inv_deltas - (3,) array: inverse of the quantum size (for each dimension)
    clip_vals - (2,) array: clip size (only applied to coords dimensions)

    clipping is performed on ranges [0, clip_vals[0]] for x and
    [0, clip_vals[1]] for y

    returns an array with the quantized coordinates, with coordinates
    falling outside the clip zone filtered out.

    """
    count = len(coords)
    a = np.zeros((count, 3), dtype=np.int32)

    curr = 0
    for i in range(count):
        x = int(np.floor((coords[i, 0] - base[0]) * inv_deltas[0]))

        if x < 0 or x >= clip_vals[0]:
            continue

        y = int(np.floor((coords[i, 1] - base[1]) * inv_deltas[1]))

        if y < 0 or y >= clip_vals[1]:
            continue

        z = int(np.floor((angles[i] - base[2]) * inv_deltas[2]))

        a[curr, 0] = x
        a[curr, 1] = y
        a[curr, 2] = z
        curr += 1

    return a[:curr,:]

@numba.njit
def _quant_and_clip_confidence(coords, angles, image, base, inv_deltas, clip_vals):
    """quantize and clip the parametric coordinates in coords + angles

    coords - (..., 2) array: input 2d parametric coordinates
    angles - (...) array: additional dimension for coordinates
    base   - (3,) array: base value for quantization (for each dimension)
    inv_deltas - (3,) array: inverse of the quantum size (for each dimension)
    clip_vals - (2,) array: clip size (only applied to coords dimensions)

    clipping is performed on ranges [0, clip_vals[0]] for x and
    [0, clip_vals[1]] for y

    returns an array with the quantized coordinates, with coordinates
    falling outside the clip zone filtered out.

    """
    count = len(coords)

    in_sensor = 0
    matches = 0
    for i in range(count):
        xf = coords[i, 0]
        yf = coords[i, 1]

        xf = np.floor((xf - base[0]) * inv_deltas[0])
        if not xf >= 0.0:
            continue
        if not xf < clip_vals[0]:
            continue

        yf = np.floor((yf - base[1]) * inv_deltas[1])

        if not yf >= 0.0:
            continue
        if not yf < clip_vals[1]:
            continue

        zf = np.floor((angles[i] - base[2]) * inv_deltas[2])

        in_sensor += 1
        matches += image[int(zf), int(yf), int(xf)]

    return 0 if in_sensor == 0 else float(matches)/float(in_sensor)

# ==============================================================================
# %% SCRIPT ENTRY AND PARAMETER HANDLING
# ==============================================================================
def main(args, controller):
    grain_params, experiment = mockup_experiment()
    controller.handle_result('experiment', experiment)
    controller.handle_result('grain_params', grain_params)
    image_stack = get_simulate_diffractions(grain_params, experiment,
                                            controller=controller)

    test_orientations(image_stack, grain_params, experiment,
                      controller=controller)


def parse_args():
    try:
        default_ncpus = multiprocessing.cpu_count()
    except NotImplementedError:
        default_ncpus = 1

    parser = argparse.ArgumentParser()
    parser.add_argument("--inst-profile", action='append',
                        help="instrumented profile")
    parser.add_argument("--generate",
                        help="generate file with intermediate results")
    parser.add_argument("--check",
                        help="check against an file with intermediate results")
    parser.add_argument("--limit", type=int,
                        help="limit the size of the run")
    parser.add_argument("--ncpus", type=int, default=default_ncpus,
                        help="number of processes to use")
    parser.add_argument("--chunk-size", type=int, default=100,
                        help="chunk size for use in multiprocessing/reporting")
    args = parser.parse_args()

    keys = ['inst_profile', 'generate', 'check', 'limit', 'ncpus', 'chunk_size']

    print('\n'.join([': '.join([key, str(getattr(args, key))]) for key in keys]))

    return args


def build_controller(args):
    # builds the controller to use based on the args

    # result handle
    progress_handler = progressbar_progress_observer()

    if args.check is not None:
        if args.generate is not None:
            logging.warn("generating and checking can not happen at the same time, going with checking")

        result_handler = checking_result_handler(args.check)
    elif args.generate is not None:
        result_handler = saving_result_handler(args.generate)
    else:
        result_handler = forgetful_result_handler()

    controller = ProcessController(result_handler, progress_handler,
                                   ncpus=args.ncpus, chunk_size=args.chunk_size)
    if args.limit is not None:
        controller.set_limit('coords', lambda x: min(x, args.limit))

    return controller


if __name__=='__main__':
    FORMAT="%(relativeCreated)12d [%(process)6d/%(thread)6d] %(levelname)8s: %(message)s"
    logging.basicConfig(level=logging.NOTSET,
                        format=FORMAT)
    args= parse_args()


    if len(args.inst_profile) > 0:
        from hexrd.utils import profiler

        logging.debug("Instrumenting functions")
        profiler.instrument_all(args.inst_profile)

    controller = build_controller(args)
    main(args, controller)
    del controller

    if len(args.inst_profile) > 0:
        logging.debug("Dumping profiler results")
        profiler.dump_results(args.inst_profile)
