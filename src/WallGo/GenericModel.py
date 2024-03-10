import numpy as np
import numpy.typing as npt
from abc import ABC, abstractmethod ## Abstract Base Class

## WallGo imports
from .Particle import Particle
from .EffectivePotential import EffectivePotential
from .WallGoTypes import ActionParameters

class GenericModel(ABC):
    '''
    Common interface for WallGo model definitions. This is basically input parameters + particle definitions + effective potential.
    The user should implement this and the abstract methods below with their model-specific stuff. 
    '''

    ## TODO some method for checking that user has defined variables with correct names


    ## How many classical fields
    @property
    @abstractmethod
    def fieldCount(self) -> int:
        pass


    def computeThermalParameters(self, temperature: npt.ArrayLike, params: ActionParameters) -> ActionParameters:
        """Computes temperature-dependent parameters for use in the effective potential.
        By default this is a simple pass-through function, ie. just returns the input params.
        Users who need T-dependent parameters are supposed to override this with their own implementation.
        Example: If you wish to implement RG running and use temperature-dependent RG scale,
        implement the running here.
        """
        return params


    def addParticle(self, particleToAdd: Particle) -> None:
        ## Common routine for defining a new particle. Usually should not be overriden

        self.particles.append(particleToAdd)
        
        # add to out-of-eq particles too if applicable
        if (not particleToAdd.inEquilibrium):
            self.outOfEquilibriumParticles.append(particleToAdd)