import pytest # for tests
import os # for path names
import numpy as np  # arrays and maths
from WallSpeed.Grid import Grid
from WallSpeed.Polynomial import Polynomial
from WallSpeed.Boltzmann import BoltzmannSolver


real_path = os.path.realpath(__file__)
dir_path = os.path.dirname(real_path)


@pytest.mark.parametrize(
    "M, N, a, b, c, d, e, f",
    [#(10, 10, 1, 0, 0, 1, 0, 0),
    (25, 25, 1, 0, 0, 1, 0, 0)]
)
def test_Delta00(background, particle, M, N, a, b, c, d, e, f):
    r"""
    Tests that the Delta integral gives a known analytic result for
    :math:`\delta f = E \sqrt{(1 - \rho_z^2)(1 - \rho_\Vert)}`.
    """
    # setting up objects
    grid = Grid(M, N, 1, 1)
    poly = Polynomial(grid)
    boltzmann = BoltzmannSolver(grid, background, particle)

    # coordinates
    chi, rz, rp = grid.getCompactCoordinates() # compact
    rz = rz[np.newaxis, :, np.newaxis]
    rp = rp[np.newaxis, np.newaxis, :]
    xi, pz, pp = grid.getCoordinates() # non-compact
    pz = pz[np.newaxis, :, np.newaxis]
    pp = pp[np.newaxis, np.newaxis, :]

    # fluctuation mode
    msq = particle.msqVacuum(background.fieldProfile)
    msq = msq[:, np.newaxis, np.newaxis]
    E = np.sqrt(msq + pz**2 + pp**2)

    # integrand with known result
    eps = 2e-16
    integrand_analytic = E * (1 - rz**2) * (1 - rp) / (np.log(2 / (1 - rp)) + eps)
    integrand_analytic *= (a + b * rz + c * rz**2)
    integrand_analytic *= (d + e * rp + f * rp**2)

    # doing computation
    Deltas = boltzmann.getDeltas(integrand_analytic)

    # comparing to analytic result
    Delta00_analytic = background.temperatureProfile**3 * (
        2 / (9 * np.pi**2) * (3 * a + c) * (3 * d + f)
    )
    ratios = Deltas["00"] / Delta00_analytic

    # asserting result
    np.testing.assert_allclose(ratios, np.ones(M - 1), rtol=1e-2, atol=0)
