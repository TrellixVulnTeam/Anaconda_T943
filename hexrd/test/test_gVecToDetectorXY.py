import sys, os, time
import numpy as np

from hexrd.xrd import transforms as xf
from hexrd.xrd import transforms_CAPI as xfcapi

# input parameters
bVec_ref = xf.bVec_ref

rMat_d = xf.makeDetectorRotMat( ( 0.0011546340766314521,
                                 -0.0040527538387122993,
                                 -0.0026221336905160211 ) ) 
tVec_d = np.array( [ [   -1.44904 ],
                     [   -3.235616],
                     [-1050.74026 ] ] )

chi    = -0.0011591608938627839
tVec_s = np.array([ [-0.15354144],
                    [ 0.        ],
                    [-0.23294777] ] )

rMat_c = xf.makeRotMatOfExpMap(np.array( [ [ 0.66931818],
                                           [-0.98578066],
                                           [ 0.73593251] ] ) )
tVec_c = np.array( [ [ 0.07547626],
                     [ 0.08827523],
                     [-0.02131205] ] )

rMat_s = xf.makeOscillRotMat([chi, 0.])

# ######################################################################
# Calculate pixel coordinates
#
pvec  = 204.8 * np.linspace(-1, 1, 2048)
dcrds = np.meshgrid(pvec, pvec)
XY    = np.vstack([dcrds[0].flatten(), dcrds[1].flatten()]).T

# Check the timings
start1 = time.clock()                      # time this
dangs1 = xf.detectorXYToGvec(XY, rMat_d, rMat_s,
                             tVec_d, tVec_s, tVec_c, 
                             beamVec=bVec_ref)
tTh_d1   = dangs1[0][0]
eta_d1   = dangs1[0][1]
gVec_l1  = dangs1[1]
elapsed1 = (time.clock() - start1)
print "Time for Python detectorXYToGvec: %f"%(elapsed1)

start2 = time.clock()                      # time this
dangs2 = xfcapi.detectorXYToGvec(XY, rMat_d, rMat_s,
                                 tVec_d, tVec_s, tVec_c, 
                                 beamVec=bVec_ref)
tTh_d2   = dangs2[0][0]
eta_d2   = dangs2[0][1]
gVec_l2  = dangs2[1]
elapsed2 = (time.clock() - start2)
print "Time for CAPI detectorXYToGvec: %f"%(elapsed2)

maxDiff_tTh = np.linalg.norm(tTh_d1-tTh_d2,np.inf)
print "Maximum disagreement in tTh:  %f"%maxDiff_tTh
maxDiff_eta = np.linalg.norm(eta_d1-eta_d2,np.inf)
print "Maximum disagreement in eta:  %f"%maxDiff_eta
maxDiff_gVec = np.linalg.norm(np.sqrt(np.sum(np.asarray(gVec_l1.T-gVec_l2)**2,1)),np.inf)
print "Maximum disagreement in gVec: %f"%maxDiff_gVec

gVec_c1 = np.dot(rMat_c.T,np.dot(rMat_s.T,gVec_l1))
gVec_c2 = np.ascontiguousarray(np.dot(rMat_c.T,np.dot(rMat_s.T,gVec_l2.T)).T)

start3 = time.clock()                      # time this
xy1 = xf.gvecToDetectorXY(gVec_c1,rMat_d,rMat_s,rMat_c,tVec_d,tVec_s,tVec_c,beamVec=bVec_ref)
elapsed3 = (time.clock() - start3)
print "Time for Python gvecToDetectorXY: %f"%(elapsed3)

maxDiff_xy = np.linalg.norm(np.sqrt(np.sum(np.asarray(XY-xy1)**2,1)),np.inf)
print "Maximum disagreement in gVec: %f"%maxDiff_xy

start4 = time.clock()                      # time this
xy2 = xfcapi.gvecToDetectorXY(gVec_c2,rMat_d,rMat_s,rMat_c,tVec_d,tVec_s,tVec_c,beamVec=bVec_ref)
elapsed4 = (time.clock() - start4)
print "Time for CAPI gvecToDetectorXY: %f"%(elapsed4)

maxDiff_xy = np.linalg.norm(np.sqrt(np.sum(np.asarray(XY-xy2)**2,1)),np.inf)
print "Maximum disagreement in gVec: %f"%maxDiff_xy
