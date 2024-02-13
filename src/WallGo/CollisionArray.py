import numpy as np
from scipy.special import eval_chebyt
import h5py # read/write hdf5 structured binary data file format
import codecs # for decoding unicode string from hdf5 file
from typing import Tuple
import copy ## for deepcopy

from .Particle import Particle
from .Polynomial import Polynomial
from .Grid import Grid

class CollisionArray:
    """
    Class used to load, transform, interpolate and hold the collision array 
    which is needed in Boltzmann. Internally the collision array is represented by a Polynomial object.
    Specifically, this describes a rank-4 tensor C[P_k(pZ_i) P_l(pPar_j)] where the p are momenta on grid.
    Index ordering is hardcoded as: ijkl.
    Right now we have one CollisionArray for each pair of off-eq particles 
    """

    """Hardcode axis types and their meaning in correct ordering. 
    Our order is ijkl with momentum indices first, polynomial indices last.
    """
    AXIS_TYPES = ("pz", "pp", "pz", "pp")
    AXIS_LABELS = ("pz", "pp", "polynomial1", "polynomial2")

    def __init__(self, grid: Grid, basisType: str, particle1: Particle, particle2: Particle):
        """
        Initializes a CollisionArray for given grid and basis. Collision data will be set to zero.

        Parameters
        ----------
        grid : Grid
            Grid object that the collision array lives on (non-owned).
        basisType: str
            Basis to use for the polynomials. Note that unlike in the Polynomial class, our basis is just a string.
            We always use "Cardinal" basis on momentum axes and basisType on polynomial axes. 
            We do NOT support different basis types for the two polynomials.
        particle1: Particle
        particle2: Particle
            The two out-of-equilibrium particles this collision array describes.

        Returns
        -------
        None.
        """

        self.grid = grid

        ## Our actual data size is N-1 in each direction
        self.size = grid.N - 1

        self.grid = grid
        self.basisType = basisType
        self.particle1 = particle1
        self.particle2 = particle2
        
        ## Setup the actual collision data. We will use "Cardinal" basis on momentum axes and default to "Chebyshev" for polynomial axes.
        bases = ("Cardinal", "Cardinal", basisType, basisType)

        ## Default to zero but correct size
        data = np.empty( (self.size, self.size, self.size, self.size))
        self.polynomialData = Polynomial(data, grid, bases, CollisionArray.AXIS_TYPES, endpoints=False)



    def __getitem__(self, key):
        return self.polynomialData.coefficients[key]
    
    def getBasisSize(self) -> int:
        return self.size
    
    def getBasisType(self) -> str:
        return self.basisType
    
    @staticmethod
    def newFromPolynomial(inputPolynomial: Polynomial, particle1: Particle, particle2: Particle) -> 'CollisionArray':
        """Creates a new CollisionArray object from polynomial data (which contains a grid reference).
        This only makes sense if the polynomial is already in correct shape.
        """

        bases = inputPolynomial.basis

        assert inputPolynomial.rank == 4
        assert bases[0] == "Cardinal" and bases[1] == "Cardinal"
        assert bases[2] == bases[3] ## polynomial axes need to be in same basis   
        
        basisType = bases[2]

        newCollision = CollisionArray(inputPolynomial.grid, basisType, particle1, particle2)
        newCollision.polynomialData = inputPolynomial
        return newCollision



    ## This will fail with assert or exception if something goes wrong. If we don't want to abort, consider denoting failure by return value instead
    @staticmethod
    def newFromFile(filename: str, grid: Grid, basisType: str, particle1: Particle, particle2: Particle, bInterpolate: bool = True) -> 'CollisionArray':
        """
        Create a new CollisionArray object from 

        Parameters
        ----------
        filename : str
            Path of the file containing the collision array.

        bInterpolate : bool = True
            Interpolate the data to match our grid size? Extrapolation is not possible.    
        
        Returns
        -------
        CollisionArray

        """
        try:
            with h5py.File(filename, "r") as file:
                metadata = file["metadata"]
                basisSizeFile = metadata.attrs["Basis Size"]
                basisTypeFile = codecs.decode(
                    metadata.attrs["Basis Type"], 'unicode_escape',
                )
                CollisionArray.__checkBasis(basisTypeFile)

                # LN: currently the dataset names are of form
                # "particle1, particle2". Here it's just "top, top" for now.
                datasetName = particle1.name + ", " + particle2.name
                collisionFileArray = np.array(file[datasetName][:])
        except FileNotFoundError:
            print("CollisionArray error: %s not found" % filename)
            raise

        # HACK. converting between conventions because collision file was computed with different index ordering
        collisionFileArray = np.transpose(
            np.flip(collisionFileArray, (2, 3)),
            (2, 3, 0, 1),
        )

        """We want to compute Polynomial object from the loaded data and put it on the input grid.
        This is straightforward if the grid size matches that of the data, if not we either abort
        or attempt interpolation to smaller N. In latter case we need a dummy grid of read size,
        create a dummy CollisionArray living on the dummy grid, and finally downscale that. 
        """

        if (basisSizeFile == grid.N):
            polynomialData = Polynomial(collisionFileArray, grid, ("Cardinal", "Cardinal", basisTypeFile, basisTypeFile),
                                        CollisionArray.AXIS_TYPES, endpoints=False)
            newCollision = CollisionArray.newFromPolynomial(polynomialData, particle1, particle2)
            
        else:   
            ## Grid sizes don't match, attempt interpolation
            if (not bInterpolate):
                raise RuntimeError("Grid size mismatch when loading collision file: ", filename, \
                                   "Consider using bInterpolate=True in CollisionArray.loadFromFile()." )
            
            dummyGrid = Grid(grid.M, basisSizeFile, grid.L_xi, grid.momentumFalloffT, grid.spacing)
            dummyPolynomial = Polynomial(collisionFileArray, dummyGrid, ("Cardinal", "Cardinal", basisTypeFile, basisTypeFile),
                                         CollisionArray.AXIS_TYPES, endpoints=False)
            
            dummyCollision = CollisionArray.newFromPolynomial(dummyPolynomial, particle1, particle2)
            newCollision = CollisionArray.interpolateCollisionArray(dummyCollision, grid)

        ## Change to the requested basis
        return newCollision.changeBasis(basisType)


    def changeBasis(self, newBasisType: str) -> 'CollisionArray':
        """Changes basis in our polynomial indices. Momentum indices always use Cardinal. 
        This modifies the object in place"""

        if (self.basisType == newBasisType): 
            return self


        CollisionArray.__checkBasis(newBasisType)

        ## NEEDS to take inverse transpose because of magic
        self.polynomialData.changeBasis( ("Cardinal", "Cardinal", newBasisType, newBasisType), inverseTranspose=True)
        self.basisType = newBasisType
        return self

        
    @staticmethod
    def interpolateCollisionArray(srcCollision: 'CollisionArray', targetGrid: Grid) -> 'CollisionArray':
        """
        Interpolate collision array to match a target grid.
        size.

        Parameters
        ----------
        collisionArray :
            Basis size of the desired collision array.

        Returns
        -------
        None.
        """

        assert targetGrid.N <= srcCollision.getBasisSize(), "CollisionArray interpolation error: target grid size must be smaller than the source grid size."
        
        ## Take deepcopy to avoid modifying the input
        source = copy.deepcopy(srcCollision)

        # Source needs to be in the Chebyshev basis for interpolation
        source.changeBasis("Chebyshev")  
        
        # Generate a grid of points to give as input to Polynomial.evaluate.
        gridPoints = np.array(np.meshgrid(targetGrid.rzValues, targetGrid.rpValues,indexing='ij')).reshape((2,(targetGrid.N-1)**2))
        
        # Evaluate the original collisions on the interpolated grid, create a new polynomial from the result and finally a new CollisionArray from the polynomial data
        interpolatedData = source.polynomialData.evaluate(gridPoints, (0,1))[:,:targetGrid.N-1,:targetGrid.N-1].reshape(4*(targetGrid.N-1,))

        interpolatedPolynomial = Polynomial(interpolatedData, targetGrid, 
                                            ("Cardinal", "Cardinal", "Chebyshev", "Chebyshev"), 
                                            ("pz","pp","pz","pp"), endpoints=False)
        
        newCollision = CollisionArray.newFromPolynomial(interpolatedPolynomial, source.particle1, source.particle2)

        ## Change back to the original basis
        newCollision.changeBasis(srcCollision.getBasisType())
        return newCollision
    

    def estimateLxi(self, v: float, T1: float, T2: float, msq1: float, msq2: float) -> Tuple[float, float]:
        """
        Estimate the decay length of the solution by computing the eigenvalues
        of the collision array.

        Parameters
        ----------
        v : float
            Wall velocity in the plasma frame.
        T1 : float
            Temperature in the symmetric phase.
        T2 : float
            Temperature in the broken phase.
        msq1 : float
            Squared mass in the symmetric phase.
        msq2 : float
            Squared mass in the broken phase.

        Returns
        -------
        Tuple(float,float)
            Approximate decay length in the symmetric and broken phases, 
            respectively.

        """
        # Compute the grid of momenta
        _, pz, pp = self.grid.getCoordinates() 
        pz = pz[:, np.newaxis]
        pp = pp[np.newaxis, :]
        E1 = np.sqrt(msq1 + pz**2 + pp**2)
        E2 = np.sqrt(msq2 + pz**2 + pp**2)
        
        gamma = 1 / np.sqrt(1 - v**2)
        PWall1 = gamma * (pz - v * E1)
        PWall2 = gamma * (pz - v * E2)
    
        # Compute the eigenvalues
        size = self.grid.N-1
        eigvals1 = np.linalg.eigvals(T1**2*((self.polynomialData.coefficients / PWall1[:,:,None,None]).reshape((size,size,size**2))).reshape((size**2,size**2)))
        eigvals2 = np.linalg.eigvals(T2**2*((self.polynomialData.coefficients / PWall2[:,:,None,None]).reshape((size,size,size**2))).reshape((size**2,size**2)))
        
        # Compute the decay length
        return np.max(-1/np.real(eigvals1)),np.max(1/np.real(eigvals2))
        
    @staticmethod
    def __checkBasis(basis: str):
        """
        Check that basis is reckognised
        """
        bases = ["Cardinal", "Chebyshev"]
        assert basis in bases, "CollisionArray error: unkown basis %s" % basis