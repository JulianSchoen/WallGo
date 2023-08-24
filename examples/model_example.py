"""
A first example.
"""
import numpy as np # arrays, maths and stuff
from pprint import pprint # pretty printing of dicts
from WallSpeed.Grid import Grid
from WallSpeed.Polynomial import Polynomial
from WallSpeed.Boltzmann import BoltzmannSolver
from WallSpeed.Thermodynamics import Thermodynamics
from WallSpeed.Hydro import Hydro
#from WallSpeed.eomHydro import findWallVelocityLoop
from WallSpeed import Particle, FreeEnergy, Model


print("--------------")
print("xSM model")
print("Testing the hydrodynamics against Benoit's earlier results")
mod = Model(125,120,1.0,0.9)
params = mod.params
pprint(params)

Tc = 108.22
Tn = 100
print(f"{Tc=}, {Tn=}")

fxSM = FreeEnergy(mod.Vtot, Tc, Tn, params=params)
print("\nFree energy:", fxSM)
print(f"{fxSM([0, 1], 100)=}")
print(f"{fxSM.derivT([0, 1], 100)=}")
print(f"{fxSM.derivField([0, 1], 100)=}")

# looking at thermodynamics
thermo = Thermodynamics(fxSM)
print("\nThermodynamics:", thermo)
print(f"{thermo.pSym(100)=}")
print(f"{thermo.pBrok(100)=}")
print(f"{thermo.ddpBrok(100)=}")

# checking Tplus and Tminus
print(f"{fxSM.findPhases(100.1)=}")
print(f"{fxSM.findPhases(103.1)=}")
thermo = Thermodynamics(fxSM)
hydro = Hydro(thermo)
vJ = hydro.vJ
c1, c2, Tplus, Tminus = hydro.findHydroBoundaries(0.5229)

print("Jouguet velocity")
print(vJ)
print(thermo.pBrok(100.1))
print(thermo.pSym(103.1))

print("c1,c2")
print(c1,c2)


# defining particles which are out of equilibrium for WallGo
top = Particle(
    "top",
    msqVacuum=lambda X: params["yt"]**2 * np.asanyarray(X)[..., 0]**2,
    msqThermal=lambda T: params["yt"]**2 * T**2,
    statistics="Fermion",
    inEquilibrium=False,
    ultrarelativistic=False,
    collisionPrefactors=[params["g2"]**4, params["g2"]**4, params["g2"]**4],
)
particles = [top]
print("\ntop quark:", top)

# grid size
M = 20
N = 20

# now compute the bubble wall speed
# findWallVelocityLoop
