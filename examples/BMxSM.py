"""
Benchmark model: xSM, as implemented earlier by Benoit
defines model, grid and top
"""
import numpy as np # arrays, maths and stuff
from pprint import pprint # pretty printing of dicts
from WallSpeed.Grid import Grid
from WallSpeed.Polynomial import Polynomial
from WallSpeed.Boltzmann import BoltzmannBackground, BoltzmannSolver
from WallSpeed.Thermodynamics import Thermodynamics
from WallSpeed.Hydro import Hydro
from WallSpeed import Particle, FreeEnergy, Model
from WallSpeed.EOM import EOM
import WallSpeed

"""
Grid
"""
M = 20
N = 20
grid = Grid(M, N, 0.05, 100)
poly = Polynomial(grid)

"""
Model definition
"""
mod = WallSpeed.Model(125, 120, 1.0, 0.9)
params = mod.params

Tc = None
Tn = 100

fxSM = WallSpeed.FreeEnergy(mod.Vtot, Tc, Tn, params=params)
Tc = fxSM.Tc
pprint(params)
print(f"{Tc=}, {Tn=}")
print("\nFree energy:", fxSM)
print(f"{fxSM([[0],[1]], 100)=}")
print(f"{fxSM.derivT([[0],[1]], 100)=}")
print(f"{fxSM.derivField([[0],[1]], 100)=}")


# defining particles which are out of equilibrium for WallGo
top = WallSpeed.Particle(
    "top",
    msqVacuum=lambda X: params["yt"]**2 * np.asanyarray(X)[0,...]**2,
    msqThermal=lambda T: params["yt"]**2 * T**2,
    statistics="Fermion",
    inEquilibrium=False,
    ultrarelativistic=False,
    collisionPrefactors=[params["g2"]**4, params["g2"]**4, params["g2"]**4],
)

"""
Define thermodynamics, hydrodynamics and equation of motion
"""
fxSM.interpolateMinima(0,1.2*fxSM.Tc,1)

thermo = Thermodynamics(fxSM)
hydro = Hydro(thermo)
eom = EOM(top, fxSM, grid, 2)
