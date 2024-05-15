import pytest
import numpy as np
import WallGo

@pytest.mark.parametrize(
    "wallThickness, tails, ratio",
    [
         (1,2.5,0.5),
         (0.5,1.25,0.5),
         (0.5,2.5,0.5),
         (1,5,0.25),
         (0.5,2.5,0.25),
         (0.5,5,0.25),
         (1,2.5,0.75),
         (0.5,1.25,0.75),
         (0.5,2.5,0.75),
     ]
)
def test_integration(wallThickness, tails, ratio):
    r"""
    Computes the integral :math:`\int dp dz\ m'(z)\frac{p}{E(e^E+1)}=2+\frac{\pi^2}{12}+\mathrm{Li}_2(-e^2)\approx -0.6914545487096899`, 
    with :math:`m(z)=1-\mathrm{tanh}(z)`, and compare it to the value computed from the Polynomial class.
    """
    N = 101
    M = 101
    grid = WallGo.Grid3Scales.Grid3Scales(M, N, tails, tails, wallThickness, 1, ratio)
    
    m = lambda z: 1-np.tanh(z)
    dmdz = lambda z: -1/np.cosh(z)**2
    p = lambda pz, pp: np.sqrt(pz**2+pp**2)
    E = lambda z, pz, pp: np.sqrt(p(pz,pp)**2+m(z)**2)
    func = lambda z, pz, pp: dmdz(z)*p(pz,pp)/(E(z,pz,pp)*(np.exp(E(z,pz,pp))+1))
    
    polyCoeff = func(grid.xiValues[:,None,None,], grid.pzValues[None,:,None], grid.ppValues[None,None,:])
    polynomial = WallGo.Polynomial(polyCoeff, grid, direction=('z','pz','pp'))
    
    integralExact = -0.6914545487096899
    dxidchi, dpzdrz, dppdrp = grid.getCompactificationDerivatives()
    integralPoly = polynomial.integrate(w=dxidchi[:,None,None]*dpzdrz[None,:,None]*dppdrp[None,None,:]*grid.ppValues[None,None,:]/(grid.ppValues[None,None,:]**2+grid.pzValues[None,:,None]**2)/2)
    
    assert np.isclose(integralExact, integralPoly,rtol=0,atol=1e-3)