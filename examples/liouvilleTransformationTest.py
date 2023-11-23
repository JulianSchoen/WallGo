"""
Testing the construction of the Liouville operator and the source terms in the Boltzmann equation
"""
import numpy as np # arrays, maths and stuff
from pprint import pprint # pretty printing of dicts
import matplotlib.pyplot as plt
from scipy import integrate
from WallSpeed.Boltzmann import BoltzmannBackground, BoltzmannSolver
from WallSpeed.Thermodynamics import Thermodynamics
from WallSpeed.Polynomial2 import Polynomial2
#from WallSpeed.eomHydro import findWallVelocityLoop
from WallSpeed import Particle, FreeEnergy, Grid, Polynomial
import warnings



def __feq(x, statistics):
    if np.isclose(statistics, 1, atol=1e-14):
        return 1 / np.expm1(x)
    else:
        return 1 / (np.exp(x) + 1)
        
def __dfeq(x, statistics):
    x = np.asarray(x)
    if np.isclose(statistics, 1, atol=1e-14):
        return np.where(x > 100, -np.exp(-x), -np.exp(x) / np.expm1(x) ** 2)
    else:
        return np.where(
            x > 100, -np.exp(-x), -1 / (np.exp(x) + 2 + np.exp(-x))
        )
    
def chebToCard(matrix, poly):
    return np.einsum(
                "abc, ai, bj, ck -> ijk",
                matrix,
                poly.matrix("Cardinal", "z"),
                poly.matrix("Chebyshev", "pz"),
                poly.matrix("Chebyshev", "pp"),
                optimize=True,
            )

def cardToCheb(matrix, pzInvTransf, ppInvTransf):
    return np.einsum(
                "abc, bj, ck -> ajk",
                matrix,
                pzInvTransf,
                ppInvTransf,
                optimize=True,
            )

