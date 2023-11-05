import numpy as np
import pytest
from WallSpeed.Polynomial2 import Polynomial
from WallSpeed.Grid import Grid

grid = Grid(4,4,1,1)

def test_evaluate():
    polyCard = Polynomial([-0.103553, 0.5, 0.603553],grid,'Cardinal','z',False)
    polyCheb = Polynomial([-0.25,-0.25,0],grid,'Chebyshev','z',False)
    x = [[-1,-0.3,0.2,0.7,1]]
    np.testing.assert_allclose(polyCard.evaluate(x),[0., 0.182, 0.672, 0.612, 0.],rtol=1e-5,atol=1e-5)
    np.testing.assert_allclose(polyCheb.evaluate(x),[0., 0.182, 0.672, 0.612, 0.],rtol=1e-5,atol=1e-5)
    
def test_changeBasis():
    polyCard = Polynomial([-0.103553, 0.5, 0.603553],grid,'Cardinal','z',False)
    polyCheb = Polynomial([-0.25,-0.25,0],grid,'Chebyshev','z',False)
    polyCard.changeBasis('Chebyshev')
    polyCheb.changeBasis('Cardinal')
    np.testing.assert_allclose(polyCard.coefficients, [-0.25,-0.25,0],rtol=1e-6,atol=1e-6)
    np.testing.assert_allclose(polyCheb.coefficients, [-0.103553, 0.5, 0.603553],rtol=1e-6,atol=1e-6)
    
def test_deriv():
    polyCard = Polynomial([-0.103553, 0.5, 0.603553],grid,'Cardinal','z',False)
    polyCheb = Polynomial([-0.25,-0.25,0],grid,'Chebyshev','z',False)
    
    derivCard = polyCard.derivative(0)
    derivCheb = polyCheb.derivative(0)
    
    np.testing.assert_allclose(derivCard.coefficients, [-1., 0.207107, 1., -1.20711, -3.],rtol=1e-5,atol=1e-5)
    np.testing.assert_allclose(derivCheb.coefficients, [-1., 0.207107, 1., -1.20711, -3.],rtol=1e-5,atol=1e-5)
    
    derivCheb.changeBasis('Chebyshev')
    np.testing.assert_allclose(derivCheb.coefficients, [-0.5,-1,-1.5,0,0],rtol=1e-5,atol=1e-5)
    
def test_integrate():
    polyCard = Polynomial([-0.103553, 0.5, 0.603553],grid,'Cardinal','z',False)
    polyCheb = Polynomial([-0.25,-0.25,0],grid,'Chebyshev','z',False)
    
    assert np.isclose(polyCard.integrate(w=1/np.sqrt(1-grid.chiValues**2)), np.pi/4,rtol=1e-5,atol=1e-5)
    assert np.isclose(polyCheb.integrate(w=1/np.sqrt(1-grid.chiValues**2)), np.pi/4,rtol=1e-5,atol=1e-5)
    
    




































    