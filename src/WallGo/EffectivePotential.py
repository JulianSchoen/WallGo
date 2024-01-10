import numpy as np
import numpy.typing as npt
from typing import Tuple
from abc import ABC, abstractmethod ## Abstract Base Class
import cmath # complex numbers
import scipy.optimize
import scipy.interpolate

from .helpers import derivative

from .Fields import Fields


class EffectivePotential(ABC):
    """Base class for the effective potential Veff. WallGo uses this to identify phases and their temperature dependence, 
    and computing free energies (pressures) in the two phases.
    
    Hydrodynamical routines in WallGo need the full pressure in the plasma, which in principle is p = -Veff(phi) if phi is a local minimum.
    However for phase transitions it is common to neglect field-independent parts of Veff, for example one may choose normalization so that Veff(0) = 0.
    Meanwhile for hydrodynamics we require knowledge of all temperature-dependent parts.
    This class does not enforce any particular normalization of the potential, however you are REQUIRED to provide a definition of constantTerms()
    that should add T-dependent but field-indepent terms to the potential so that the full T-dependency of free energies can be computed. 

    The final technicality you should be aware of is the variable fieldLowerBound, which is used as a cutoff for avoiding spurious behavior at phi = 0.
    You may need to adjust this to suit your needs, especially if using a complicated 2-loop potential. 
    """

    """
    Internal logic related to the pressure: 
        1. evaluate() computes Veff(phi) in some normalization (can be anything)
        2. constantTerms() computes additional T-dependent but field-independent terms that were neglected in evaluate(), eg. light fermion contributions to ideal gas pressure.
        3. In Thermodynamics we compute the pressure from -p = Veff.evaluate(phi, T) + constantTerms(T)
    """

    ## How many background fields. This is explicitly required so that we can have better control over array shapes 
    fieldCount: int

    ## Lower bound for field values, used in normalize(). Using a small but nonzero value to avoid spurious divergences from eg. logarithms
    fieldLowerBound: float = 1e-8

    ## In practice we'll get the model params from a GenericModel subclass 
    def __init__(self, modelParameters: dict[str, float], fieldCount: int):
        self.modelParameters = modelParameters
        self.fieldCount = fieldCount

        ## Used for derivatives. TODO read from config file probably
        self.dT = 1e-3
        self.dPhi = 1e-3 ## field difference


    @abstractmethod
    def evaluate(self, fields: Fields, temperature: npt.ArrayLike) -> npt.ArrayLike:
        """Implement the actual computation of Veff(phi) here. The return value should be (the UV-finite part of) Veff 
        at the input field configuration and temperature.  Normalization of the potential does not matter: You may eg. choose Veff(0) = 0.
        """
        raise NotImplementedError("You are required to give an expression for the effective potential.")
    

    def constantTerms(self, temperature: npt.ArrayLike) -> npt.ArrayLike:
        """Computes additional terms to the effective potential that are required to be field-independent, hence ``constant``.
        These are still allowed to depend on the temperature. The purpose of this function is that the combination
            `V_{full} = evaluate(fields, T) + constantTerms(T)` 
        gives the full free-energy density corresponding to the input field configuration and temperature.

        While many phase-transition quantities depend only on the field-dependent part, the ``constant`` part is
        required for hydrodynamical computations (eg. for the sound speed in LTE approximation).

        For example, in the high-T expansion at leading order this should add ideal gas contributions to (minus the) pressure
        from light particles that are often not integrated over in the field-dependent evaluation function. 
        T-independent constant terms need not be included.

        See also the documentation of the EffectivePotential class.
        
        Parameters
        ----------
        temperature : ArrayLike 

        Returns
        -------
        npt.ArrayLike 
        """

        raise NotImplementedError()


    #### Non-abstract stuff from here on

    def findLocalMinimum(self, initialGuess: Fields, temperature: npt.ArrayLike) -> Tuple[Fields, npt.ArrayLike]:
        """
        Finds a local minimum starting from a given initial configuration of background fields.
        Feel free to override this if your model requires more delicate minimization.

        Returns
        -------
        minimum, functionValue : tuple. 
        minimum: list[float] is the location x of the minimum in field space.
        functionValue: float is Veff(x) evaluated at the minimum .
        If the input temperature is a numpy array, the returned values will be arrays of same length. 
        """

        # I think we'll need to manually vectorize this in case we got many field/temperature points
        T = np.atleast_1d(temperature)

        numPoints = max(T.shape[0], initialGuess.NumPoints())

        ## Reshape for broadcasting
        guesses = initialGuess.Resize(numPoints, initialGuess.NumFields())
        T = np.resize(T, (numPoints))

        resValue = np.empty_like(T)
        resLocation = np.empty_like(guesses)

        for i in range(0, numPoints):

            """Numerically minimize the potential wrt. fields. 
            We can pass a fields array to scipy routines normally, but scipy seems to forcibly convert back to standard ndarray
            causing issues in the Veff evaluate function if it uses extended functionality from the Fields class. 
            So we need a wrapper that casts back to Fields type. It also needs to fix the temperature, and we only minimize the real part
            """

            def evaluateWrapper(fieldArray: np.ndarray):
                fields = Fields.CastFromNumpy(fieldArray)
                return self.evaluate(fields, T[i]).real

            guess = guesses.GetFieldPoint(i)

            res = scipy.optimize.minimize(evaluateWrapper, guess)

            resLocation[i] = res.x
            resValue[i] = res.fun

        ## Need to cast the field location
        return Fields.CastFromNumpy(resLocation), resValue
    

    ## Find Tc for two minima, search only range [TMin, TMax].
    ## Feel free to override this if your potential needs a more sophisticated minimization algorithm.
    def findCriticalTemperature(self, minimum1: Fields, minimum2: Fields, TMin: float, TMax: float) -> float:

        if (TMax < TMin):
            raise ValueError("findCriticalTemperature needs TMin < TMax")
    

        ## @todo Should probably do something more sophisticated so that we can update initial guesses for the minima during T-loop

        def freeEnergyDifference(inputT):
            _, f1 = self.findLocalMinimum(minimum1, inputT)
            _, f2 = self.findLocalMinimum(minimum2, inputT)
            return f2.real - f1.real
        

        ## start from TMin and increase temperature in small steps until the free energy difference changes sign

        T = TMin
        dT = 0.5 # If this is too large the high-T phase may disappear before we see the free-energy sign change. TODO better solution
        signAtStart = np.sign(freeEnergyDifference(T))
        bConverged = False

        while (T < TMax):
            T += dT
            if (np.sign(freeEnergyDifference(T)) != signAtStart):
                bConverged = True
                break

        if (not bConverged):
            raise RuntimeWarning("Could not find critical temperature")
            return None


        # Improve Tc estimate by solving DeltaF = 0 in narrow range near the above T 

        # NB: bracket will break if the function has same sign on both ends. The rough loop above should prevent this.
        rootResults = scipy.optimize.root_scalar(freeEnergyDifference, bracket=(T-dT, T), rtol=1e-6, xtol=1e-6)

        return rootResults.root


    def evaluateWithConstantPart(self, fields: Fields, temperature: npt.ArrayLike) -> complex:
        """Computed Veff.evaluate(phi, T) + constantTerms(T), ie. full free-energy density.
        """
        return self.evaluate(fields, temperature) + self.constantTerms(temperature)


    def derivT(self, fields: Fields, temperature: npt.ArrayLike):
        """Calculate derivative of (real part of) the effective potential with respect to temperature.
        """
        der = derivative(
            lambda T: self.evaluate(fields, T).real,
            temperature,
            dx = self.dT,
            n = 1,
            order = 4
        )
        return der


