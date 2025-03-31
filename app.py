import streamlit as st
import openseespy.opensees as ops
import openseespy.postprocessing.ops_vis as opsv
import matplotlib.pyplot as plt
import pandas as pd
from math import sqrt

# Fixed section properties
A = 0.002      # Area in m²
E = 2e11       # Young's Modulus in Pa
Iz = 1.6e-5    # Moment of Inertia in m⁴

def parse_input(text, n_cols):
    lines = text.strip().split("\n")
    data = []
    for line in lines:
        parts = line.strip().replace(",", " ").split()
        if len(parts) >= n_cols:
            data.append([float(p) if '.' in p or 'e' in p.lower() else int(p) for p in parts[:n_cols]])
    return data

def run_analysis(nodes, elements, point_loads, uniform_loads, boundary_conds, discretizations):
    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    for node in nodes:
        ops.node(*node)

    for bc in boundary_conds:
        tag, ux, uy, rz = bc
        ops.fix(tag, ux, uy, rz)

    ops.geomTransf('Linear', 1)

    ele_counter = 1
    Ew = {}

    for tag, iNode, jNode in elements:
        subdivision = next((int(d[1]) for d in discretizations if d[0] == tag), 1)
        xi, yi = [n[1:] for n in nodes if n[0] == iNode][0]
        xj, yj = [n[1:] for n in nodes if n[0] == jNode][0]

        dx = (xj - xi) / subdivision
        dy = (yj - yi) / subdivision

        prev_node = iNode
        for i in range(1, subdivision + 1):
            if i < subdivision:
                new_node_tag = max([n[0] for n in nodes]) + 1
                new_x = xi + i * dx
                new_y = yi + i * dy
                ops.node(new_node_tag, new_x, new_y)
                nodes.append([new_node_tag, new_x, new_y])
            else:
                new_node_tag = jNode

            ops.element('elasticBeamColumn', ele_counter, prev_node, new_node_tag, A, E, Iz, 1)
            Ew[ele_counter] = ['-beamUniform', 0.0, 0.0]
            prev_node = new_node_tag
            ele_counter += 1

    ops.timeSeries('Constant', 1)
    ops.pattern('Plain', 1, 1)

    for load in point_loads:
        nodeTag, Px, Py, Mz = load
        ops.load(nodeTag, Px, Py, Mz)

    for ul in uniform_loads:
        eleTag, Wy, Wx = ul
        Ew[eleTag] = ['-beamUniform', Wy, Wx]
        ops.eleLoad('-ele', eleTag, '-type', '-beamUniform', Wy, Wx)

    ops.constraints('Transformation')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test('NormDispIncr', 1.0e-6, 6)
    ops.algorithm('Linear')
    ops.integrator('LoadControl', 1)
    ops.analysis('Static')
    ops.analyze(1)

    return Ew

st.title("2D Frame Analysis with OpenSeesPy")

st.markdown("### Node Coordinates")
node_df = st.data_editor(
    pd.DataFrame({
        "tag": [1, 2, 3, 4],
        "x": [0.0, 0.0, 6.0, 6.0],
        "y": [0.0, 4.0, 0.0, 4.0],
    }),
    num_rows="dynamic",
    use_container_width=True
)
nodes = node_df.to_numpy().tolist()

st.markdown("### Element Connectivity")
element_df = st.data_editor(
    pd.DataFrame({
        "tag": [1, 2, 3],
        "iNode": [1, 3, 2],
        "jNode": [2, 4, 4],
    }),
    num_rows="dynamic",
    use_container_width=True
)
elements = element_df.to_numpy().tolist()

st.markdown("### Element Subdivision (Discretization)")
discrete_df = st.data_editor(
    pd.DataFrame({
        "eleTag": [1, 2, 3],
        "subdivisions": [1, 1, 1]
    }),
    num_rows="dynamic",
    use_container_width=True
)
discretizations = discrete_df.to_numpy().tolist()

st.markdown("### Boundary Conditions")
bc_df = st.data_editor(
    pd.DataFrame({
        "nodeTag": [1, 3],
        "UX": [1, 1],
        "UY": [1, 1],
        "RZ": [1, 1],
    }),
    num_rows="dynamic",
    use_container_width=True
)
boundary_conds = bc_df.to_numpy().tolist()

st.markdown("### Point Loads")
pl_df = st.data_editor(
    pd.DataFrame({
        "nodeTag": [2],
        "Px": [0.0],
        "Py": [0.0],
        "Mz": [0.0],
    }),
    num_rows="dynamic",
    use_container_width=True
)
point_loads = pl_df.to_numpy().tolist()

st.markdown("### Uniform Loads")
ul_df = st.data_editor(
    pd.DataFrame({
        "eleTag": [3],
        "Wy": [-1.0],
        "Wx": [0.0],
    }),
    num_rows="dynamic",
    use_container_width=True
)
uniform_loads = ul_df.to_numpy().tolist()

if st.button("Run Analysis"):
    st.session_state.run_analysis = True

if st.session_state.get("run_analysis", False):
    Ew = run_analysis(nodes, elements, point_loads, uniform_loads, boundary_conds, discretizations)

    st.subheader("Undeformed Model")
    fig = plt.figure()
    plt.clf()
    opsv.plot_model(1, 1, 1)
    plt.axis('off')
    st.pyplot(plt.gcf())

    st.subheader("Deformed Shape")

    x_coords = [node[1] for node in nodes]
    y_coords = [node[2] for node in nodes]
    x_range = max(x_coords) - min(x_coords) if x_coords else 1.0
    y_range = max(y_coords) - min(y_coords) if y_coords else 1.0

    ux_vals, uy_vals = [], []
    for node in nodes:
        tag = node[0]
        try:
            ux_vals.append(abs(ops.nodeDisp(tag, 1)))
            uy_vals.append(abs(ops.nodeDisp(tag, 2)))
        except:
            continue

    ux_max = max(ux_vals) if ux_vals else 0.0
    uy_max = max(uy_vals) if uy_vals else 0.0

    sfac_x = 0.01 * x_range / ux_max if ux_max > 0 else 1.0
    sfac_y = 0.01 * y_range / uy_max if uy_max > 0 else 1.0
    sfac = min(sfac_x, sfac_y)

    fig2 = plt.figure()
    plt.clf()
    opsv.plot_defo(sfac)
    plt.axis('off')
    st.pyplot(fig2)

    st.subheader("Moment Diagram")
    fig4 = plt.figure()
    minM, maxM = opsv.section_force_diagram_2d('M', Ew, 1e-6)
    maxAbsM = max(abs(minM), abs(maxM))
    sfacM = 1.0 / maxAbsM if maxAbsM != 0 else 1.0
    plt.clf()
    opsv.section_force_diagram_2d('M', Ew, sfacM)
    plt.axis('off')
    st.pyplot(fig4)

    st.subheader("Shear Force Diagram")
    fig5 = plt.figure()
    minT, maxT = opsv.section_force_diagram_2d('T', Ew, 1e-6)
    maxAbsT = max(abs(minT), abs(maxT))
    sfacV = 1.0 / maxAbsT if maxAbsT != 0 else 1.0
    plt.clf()
    opsv.section_force_diagram_2d('T', Ew, sfacV)
    plt.axis('off')
    st.pyplot(fig5)

    st.success("Analysis complete!")
