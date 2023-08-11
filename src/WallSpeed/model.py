"""
Classes for user input of models
"""
from .helpers import derivative # derivatives for callable functions


class Particle:
    """Particle configuration

    A simple class holding attributes of an out-of-equilibrium particle as
    relevant for calculations of Boltzmann equations.
    """
    STATISTICS_OPTIONS = ["Fermion", "Boson"]

    def __init__(
        self,
        msqVaccum,
        msqThermal,
        statistics,
        collisionPrefactors,
    ):
        r"""Initialisation

        Parameters
        ----------
        msqVaccum : function
            Function :math:`m^2_0(\phi)`, should take a float and return one.
        msqThermal : function
            Function :math:`m^2_T(T)`, should take a float and return one.
        statistics : {\"Fermion\", \"Boson\"}
            Particle statistics.
        collisionPrefactors : list
            Coefficients of collision integrals, :math:`\sim g^4`, currently
            must be of length 3.

        Returns
        -------
        cls : Particle
            An object of the Particle class.
        """
        Particle.__validateInput(
            msqVaccum, msqThermal, statistics, collisionPrefactors,
        )
        self.msqVacuum = msqVaccum
        self.msqThermal = msqThermal
        self.statistics = statistics
        self.collisionPrefactors = collisionPrefactors

    @staticmethod
    def __validateInput(msqVaccum, msqThermal, statistics, collisionPrefactors):
        """
        Checks input fits expectations
        """
        fields = [1, 1]
        assert isinstance(msqVacuum(fields), float), \
            f"msqVacuum({fields}) must return float"
        T = 100
        assert isinstance(msqThermal(T), float), \
            f"msqThermal({T}) must return float"
        if statistics not in ParticleConfig.STATISTICS_OPTIONS:
            raise ValueError(
                f"{statistics=} not in {ParticleConfig.STATISTICS_OPTIONS}"
            )
        assert len(collisionPrefactors) == 3, \
            "len(collisionPrefactors) must be 3"


class FreeEnergy:
    def __init__(
        self,
        f,
        phi_eps=1e-3,
        T_eps=1e-3,
    ):
        r"""Initialisation

        Initialisation for FreeEnergy class from potential.

        Parameters
        ----------
        f : function
            Free energy density function :math:`f(\phi, T)`.
        phi_eps : float, optional
            Small value with which to take numerical derivatives with respect
            to the field.
        T_eps : float, optional
            Small value with which to take numerical derivatives with respect
            to the temperature.

        Returns
        -------
        cls : FreeEnergy
            An object of the FreeEnergy class.
        """
        self.f = f
        self.phi_eps = phi_eps
        self.T_eps = phi_eps


    def findPhases(self, T):
        """Finds all phases at a given temperature T

        Parameters
        ----------
        T : float
            The temperature for which to find the phases.

        Returns
        -------
        phases : array_like
            A list of phases

        """
        return np.array([[0, 0], [1.0, 1.7]])
