import streamlit as st
import matplotlib.pyplot as plt
import openseespy.opensees as ops
import openseespy.postprocessing.ops_vis as opsv

def run_opensees_model():
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)

    b = 0.2
    h = 0.4
    A, Iz, Iy, J = 0.04, 0.0010667, 0.0002667, 0.01172
    E = 25.0e6
    G = 9615384.6
    Lx, Ly, Lz = 4., 4., 4.

    ops.node(1, 0., 0., 0.)
    ops.node(2, 0., 0., Lz)
    ops.node(3, Lx, 0., Lz)
    ops.node(4, Lx, Ly, Lz)

    ops.fix(1, 1, 1, 1, 1, 1, 1)
    lmass = 200.
    for node in [2, 3, 4]:
        ops.mass(node, lmass, lmass, lmass, 0.001, 0.001, 0.001)

    coordTransf = 'Linear'
    ops.geomTransf(coordTransf, 1, 0., -1., 0.)
    ops.geomTransf(coordTransf, 2, 0., -1., 0.)
    ops.geomTransf(coordTransf, 3, 1., 0., 0.)

    ops.element('elasticBeamColumn', 1, 1, 2, A, E, G, J, Iy, Iz, 1)
    ops.element('elasticBeamColumn', 2, 2, 3, A, E, G, J, Iy, Iz, 2)
    ops.element('elasticBeamColumn', 3, 3, 4, A, E, G, J, Iy, Iz, 3)

    ops.timeSeries('Constant', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(4, -40.0, -25.0, -30.0, 0., 0., 0.)

    ops.constraints('Transformation')
    ops.numberer('RCM')
    ops.system('BandGeneral')
    ops.test('NormDispIncr', 1.0e-6, 6, 2)
    ops.algorithm('Linear')
    ops.integrator('LoadControl', 1)
    ops.analysis('Static')
    ops.analyze(1)

    return b, h

def plot_figures(b, h):
    sfac = 2.0
    fig_wi_he = (10, 7)

    fig1 = opsv.plot_model()
    st.pyplot(fig1)

    fig2 = opsv.plot_defo(sfac, 9, fmt_interp='b-', az_el=(-68., 39.), fig_wi_he=fig_wi_he, endDispFlag=0)
    st.pyplot(fig2)

    fig3 = opsv.plot_defo(sfac, 19, fmt_interp='b-', az_el=(6., 30.), fig_wi_he=fig_wi_he)
    st.pyplot(fig3)

    eigValues = ops.eigen(6)
    fig4 = opsv.plot_mode_shape(6, 20.0, 19, fmt_interp='b-', az_el=(106., 46.), fig_wi_he=fig_wi_he)
    st.pyplot(fig4)

    Ew = {}
    fig5 = opsv.section_force_diagram_3d('N', Ew, 0.01)
    st.pyplot(fig5)

    fig6 = opsv.section_force_diagram_3d('Vy', Ew, 0.05)
    st.pyplot(fig6)

    fig7 = opsv.section_force_diagram_3d('Vz', Ew, 0.01)
    st.pyplot(fig7)

    fig8 = opsv.section_force_diagram_3d('My', Ew, 0.01)
    st.pyplot(fig8)

    fig9 = opsv.section_force_diagram_3d('Mz', Ew, 0.01)
    st.pyplot(fig9)

    fig10 = opsv.section_force_diagram_3d('T', Ew, 0.01)
    st.pyplot(fig10)

    ele_shapes = {
        1: ['circ', [h]],
        2: ['rect', [b, h]],
        3: ['I', [b, h, b / 10., h / 6.]]
    }
    fig11 = opsv.plot_extruded_shapes_3d(ele_shapes, fig_wi_he=fig_wi_he)
    st.pyplot(fig11)

# Streamlit layout
st.set_page_config(layout="wide")
st.title("3D Cantilever Beam Analysis using OpenSeesPy")

if st.button("Run OpenSeesPy Model"):
    b, h = run_opensees_model()
    st.success("Model run successfully. Generating plots...")
    plot_figures(b, h)
