"""
A first example.
"""
import numpy as np # arrays, maths and stuff
from pprint import pprint # pretty printing of dicts
from WallSpeed.Boltzmann import BoltzmannBackground, BoltzmannSolver
from WallSpeed.Thermodynamics import Thermodynamics
#from WallSpeed.eomHydro import findWallVelocityLoop
from WallSpeed import Particle, FreeEnergy, Grid, Polynomial

"""
Grid
"""
M = 20
N = 20
grid = Grid(M, N, 1, 1)
poly = Polynomial(grid)

"""
Background
"""
vw = 1 / np.sqrt(3)
v = - np.ones(M - 1) / np.sqrt(3)
field = np.ones((M - 1,))
field[M // 2:]  = 0
T = 100 * np.ones(M - 1)
basis = "Cardinal"

background = BoltzmannBackground(
    vw=vw,
    velocityProfile=v,
    fieldProfile=field,
    temperatureProfile=T,
    polynomialBasis=basis,
)

"""
Particle
"""
particle = Particle(
    name="top",
    msqVacuum=lambda phi: 0.5 * phi**2,
    msqThermal=lambda T: 0.1 * T**2,
    statistics="Fermion",
    inEquilibrium=False,
    ultrarelativistic=False,
    collisionPrefactors=[1, 1, 1],
)

"""
Boltzmann solver
"""
boltzmann = BoltzmannSolver(grid, background, particle)
print("BoltzmannSolver object =", boltzmann)
operator, source = boltzmann.buildLinearEquations()
print("operator.shape =", operator.shape)
print("source.shape =", source.shape)

deltaF = boltzmann.solveBoltzmannEquations()
print("deltaF.shape =", deltaF.shape)
print("deltaF[:, 0, 0] =", deltaF[:, 0, 0])
print("deltaF[:, 0, 0] =", deltaF[:, 0, 0])

Deltas = boltzmann.getDeltas(deltaF)
print("Deltas =", Deltas)

# now making a deltaF by hand
deltaF = np.zeros(deltaF.shape)
# coordinates
chi, rz, rp = grid.getCompactCoordinates() # compact
xi, pz, pp = grid.getCoordinates() # non-compact
xi = xi[:, np.newaxis, np.newaxis]
pz = pz[np.newaxis, :, np.newaxis]
pp = pp[np.newaxis, np.newaxis, :]

# background
vFixed = background.velocityProfile[0]
T0 = background.temperatureProfile[0]

# fluctuation mode
msq = particle.msqVacuum(background.fieldProfile)
msq = msq[:, np.newaxis, np.newaxis]
E = np.sqrt(msq + pz**2 + pp**2)

# integrand with known result
integrand_analytic = (
    E
    * np.sqrt(1 - rz[np.newaxis, :, np.newaxis]**2)
    * np.sqrt(1 - rp[np.newaxis, np.newaxis, :])
)

# test with integrand_analytic
Deltas = boltzmann.getDeltas(integrand_analytic)
Deltas_analytic = 2 * np.sqrt(2) * background.temperatureProfile**3 / np.pi
print("Ratio = 1 =", Deltas["00"] / Deltas_analytic)
print("T =", background.temperatureProfile)
