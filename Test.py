import streamlit as st
import pandas as pd
import numpy as np
import openseespy.opensees as ops
import openseespy.postprocessing.ops_vis as opsv
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("General 3D Beam Modeler - OpenSeesPy")

# --- INPUTS ---

st.sidebar.header("General Input Parameters")

# Default node input
default_nodes = """1, 0, 0, 0
2, 0, 0, 4
3, 4, 0, 4
4, 4, 4, 4"""

node_str = st.sidebar.text_area("Nodes (node_id, x, y, z)", value=default_nodes)

# Default element input
default_elements = """1, 1, 2, 0.04, 25e6, 9615384.6, 0.01172, 0.0002667, 0.0010667, 1
2, 2, 3, 0.04, 25e6, 9615384.6, 0.01172, 0.0002667, 0.0010667, 2
3, 3, 4, 0.04, 25e6, 9615384.6, 0.01172, 0.0002667, 0.0010667, 3"""

elem_str = st.sidebar.text_area("Elements (id, i, j, A, E, G, J, Iy, Iz, transf_tag)", value=default_elements)

# Default transformations
default_trans = """1, 0, -1, 0
2, 0, -1, 0
3, 1, 0, 0"""

trans_str = st.sidebar.text_area("Transformations (tag, x, y, z)", value=default_trans)

# Default fixities
default_fix = """1, 1, 1, 1, 1, 1, 1"""

fix_str = st.sidebar.text_area("Fixities (node_id, x, y, z, rx, ry, rz)", value=default_fix)

# Default mass
default_mass = """2, 200, 200, 200, 0.001, 0.001, 0.001
3, 200, 200, 200, 0.001, 0.001, 0.001
4, 200, 200, 200, 0.001, 0.001, 0.001"""

mass_str = st.sidebar.text_area("Masses (node_id, mx, my, mz, rx, ry, rz)", value=default_mass)

# Default loads
default_loads = """4, -40, -25, -30, 0, 0, 0"""

load_str = st.sidebar.text_area("Loads (node_id, Px, Py, Pz, Mx, My, Mz)", value=default_loads)

# Visualization
sfac = st.sidebar.slider("Deformation scale", 0.1, 50.0, 2.0)
modeNo = st.sidebar.slider("Mode shape number", 1, 6, 1)

# --- PROCESSING INPUTS ---

ops.wipe()
ops.model('basic', '-ndm', 3, '-ndf', 6)

# Parse and create nodes
for line in node_str.strip().split('\n'):
    nid, x, y, z = map(float, line.strip().split(','))
    ops.node(int(nid), x, y, z)

# Parse transformations
for line in trans_str.strip().split('\n'):
    tag, x, y, z = map(float, line.strip().split(','))
    ops.geomTransf('Linear', int(tag), x, y, z)

# Fixities
for line in fix_str.strip().split('\n'):
    parts = list(map(int, line.strip().split(',')))
    ops.fix(parts[0], *parts[1:])

# Masses
for line in mass_str.strip().split('\n'):
    parts = list(map(float, line.strip().split(',')))
    ops.mass(int(parts[0]), *parts[1:])

# Elements
for line in elem_str.strip().split('\n'):
    eid, ni, nj, A, E, G, J, Iy, Iz, trans = map(float, line.strip().split(','))
    ops.element('elasticBeamColumn', int(eid), int(ni), int(nj), A, E, G, J, Iy, Iz, int(trans))

# Loads
ops.timeSeries('Constant', 1)
ops.pattern('Plain', 1, 1)
for line in load_str.strip().split('\n'):
    parts = list(map(float, line.strip().split(',')))
    ops.load(int(parts[0]), *parts[1:])

# --- ANALYSIS ---
ops.constraints('Transformation')
ops.numberer('RCM')
ops.system('BandGeneral')
ops.test('NormDispIncr', 1e-6, 6)
ops.algorithm('Linear')
ops.integrator('LoadControl', 1.0)
ops.analysis('Static')
ops.analyze(1)

# --- VISUALIZATION ---

st.subheader("Undeformed Structure")
fig_model = opsv.plot_model(show=False)
st.pyplot(fig_model)

st.subheader("Deformed Shape")
fig_def = opsv.plot_defo(sfac, 9, fmt_interp='b-', show=False)
st.pyplot(fig_def)

eigVals = ops.eigen(6)
st.subheader(f"Mode Shape {modeNo}")
fig_mode = opsv.plot_mode_shape(modeNo, sfac*10, 19, fmt_interp='b-', show=False)
st.pyplot(fig_mode)

st.subheader("Internal Forces")
forces = ['N', 'Vy', 'Vz', 'My', 'Mz', 'T']
labels = ['Axial', 'Shear Y', 'Shear Z', 'Moment Y', 'Moment Z', 'Torsion']
scales = [1e-2, 5e-2, 5e-2, 1e-2, 1e-2, 1e-2]

for f, lbl, sf in zip(forces, labels, scales):
    fig = plt.figure()
    minY, maxY = opsv.section_force_diagram_3d(f, {}, sf, show=False)
    plt.title(f"{lbl}: min = {minY:.2f}, max = {maxY:.2f}")
    st.pyplot(fig)
