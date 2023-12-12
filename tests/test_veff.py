import pytest
import numpy as np
import WallSpeed


def test_BM1():
    Tc = 108.22
    Tn = 100
    vJ = 0.6444
    vw = 0.5229
    c1 = -3331587978
    c2 = 2976953742
    Tplus = 103.1
    Tminus = 100.1
    mod = WallSpeed.Model(125, 120, 1.0, 0.9)
    params = mod.params
    res = mod.Vtot([[110],[130]], 100)
    assert res.shape == (1,)
    assert res == pytest.approx([-1.19018205e09], rel=1e-2)
    free = WallSpeed.FreeEnergy(mod.Vtot, Tc, Tnucl=Tn, params=params)
    res = free.findPhases(100)
    np.testing.assert_allclose(
        res, [[195.03215146, 0.0], [0.0, 104.86914171]], rtol=1e-2
    )
    res = free.findTc()
    assert res == pytest.approx(Tc, rel=1e-2)
    free.interpolateMinima(0, 1.2 * Tc, 1)
    thermo = WallSpeed.Thermodynamics(free)
    hydro = WallSpeed.Hydro(thermo)
    res = hydro.vJ
    assert res == pytest.approx(vJ, rel=1e-2)
    res = hydro.findHydroBoundaries(vw)
    np.testing.assert_allclose(res[:4], (c1, c2, Tplus, Tminus), rtol=1e-2)


def test_BM2():
    mod = WallSpeed.Model(125, 160.0, 1.0, 1.2)
    res = mod.Vtot([[100,110],[130,130]], 100)
    assert res.shape == (2,)
    np.testing.assert_allclose(
        res, [-1.16182579e+09, -1.15446813e+09], rtol=1e-2
    )

def test_BM3():
    mod = WallSpeed.Model(125, 160, 1.0, 1.6)
    res = mod.Vtot([[110],[130]], 100)
    assert res.shape == (1,)
    assert res == pytest.approx([-1.23684861e09], rel=1e-2)
    res = mod.Vtot([110,130], 100)
    assert res.shape == ()
    assert res == pytest.approx(-1.23684861e09, rel=1e-2)


def test_BM4():
    mod = WallSpeed.Model(125, 80, 1.0, 0.5)
    res = mod.Vtot([[100, 110],[100, 130]], 100)
    np.testing.assert_allclose(
        res, [-1210419844, -1.180062e+09], rtol=1e-2
    )