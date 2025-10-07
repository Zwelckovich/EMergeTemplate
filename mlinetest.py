# -----------------------------------------------------------------------------
# Microstrip template and Adaptive mesh refinement
#
# -----------------------------------------------------------------------------


import emerge as em
from emerge.plot import plot_sp

############################################################
#                    CONSTANT DEFINITION                   #
############################################################


SIMULATION_PARAMS = {
    # Geometry parameters
    "W": 90,  # Width in um
    "H": 101.6,  # Height in um
    "T": 5,  # Thickness in um
    "length": 560,  # Length of the MLine in um (560 μm)
    "wgnd_multiplier": 20,  # Ground plane width = W * wgnd_multiplier
    # Frequency parameters
    "f_start": 1e9,  # Start frequency in Hz
    "f_stop": 110e9,  # Stop frequency in Hz
    "f_step": 1e9,  # Frequency step size in Hz (1 GHz steps)
    # Material parameters
    "ep_r": 9.6,  # Relative permittivity
    "cond": 4.561e7,  # Conductivity in S/m
    "tanD": 0.0003,  # Loss tangent
    "rough": 0.2e-6,  # Surface roughness in meters
    "f_epr_tand": 10e9,  # Frequency for Epsilon_r and tanD
    # Derived parameters
    "rho": lambda: 1 / SIMULATION_PARAMS["cond"],  # Resistivity in Ohm*m
    "wgnd": lambda: SIMULATION_PARAMS["W"]
    * SIMULATION_PARAMS["wgnd_multiplier"],  # Ground plane width
    # Units
    "m": 1,  # m, Definition
    "mm": 1e-3,  # mm, Definition
    "um": 1e-6,  # um, Definition
}


############################################################
#                     SIMULATION SETUP                    #
############################################################

# We will invoke thSe SimulationBeta class because it houses some specific
# implementation details required for adaptive mesh refinement.
m = em.SimulationBeta("Transition")

# We can define the material using the Material class. Just supply the dielectric properties and you are done!
pcbmat = em.Material(
    er=SIMULATION_PARAMS["ep_r"],
    tand=SIMULATION_PARAMS["tanD"],
    color="#217627",
    opacity=0.3,
)

tracemat = em.Material(
    cond=SIMULATION_PARAMS["cond"],
    color="#62290c",
    opacity=1.0,
    _metal=True,
    name="Gold",
)

# Next we create the PCB designer class instance.
pcb = em.geo.PCB(
    thickness=SIMULATION_PARAMS["H"],
    unit=SIMULATION_PARAMS["um"],
    material=pcbmat,
    trace_material=tracemat,
    trace_thickness=SIMULATION_PARAMS["T"],
)

# We can use this function to compute the microstripline impedance. Right now (version 1.1) it just assumes top vs bottom layer.
# w0 = pcb.calc.z0(50)

# We start a new simple microstripline at xy=(0,0) and go Lfeed forward.
pcb.new(x=0, y=0, width=SIMULATION_PARAMS["W"], direction=(0, 1)).store("p1").straight(
    SIMULATION_PARAMS["length"]
).store("p2")

# Then finally we generate all our paths.
# They will be returned in the following order
#    1. All stripline paths in order of creation
#    2. All polygon geometries

trace = pcb.compile_paths()

# After generation of all geometries we can determine the bounds. We will add 20mm of margin to the left and back of
# our PCB domain. We start at the front and end at the right.
pcb.determine_bounds(leftmargin=900, topmargin=0, rightmargin=900, bottommargin=0)

# We add a ground plane on the bottom.
ground = pcb.plane(pcb.z(0))

# We add two modal port surfaces at the nodes p1 and p2
mp1 = pcb.modal_port(
    pcb.load("p1"), height=2 * SIMULATION_PARAMS["W"], width_multiplier=6
)
mp2 = pcb.modal_port(
    pcb.load("p2"), height=2 * SIMULATION_PARAMS["W"], width_multiplier=6
)

# Finally we generate the PCB, top air and bottom air.
diel = pcb.generate_pcb()
air_top = pcb.generate_air(height=2 * SIMULATION_PARAMS["W"])

# With Commit geometry we say: here we are done generating our model.
m.commit_geometry()

# Viewing model before mesh
m.view()

# We set the frequency range from 1GHz to 110GHz in 110 steps.
m.mw.set_frequency_range(1e9, 110e9, 110)

# We don't use any manual refinement steps to illustrate the power of
# Adaptive Mesh refinement.
# We generate the mesh and view it
m.generate_mesh()

# Notice the course initial mesh
m.view(plot_mesh=False)
m.view(plot_mesh=True)


############################################################
#                    BOUNDARY CONDITIONS                   #
############################################################

# Here we define our boundary conditions.
p1 = m.mw.bc.ModalPort(mp1, 1, modetype="TEM")
p2 = m.mw.bc.ModalPort(mp2, 2, modetype="TEM")

############################################################
#                        SIMULATION                       #
############################################################

# First we call the Adaptive Mesh Refinement routine. We refine at 6GHz because this is in the pass-band.
# We set show_mesh to True so we can see the progress of refinement for the purspose of this example.
# This halts the simulation so we have to click away the window to proceed.
# You can see that more nodes are added around the signal traces because the E-field error is highest
m.adaptive_mesh_refinement(frequency=20e9, show_mesh=False, growth_rate=5)

# We can view the improvement in the refined mesh.
m.view(plot_mesh=True)

# Finally we start our solve with 4 parallel workers
data = m.mw.run_sweep(True, n_workers=4)


############################################################
#                      POST PROCESSING                     #
############################################################

# We make a convenient object name for the gridded S-parameter data and plot it.
g = data.scalar.grid

plot_sp(g.freq, [g.S(1, 1)], labels=["S11"], dblim=[-40, 0])
plot_sp(g.freq, [g.S(2, 1)], labels=["S21"], dblim=[-2, 0])
