"""
Class for the one-loop effective potential without high-temperature expansion
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
import typing
import numpy as np

from WallGo import EffectivePotential, EExtrapolationType

from .integrals import Integrals
from .utils import getSafePathToResource


class EImaginaryOption(Enum):
    """
    Enums for what to do with imaginary parts in the effective potential.
    """

    # Throw an error if imaginary part nonzero
    ERROR = auto()
    # Take absolute value of argument
    ABS_ARGUMENT = auto()
    # Take absolute value of result
    ABS_RESULT = auto()
    # Principal part
    PRINCIPAL_PART = auto()


class EffectivePotentialNoResum(EffectivePotential, ABC):
    r"""Class EffectivePotential_NoResum -- Specialization of the abstract
    EffectivePotential class that implements common functions for computing
    the 1-loop potential at finite temperature, without any
    assumptions regarding the temperature (no high- or low-T approximations).
    In some literature this would be the "4D effective potential".

    """

    SMALL_NUMBER: typing.Final[float] = 1e-100

    def __init__(
        self,
        integrals: Integrals = None,
        useDefaultInterpolation: bool = False,
        imaginaryOption: EImaginaryOption = EImaginaryOption.ERROR,
    ):
        """FIXME: if we intend to have this as a ready-to-use Veff template,
        we should do inits in __init_subclass__() instead.
        This way the user doesn't have to worry about calling super().__init__()"""
        # Option for how to deal with imaginary parts
        self.imaginaryOption = imaginaryOption

        # Use the passed Integrals object if provided,
        # otherwise create a new one
        if integrals:
            self.integrals = integrals
        else:
            # The default is an integral object without interpolation
            self.integrals = Integrals()

            # For the sake of speed, one can use interpolated integrals.
            # By setting useDefaultInterpolation to True, the default
            # interpolation tables provided by WallGo are used.
            if useDefaultInterpolation:
                # TODO: find better way of doing this
                from WallGo import PotentialTools  # import statement here to avoid circular import

                # TODO: this could be tidier
                PotentialTools.initialize()
                self.integrals = PotentialTools.defaultIntegrals

                self.integrals.Jb.disableAdaptiveInterpolation()
                self.integrals.Jf.disableAdaptiveInterpolation()

                self.integrals.Jb.setExtrapolationType(
                    extrapolationTypeLower=EExtrapolationType.CONSTANT,
                    extrapolationTypeUpper=EExtrapolationType.CONSTANT,
                )

                self.integrals.Jf.setExtrapolationType(
                    extrapolationTypeLower=EExtrapolationType.CONSTANT,
                    extrapolationTypeUpper=EExtrapolationType.CONSTANT,
                )

    @abstractmethod
    def bosonStuff(
        self, fields: np.ndarray, __temperature: float | np.ndarray
    ) -> tuple[
        np.ndarray,
        float | np.ndarray,
        float | np.ndarray,
        float | np.ndarray,
    ]:
        """
        Calculate the boson particle spectrum. Should be overridden by
        subclasses.

        Parameters
        ----------
        fields : array_like
            Field value(s).
            Either a single point (with length `Ndim`), or an array of points.
        temperature : float or array_like
            The temperature at which to calculate the boson masses. Can be used
            for including thermal mass corrrections. The shapes of `fields` and
            `temperature` should be such that ``fields.shape[:-1]`` and
            ``temperature.shape`` are broadcastable
            (that is, ``fields[0,...]*T`` is a valid operation).

        Returns
        -------
        massSq : array_like
            A list of the boson particle masses at each input point `X`. The
            shape should be such that
            ``massSq.shape == (X[...,0]*T).shape + (Nbosons,)``.
            That is, the particle index is the *last* index in the output array
            if the input array(s) are multidimensional.
        degreesOfFreedom : float or array_like
            The number of degrees of freedom for each particle. If an array
            (i.e., different particles have different d.o.f.), it should have
            length `Ndim`.
        c : float or array_like
            A constant used in the one-loop zero-temperature effective
            potential. If an array, it should have length `Ndim`. Generally
            `c = 1/2` for gauge boson transverse modes, and `c = 3/2` for all
            other bosons.
        rgScale : float or array_like
            Renormalization scale in the one-loop zero-temperature effective
            potential. If an array, it should have length `Ndim`. Typically, one
            takes the same rgScale for all particles, but different scales
            for each particle are possible.
        """

    @abstractmethod
    def fermionStuff(
        self, fields: np.ndarray, __temperature: float | np.ndarray
    ) -> tuple[
        np.ndarray,
        float | np.ndarray,
        float | np.ndarray,
        float | np.ndarray,
    ]:
        """
        Calculate the fermion particle spectrum. Should be overridden by
        subclasses.

        Parameters
        ----------
        fields : array_like
            Field value(s).
            Either a single point (with length `Ndim`), or an array of points.
        temperature : float or array_like

        Returns
        -------
        massSq : array_like
            A list of the fermion particle masses at each input point `field`. The
            shape should be such that  ``massSq.shape == (field[...,0]).shape``.
            That is, the particle index is the *last* index in the output array
            if the input array(s) are multidimensional.
        degreesOfFreedom : float or array_like
            The number of degrees of freedom for each particle. If an array
            (i.e., different particles have different d.o.f.), it should have
            length `Ndim`.
        c : float or array_like
            A constant used in the one-loop zero-temperature effective
            potential. If an array, it should have length `Ndim`. Generally
            `c = 3/2` for all fermions.
        rgScale : float or array_like
            Renormalization scale in the one-loop zero-temperature effective
            potential. If an array, it should have length `Ndim`. Typically, one
            takes the same rgScale for all particles, but different scales
            for each particle are possible.
        """

    @staticmethod
    def jCW(
        massSq: np.ndarray,
        degreesOfFreedom: int | np.ndarray,
        c: float | np.ndarray,
        rgScale: float | np.ndarray,
    ) -> float | np.ndarray:
        """
        Coleman-Weinberg potential

        Parameters
        ----------
        msq : array_like
            A list of the boson particle masses at each input point `X`.
        degreesOfFreedom : float or array_like
            The number of degrees of freedom for each particle. If an array
            (i.e., different particles have different d.o.f.), it should have
            length `Ndim`.
        c: float or array_like
            A constant used in the one-loop zero-temperature effective
            potential. If an array, it should have length `Ndim`. Generally
            `c = 1/2` for gauge boson transverse modes, and `c = 3/2` for all
            other bosons.
        rgScale : float or array_like
            Renormalization scale in the one-loop zero-temperature effective
            potential. If an array, it should have length `Ndim`. Typically, one
            takes the same rgScale for all particles, but different scales
            for each particle are possible.

        Returns
        -------
        jCW : float or array_like
            One-loop Coleman-Weinberg potential for given particle spectrum.
        """
        smallImagNumber = EffectivePotentialNoResum.SMALL_NUMBER * 1j
        return (
            degreesOfFreedom
            * massSq**2
            * (np.log(massSq / rgScale**2 + smallImagNumber) - c)
        ) / (64 * np.pi * np.pi)

    def potentialOneLoop(
        self, bosons: tuple, fermions: tuple, checkForImaginary: bool = False
    ) -> float | np.ndarray:
        """
        One-loop corrections to the zero-temperature effective potential
        in dimensional regularization.

        Parameters
        ----------
        bosons : array of floats
            bosonic particle spectrum (here: masses, number of dofs, ci)
        fermions : array of floats
            fermionic particle spectrum (here: masses, number of dofs)
        RGscale: float
            RG scale of the effective potential

        Returns
        -------
        potential : float
        """

        massSqB, nB, cB, rgScaleB = bosons
        massSqF, nF, cF, rgScaleF = fermions

        if self.imaginaryOption == EImaginaryOption.ABS_ARGUMENT:
            # one way to drop imaginary parts, replace x with |x|
            massSqB = abs(massSqB)
            massSqF = abs(massSqF)

        # constructing the potential
        potential = np.sum(self.jCW(massSqB, nB, cB, rgScaleB), axis=-1)
        potential -= np.sum(self.jCW(massSqF, nF, cF, rgScaleF), axis=-1)

        # checking for imaginary parts
        if np.any(massSqB < 0) or np.any(massSqF < 0):
            if self.imaginaryOption == EImaginaryOption.PRINCIPAL_PART:
                potential = potential.real
            elif self.imaginaryOption == EImaginaryOption.ABS_RESULT:
                potential = abs(potential)
            elif self.imaginaryOption == EImaginaryOption.ERROR:
                msqBMin = np.min(massSqB)
                msqFMin = np.min(massSqF)
                raise ValueError(
                    f"Im(Veff)={potential.imag}, Re(Veff)={potential.real}, min(msqB)={msqBMin}, min(msqF)={msqFMin}. "
                    "Choose imaginaryOption != EImaginaryOption.ERROR "
                    "when initialising EffectivePotentialNoResum."
                )
        else:
            # no imaginary parts arise if masses are all nonnegative
            potential = potential.real

        return potential

    def potentialOneLoopThermal(
        self,
        bosons: tuple,
        fermions: tuple,
        temperature: np.ndarray | float,
        checkForImaginary: bool = False,
    ) -> float | np.ndarray:
        """
        One-loop thermal correction to the effective potential without any
        temperature expansions.

        Parameters
        ----------
        bosons : ArrayLike
            bosonic particle spectrum (here: masses, number of dofs, ci)
        fermions : ArrayLike
            fermionic particle spectrum (here: masses, number of dofs)
        temperature: ArrayLike

        Returns
        -------
        potential : 4d 1loop thermal potential
        """

        # m2 is shape (len(T), 5), so to divide by T we need to transpose T,
        # or add new axis in this case.
        # But make sure we don't modify the input temperature array here.
        temperature = np.asanyarray(temperature)

        temperatureSq = temperature**2 + self.SMALL_NUMBER

        # Need reshaping mess for numpy broadcasting to work
        if temperatureSq.ndim > 0:
            temperatureSq = temperatureSq[:, np.newaxis]

        # Jb, Jf take (mass/T)^2 as input, np.array is OK.
        # Do note that for negative m^2 the integrals become wild and convergence
        # is both slow and bad, so you may want to consider taking the absolute
        # value of m^2. We will not enforce this however

        massSqB, nB, _, _ = bosons
        massSqF, nF, _, _ = fermions

        if self.imaginaryOption == EImaginaryOption.ABS_ARGUMENT:
            # one way to drop imaginary parts, replace x with |x|
            massSqB = np.abs(massSqB)
            massSqF = np.abs(massSqF)

        # Careful with the sum, it needs to be column-wise.
        # Otherwise things go horribly wrong with array T input.
        # TODO: really not a fan of hardcoded axis index

        # constructing the potential
        JbList = self.integrals.Jb(massSqB / temperatureSq)
        JfList = self.integrals.Jf(massSqF / temperatureSq)
        potential = np.sum(nB * np.asarray(JbList)[..., 0], axis=-1)
        potential += np.sum(nF * np.asarray(JfList)[..., 0], axis=-1)
        potential = potential * temperature**4 / (2 * np.pi * np.pi)

        # checking for imaginary parts
        if np.any(massSqB < 0) or np.any(massSqF < 0):
            if self.imaginaryOption == EImaginaryOption.PRINCIPAL_PART:
                potential = potential.real
            elif self.imaginaryOption == EImaginaryOption.ABS_RESULT:
                potential = abs(potential)
            elif self.imaginaryOption == EImaginaryOption.ERROR:
                msqBMin = np.min(massSqB)
                msqFMin = np.min(massSqF)
                raise ValueError(
                    f"Im(VT)={potential.imag}, Re(VT)={potential.real}, min(msqB)={msqBMin}, min(msqF)={msqFMin}. "
                    "Choose imaginaryOption != EImaginaryOption.ERROR "
                    "when initialising EffectivePotentialNoResum."
                )
        else:
            # no imaginary parts arise if masses are all nonnegative
            potential = potential.real

        return potential