"""Input binaries of the barotropic gyre setup: the tutorial's bathymetry and
wind stress (tutorial_barotropic_gyre/input/gendata.py, unchanged), plus the
initial temperature field and the control-weight file of the adjoint.

Run from input/:  python3 gendata.py   -> ../input_binaries/{bathy,windx_cosy,theta_init}.bin
                                        ../input_adj_binaries/ones_64b.bin
"""
import os
import numpy as np
from numpy import cos, pi

Ho = 5000; nx = 62; ny = 62; dx = 20; dy = 20
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'input_binaries')
adj = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'input_adj_binaries')
os.makedirs(out, exist_ok=True); os.makedirs(adj, exist_ok=True)

# flat bottom with walls on the four sides
h = -Ho * np.ones((ny, nx)); h[:, [0, -1]] = 0; h[[0, -1], :] = 0
h.astype('>f4').tofile(os.path.join(out, 'bathy.bin'))

# zonal wind stress -tauMax cos(pi y/L) at u-points (0 at the walls' outer rows)
tauMax = 0.1
y = (np.arange(ny) - .5) / (ny - 2)
Y = np.repeat(y[:, None], nx, axis=1)
(-tauMax * cos(Y * pi)).astype('>f4').tofile(os.path.join(out, 'windx_cosy.bin'))

# initial temperature: a meridional gradient, 25 C at the southern wall to
# 15 C at the northern wall, at cell centres. Passive (tAlpha = 0), so it
# only gives the forward field something to advect; the sensitivity does not
# depend on it.
yc = (np.arange(ny) - .5) / (ny - 2)          # 0 at y = 0 km, 1 at y = 1200 km
T = 25.0 - 10.0 * np.clip(yc, 0, 1)
np.repeat(T[:, None], nx, axis=1).astype('>f4').tofile(os.path.join(out, 'theta_init.bin'))

# uniform weight of the xx_theta control (one level)
np.ones((1, ny, nx)).astype('>f8').tofile(os.path.join(adj, 'ones_64b.bin'))
print('wrote', sorted(os.listdir(out)), 'and', sorted(os.listdir(adj)))