"""
Test objects
"""   
def buildLiouvilleOperator(self):
    """
    Constructs matrix and source for Boltzmann equation.

    Note, we make extensive use of numpy's broadcasting rules.
    """
    # coordinates
    xi, pz, pp = self.grid.getCoordinates()  # non-compact
    xi = xi[:, np.newaxis, np.newaxis]
    pz = pz[np.newaxis, :, np.newaxis]
    pp = pp[np.newaxis, np.newaxis, :]

    # intertwiner matrices
    TChiMat = self.poly.matrix(self.basisM, "z")
    TRzMat = self.poly.matrix(self.basisN, "pz")
    TRpMat = self.poly.matrix(self.basisN, "pp")

    # derivative matrices
    derivChi = self.poly.deriv(self.basisM, "z")
    derivRz = self.poly.deriv(self.basisN, "pz")

    # background profiles
    vw = self.background.vw
    msq = self.particle.msqVacuum(field)
    E = np.sqrt(msq + pz**2 + pp**2)
    
    msqpoly = Polynomial2(self.particle.msqVacuum(self.background.fieldProfile) ,self.grid,  'Cardinal','z', True)
    
    # dot products with wall velocity
    gammaWall = 1 / np.sqrt(1 - vw**2)
    PWall = gammaWall * (pz - vw * E)

    # spatial derivatives of profiles
    dmsqdChi = msqpoly.derivative(0).coefficients[1:-1, None, None]
    
    # derivatives of compactified coordinates
    dchidxi, drzdpz, drpdpp = self.grid.getCompactificationDerivatives()
    dchidxi = dchidxi[:, np.newaxis, np.newaxis]
    drzdpz = drzdpz[np.newaxis, :, np.newaxis]

    ##### liouville operator #####
    liouville = (
        dchidxi[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * PWall[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * derivChi[:, np.newaxis, np.newaxis, :, np.newaxis, np.newaxis]
            * TRzMat[np.newaxis, :, np.newaxis, np.newaxis, :, np.newaxis]
            * TRpMat[np.newaxis, np.newaxis, :, np.newaxis, np.newaxis, :]
        - dchidxi[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * drzdpz[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * gammaWall / 2
            * dmsqdChi[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * TChiMat[:, np.newaxis, np.newaxis, :, np.newaxis, np.newaxis]
            * derivRz[np.newaxis, :, np.newaxis, np.newaxis, :, np.newaxis]
            * TRpMat[np.newaxis, np.newaxis, :, np.newaxis, np.newaxis, :]
    )

    # returning results
    return liouville

 
def buildLiouvilleOperatorTransp(self):
    """
    Constructs matrix and source for Boltzmann equation.

    Note, we make extensive use of numpy's broadcasting rules.
    """
    # coordinates
    xi, pz, pp = self.grid.getCoordinates()  # non-compact
    xi = xi[:, np.newaxis, np.newaxis]
    pz = pz[np.newaxis, :, np.newaxis]
    pp = pp[np.newaxis, np.newaxis, :]

    # intertwiner matrices
    TChiMat = self.poly.matrix(self.basisM, "z")
    TRzMat = self.poly.matrix(self.basisN, "pz")
    TRpMat = self.poly.matrix(self.basisN, "pp")

    # derivative matrices
    derivChi = self.poly.deriv(self.basisM, "z")
    derivRz = self.poly.deriv(self.basisN, "pz")

    # background profiles
    vw = self.background.vw
    msq = self.particle.msqVacuum(field)
    E = np.sqrt(msq + pz**2 + pp**2)
    
    msqpoly = Polynomial2(self.particle.msqVacuum(self.background.fieldProfile) ,self.grid,  'Cardinal','z', True)
    
    # dot products with wall velocity
    gammaWall = 1 / np.sqrt(1 - vw**2)
    PWall = gammaWall * (pz - vw * E)

    # spatial derivatives of profiles
    dmsqdChi = msqpoly.derivative(0).coefficients[1:-1, None, None]
    
    # derivatives of compactified coordinates
    dchidxi, drzdpz, drpdpp = self.grid.getCompactificationDerivatives()
    dchidxi = dchidxi[:, np.newaxis, np.newaxis]
    drzdpz = drzdpz[np.newaxis, :, np.newaxis]

    ##### liouville operator #####
    liouville = (
        dchidxi[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * PWall[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * derivChi[:, np.newaxis, np.newaxis, :, np.newaxis, np.newaxis]
            * np.transpose(TRzMat)[np.newaxis, :, np.newaxis, np.newaxis, :, np.newaxis]
            * np.transpose(TRpMat)[np.newaxis, np.newaxis, :, np.newaxis, np.newaxis, :]
        - dchidxi[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * drzdpz[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * gammaWall / 2
            * dmsqdChi[:, :, :, np.newaxis, np.newaxis, np.newaxis]
            * np.transpose(TChiMat)[:, np.newaxis, np.newaxis, :, np.newaxis, np.newaxis]
            * derivRz[np.newaxis, :, np.newaxis, np.newaxis, :, np.newaxis]
            * np.transpose(TRpMat)[np.newaxis, np.newaxis, :, np.newaxis, np.newaxis, :]
    )

    # returning results
    return liouville


"""
Grid
"""
M = 20
N = 20
T = 100
L = 5/T
grid = Grid(M, N, L, T)
poly = Polynomial(grid)

"""
Background
"""
vw = 0
v = - np.ones(M - 1) / np.sqrt(3)
vev = 90
field = np.array([vev*(1-np.tanh(grid.xiValues/L))/2, vev*(1+np.tanh(grid.xiValues/L))/2])
T = 100 * np.ones(M - 1)
Tmid = (T[0]+T[-1])/2
basis = "Cardinal"
velocityMid = 0.5 * (v[0] + v[-1])

background = BoltzmannBackground(
    velocityMid=velocityMid,
    velocityProfile=np.concatenate(([v[0]],v,[v[-1]])),
    fieldProfile=np.concatenate((field[:,0,None],field,field[:,-1,None]),1),
    temperatureProfile=np.concatenate(([T[0]],T,[T[-1]])),
    polynomialBasis=basis,
)

"""
Particle
"""
particle = Particle(
    name="top",
    msqVacuum=lambda phi: 0.5 * phi[0]**2,
    msqThermal=lambda T: 0.1 * T**2,
    statistics="Fermion",
    inEquilibrium=False,
    ultrarelativistic=False,
    collisionPrefactors=[1, 1, 1],
)

"""
Boltzmann solver
"""
boltzmannCard = BoltzmannSolver(grid, background, particle, basisN="Cardinal")
boltzmannCheb = BoltzmannSolver(grid, background, particle)

Tpz = poly.matrix("Chebyshev", "pz")
Tpp = poly.matrix("Chebyshev", "pp")

TpzInv = np.linalg.inv(Tpz)
TppInv = np.linalg.inv(Tpp)

mat = np.random.rand(19,19,19)
matInCheb = cardToCheb(mat, TpzInv, TppInv)
sbMat = chebToCard(matInCheb, poly)

print(np.amin(np.abs(mat-sbMat)))
print(np.amax(np.abs(mat-sbMat)))

"""
Testing the Boltzmann solver
"""

liouCheb = buildLiouvilleOperator(boltzmannCheb)
liouCard = buildLiouvilleOperator(boltzmannCard)
liouChebTransp = buildLiouvilleOperatorTransp(boltzmannCheb)


randSource = np.einsum(
                "qweabc, abc -> qwe",
                liouCard,
                mat,
                optimize=True,
            )


sbRandSource = np.einsum(
                "qweabc, abc -> qwe",
                liouCheb,
                matInCheb,
                optimize=True,
            )

cbTranspRandSource = np.einsum(
                "qweabc, abc -> qwe",
                liouChebTransp,
                matInCheb,
                optimize=True,
            )


print(np.amin(np.abs(randSource-sbRandSource)))
print(np.amax(np.abs(randSource-sbRandSource)))

print(np.amin(np.abs(randSource-cbTranspRandSource)))
print(np.amax(np.abs(randSource-cbTranspRandSource)))

exit()






sbLiouCheb = np.einsum(
                "qweabc, ai, bj, ck -> qweijk",
                liouCard,
                np.transpose(boltzmannCheb.poly.matrix(boltzmannCheb.basisM, "z")),
                np.transpose(boltzmannCheb.poly.matrix(boltzmannCheb.basisN, "pz")),
                np.transpose(boltzmannCheb.poly.matrix(boltzmannCheb.basisN, "pp")),
                optimize=True,
            )

print(boltzmannCheb.poly.matrix(boltzmannCheb.basisM, "z"))

plt.plot((liouCheb-sbLiouCheb).flatten())
plt.ylabel(r"$L_{cheb}-L_{card}\cdot T$")
plt.xlabel("Flattened index")
plt.show()

exit()

fEq, sbFEq = buildEqDistrAndShouldBeEqDistr(boltzmann)

plt.plot(boltzmann.grid.xiValues, fEq[:,10,0], label=r"$S$")
plt.plot(boltzmann.grid.xiValues, sbFEq[:,10,0], label=r"$\tilde{S}=-L f_{eq}$")
plt.plot(boltzmann.grid.xiValues, (sbFEq-fEq)[:,10,0], label=r"$-(L f_{eq}+S)$")
plt.xlabel(r"$\xi$")
plt.legend()
plt.show()

plt.plot(fEq.flatten(), label=r"$S$")
plt.plot(sbFEq.flatten(), label=r"$\tilde{S}=-L f_{eq}$", alpha=0.5)
plt.plot((sbFEq-sbFEq).flatten(), label=r"$-(L f_{eq}+S)$")
plt.legend()
plt.show()


exit()

source, sbSource = buildEqDistrAndShouldBeEqDistr(boltzmann)

plt.plot(boltzmann.grid.xiValues, source[:,10,0], label=r"$S$")
plt.plot(boltzmann.grid.xiValues, sbSource[:,10,0], label=r"$\tilde{S}=-L f_{eq}$")
plt.plot(boltzmann.grid.xiValues, (sbSource-source)[:,10,0], label=r"$-(L f_{eq}+S)$")
plt.xlabel(r"$\xi$")
plt.legend()
plt.show()

plt.plot(source.flatten(), label=r"$S$")
plt.plot(sbSource.flatten(), label=r"$\tilde{S}=-L f_{eq}$", alpha=0.5)
plt.plot((sbSource-source).flatten(), label=r"$-(L f_{eq}+S)$")
plt.legend()
plt.show()

exit()

source, sbSource = buildSourceAndShouldBeSource(boltzmann)

plt.plot(boltzmann.grid.xiValues, source[:,10,0], label=r"$S$")
plt.plot(boltzmann.grid.xiValues, sbSource[:,10,0], label=r"$\tilde{S}=-L f_{eq}$")
plt.plot(boltzmann.grid.xiValues, (sbSource-source)[:,10,0], label=r"$-(L f_{eq}+S)$")
plt.xlabel(r"$\xi$")
plt.legend()
plt.show()

plt.plot(source.flatten(), label=r"$S$")
plt.plot(sbSource.flatten(), label=r"$\tilde{S}=-L f_{eq}$", alpha=0.5)
plt.plot((sbSource-source).flatten(), label=r"$-(L f_{eq}+S)$")
plt.legend()
plt.show()

