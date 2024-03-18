import numpy as np
import numpy.typing as npt
import math
import scipy.integrate as scipyint
import scipy.linalg as scipylinalg

from .InterpolatableFunction import InterpolatableFunction, EExtrapolationType
from .EffectivePotential import EffectivePotential
from .Fields import FieldPoint, Fields


class FreeEnergyValueType(np.ndarray):

    def __new__(cls, arr: np.ndarray):
        obj = arr.view(cls)
        return obj

    def getVeffValue(self):
        """Returns value of the effective potential at a free-energy minimum.
        Returns a scalar if we only contain info for one temperature, otherwise returns a 1D array.
        """
        # Our last column is value of the potential at minimum.
        if (self.ndim < 2):
            values = self[-1]
        else:
            values = self[:, -1]
            if (len(values) == 1):
                values = values[0]

        return values

    def getFields(self):
        """Returns Fields array corresponding to local free energy minimum.
        """
        # Last column is Veff value, other columns are fields
        if (self.ndim < 2):
            values = self[:-1]
        else:
            values = self[:, :-1]
        return Fields.CastFromNumpy(values)


class FreeEnergy(InterpolatableFunction):
    """ Class FreeEnergy: Describes properties of a local effective potential minimum. 
    This is used to keep track of a minimum with respect to the temperature.
    By definition: free energy density of a phase == value of Veff in its local minimum.
    """

    effectivePotential: EffectivePotential
    # Approx field values where the phase lies at starting temperature
    startingTemperature: float
    startingPhaseLocationGuess: Fields

    # Lowest possible temperature so that the phase is still (meta)stable
    minPossibleTemperature: float
    # Highest possible temperature so that the phase is still (meta)stable
    maxPossibleTemperature: float

    def __init__(
        self,
        effectivePotential: EffectivePotential,
        startingTemperature: float,
        startingPhaseLocationGuess: Fields,
        initialInterpolationPointCount: int = 1000,
    ):

        adaptiveInterpolation = True
        # Set return value count. Currently the InterpolatableFunction requires this to be set manually:
        returnValueCount = startingPhaseLocationGuess.NumFields() + 1
        super().__init__(
            bUseAdaptiveInterpolation=adaptiveInterpolation,
            returnValueCount=returnValueCount,
            initialInterpolationPointCount=initialInterpolationPointCount,
        )
        self.setExtrapolationType(EExtrapolationType.ERROR, EExtrapolationType.ERROR)
        
        self.effectivePotential = effectivePotential 
        self.startingTemperature = startingTemperature
        self.startingPhaseLocationGuess = startingPhaseLocationGuess

        self.minPossibleTemperature = 0.
        self.maxPossibleTemperature = np.Inf

    def __call__(self, x: npt.ArrayLike, useInterpolatedValues=True) -> FreeEnergyValueType:
        return FreeEnergyValueType(super().__call__(x, useInterpolatedValues))

    def _functionImplementation(self, temperature: npt.ArrayLike) -> npt.ArrayLike:
        """
        Parameters
        ----------
        temperature: float or numpy array of floats.
        """

        # Minimising potential. N.B. should already be real for this.
        phaseLocation, potentialAtMinimum = self.effectivePotential.findLocalMinimum(
            self.startingPhaseLocationGuess, temperature
        )

        """TODO make the following work independently of how the Field array is organized.
        Too much hardcoded slicing right now."""

        # reshape so that potentialAtMinimum is a column vector
        potentialAtMinimum_column = potentialAtMinimum[:, np.newaxis]

        # Join the arrays so that potentialAtMinimum is the last column and the others are as in phaseLocation
        result = np.concatenate((phaseLocation, potentialAtMinimum_column), axis=1)

        # This is now a 2D array where rows are [f1, f2, ..., Veff]
        return result

    def tracePhaseOld(self, TMin: float, TMax: float, dT: float) -> None:
        """For now this will always update the interpolation table.
        """

        TMin = max(self.minPossibleTemperature, TMin)
        TMax = min(self.maxPossibleTemperature, TMax)

        numPoints = math.ceil((TMax-TMin) / dT)
        if not self.hasInterpolation():
            self.newInterpolationTable(TMin, TMax, numPoints)
        else:
            currentPoints = self.numPoints()
            self.extendInterpolationTable(TMin, TMax, math.ceil(numPoints / 2), math.ceil(currentPoints / 2))

        """We should now have interpolation table in range [TMin, TMax]. 
        If not, it suggests that our Veff minimization became invalid beyond some subrange [TMin', TMax']
        ==> Phase became unstable. 
        """
        if (self.interpolationRangeMax() < TMax):
            self.maxPossibleTemperature = self.interpolationRangeMax()

        if (self.interpolationRangeMin() > TMin):
            self.minPossibleTemperature = self.interpolationRangeMin()

    def tracePhase(
        self,
        TMin: float,
        TMax: float,
        dT: float,
        rTol: float = 1e-6,
        spinodal: bool = True,  # Stop tracing if a mass squared turns negative
        paranoid: bool = True,  # Re-solve minimum after every step
    ) -> None:
        """
        Finds field(T) for the range over which it exists. Sets problem
        up as an initial value problem and uses scipy.integrate.solve_ivp to
        solve. Stops if we get sqrt(negative) or something like that.
        """
        # make sure the initial conditions are extra accurate
        extraTol = 0.01 * rTol

        # initial values, should be nice and accurate
        T0 = self.startingTemperature
        phase0, V0 = self.effectivePotential.findLocalMinimum(
            self.startingPhaseLocationGuess, T0, tol=extraTol,
        )
        phase0 = FieldPoint(phase0[0])

        ## HACK! a hard-coded absolute tolerance
        tol_absolute = rTol * max(*abs(phase0), T0)

        def ode_function(temperature, field):
            # ode at each temp is a linear matrix equation A*x=b
            A = self.effectivePotential.deriv2Field2(field, temperature)
            b = -self.effectivePotential.deriv2FieldT(field, temperature)
            return scipylinalg.solve(A, b, assume_a="sym")

        # finding some sensible mass scales
        ddV_T0 = self.effectivePotential.deriv2Field2(phase0, T0)
        eigs_T0 = np.linalg.eigvalsh(ddV_T0)
        #mass_scale_T0 = np.mean(eigs_T0)
        #min_mass_scale = rTol * mass_scale_T0
        #mass_hierarchy_T0 = min(eigs_T0) / max(eigs_T0)
        #min_hierarchy = rTol * mass_hierarchy_T0

        # checking stable phase at initial temperature
        assert min(eigs_T0) * max(eigs_T0) > 0, \
            "tracePhase error: unstable at starting temperature"

        def spinodal_event(temperature, field):
            if not spinodal:
                return 1  # don't bother testing
            else:
                # tests for if an eigenvalue of V'' goes through zero
                d2V = self.effectivePotential.deriv2Field2(field, temperature)
                eigs = scipylinalg.eigvalsh(d2V)
                return min(eigs)

        # arrays to store results
        TList = np.full(1, T0)
        fieldList = np.full((1, phase0.NumFields()), Fields((phase0)))
        VeffList = np.full((1, 1), [V0])

        # maximum temperature range
        TMin = max(self.minPossibleTemperature, TMin)
        TMax = min(self.maxPossibleTemperature, TMax)

        # iterating over up and down integration directions
        endpoints = [TMax, TMin]
        for direction in [0, 1]:
            TEnd = endpoints[direction]
            ode = scipyint.RK45(
                ode_function,
                T0,
                phase0,
                TEnd,
                rtol=rTol,
                atol=tol_absolute,
                max_step=dT,
            )
            while ode.status == "running":
                try:
                    ode.step()
                except RuntimeWarning as err:
                    print(err.args[0] + f" at T={ode.t}")
                    break
                if paranoid:
                    phaset, VeffT = self.effectivePotential.findLocalMinimum(
                        Fields((ode.y)), ode.t, tol=rTol,
                    )
                    ode.y = phaset[0]
                if spinodal_event(ode.t, ode.y) <= 0:
                    print(f"Phase ends at T={ode.t}, vev={ode.y}")
                    break
                if not paranoid:
                    # check if extremum is still accurate
                    dVt = self.effectivePotential.derivField(Fields((ode.y)), ode.t)
                    err = np.linalg.norm(dVt) / T0 ** 3
                    if err > rTol:
                        phaset, VeffT = self.effectivePotential.findLocalMinimum(
                            Fields((ode.y)), ode.t, tol=extraTol,
                        )
                        ode.y = phaset[0]
                    else:
                        # compute Veff
                        VeffT = self.effectivePotential.evaluate(Fields((ode.y)), ode.t)
                # append results to lists
                TList = np.append(TList, [ode.t], axis=0)
                fieldList = np.append(fieldList, [ode.y], axis=0)
                VeffList = np.append(VeffList, [VeffT], axis=0)
                # check if step size is still okay to continue
                if ode.step_size < 1e-16 * T0:
                    print(f"Step size {ode.step_size} shrunk too small at T={ode.t}, vev={ode.y}")
                    break
            if direction == 0:
                # populating results array
                TFullList = TList
                fieldFullList = fieldList
                VeffFullList = VeffList
                # making new empty array for downwards integration
                TList = np.empty(0, dtype=float)
                fieldList = np.empty((0, phase0.NumFields()), dtype=float)
                VeffList = np.empty((0, 1), dtype=float)
            else:
                if len(TList) > 1:
                    # combining up and down integrations
                    TFullList = np.append(np.flip(TList, 0), TFullList, axis=0)
                    fieldFullList = np.append(np.flip(fieldList, axis=0), fieldFullList, axis=0)
                    VeffFullList = np.append(np.flip(VeffList, axis=0), VeffFullList, axis=0)
                elif len(TFullList) <= 1:
                    # Both up and down lists are too short
                    raise RuntimeError("Failed to trace phase")

        # overwriting temperature range
        ## HACK! Hard-coded 2*dT, see issue #145
        self.minPossibleTemperature = min(TFullList) + 2 * dT
        self.maxPossibleTemperature = max(TFullList) - 2 * dT
        assert self.maxPossibleTemperature > self.minPossibleTemperature, \
            f"Temperature range negative: decrease dT from {dT}"

        # Now to construct the interpolation
        result = np.concatenate((fieldFullList, VeffFullList), axis=1)
        self.newInterpolationTableFromValues(TFullList, result)
