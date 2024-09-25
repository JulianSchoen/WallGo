import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass
import pathlib
import sys
import typing
from pathlib import Path
import copy
import inspect

import WallGo

if typing.TYPE_CHECKING:
    import WallGoCollision


@dataclass
class ExampleInputPoint:
    inputParameters: dict[str, float]
    phaseInfo: WallGo.PhaseInfo
    veffDerivativeScales: WallGo.VeffDerivativeScales
    wallSolverSettings: WallGo.WallSolverSettings


class WallGoExampleBase(ABC):
    """Base template for many WallGo examples."""

    bShouldRecalculateCollisions: bool
    """Flag used to check if new collision data should be generated inside the parameter loop.
    Concrete example models can set this in eg. updateModelParameters() based on their needs.
    Note that the '--recalculateCollisions' command line flag always takes priority.
    """

    matrixElementFile: pathlib.Path
    """Where to load matrix elements from. Used by runExample() if/when the collision model is initialized."""

    @abstractmethod
    def initWallGoModel(self) -> "WallGo.GenericModel":
        pass

    @abstractmethod
    def initCollisionModel(
        self, wallGoModel: WallGo.GenericModel
    ) -> "WallGoCollision.PhysicsModel":
        pass

    @abstractmethod
    def getBenchmarkPoints(self) -> list[ExampleInputPoint]:
        return []

    @abstractmethod
    def updateModelParameters(
        self, model: "WallGo.GenericModel", inputParameters: dict[str, float]
    ) -> None:
        """Override with whatever non-WallGo logic your example model needs to run
        when model-specific inputs are changed. Normally this refers to conversion from "physical" input
        (such as electroweak precision observables) to renormalized Lagrangian parameters,
        and/or propagating the changes to the effective potential, particle masses, collision model etc.
        """
        pass

    @property
    def exampleBaseDirectory(self) -> Path:
        """Returns directory of the example currently being ran."""
        # Could use sys.modules['__main__'].__file__ to find module containing __main__,
        # however this only works if the main module is a .py script (won't work eg. in Jupyter).
        # The following should be safer:
        return pathlib.Path(inspect.getfile(self.__class__)).resolve().parent

    def getDefaultCollisionDirectory(self, momentumGridSize: int) -> Path:
        """Path to the directory containing default collision data for the example."""
        return self.exampleBaseDirectory / Path(f"CollisionOutput_N{momentumGridSize}")

    def updateCollisionModel(
        self,
        inWallGoModel: "WallGo.GenericModel",
        inOutCollisionModel: "WallGoCollision.PhysicsModel",
    ) -> None:
        """Override to propagate changes from your WallGo model to the collision model.
        The base example calls this in runExample() if new collision data needs to be generated
        inside the parameter loop.
        """
        raise NotImplementedError(
            "Must override WallGoBaseExample.updateCollisionModel() to propagate changes from WallGo model to the collision model"
        )

    def initCommandLineArgs(self) -> argparse.ArgumentParser:
        argParser = argparse.ArgumentParser()

        argParser.add_argument(
            "--momentumGridSize",
            type=int,
            default=0,
            help="""Basis size N override for momentum grid.
            Values less than equal to 0 are ignored and we use whatever default the example has defined.""",
        )

        argParser.add_argument(
            "--recalculateMatrixElements",
            action="store_true",
            help="Forces full recalculation of matrix elements via DRalgo.",
        )

        argParser.add_argument(
            "--recalculateCollisions",
            action="store_true",
            help="""Forces full recalculation of relevant collision integrals instead of loading the provided data files for this example.
                    This is very slow and disabled by default.
                    The resulting collision data will be written to a directory labeled _UserGenerated; the default provided data will not be overwritten.
                    """,
        )

        argParser.add_argument(
            "--includeDetonations",
            action="store_true",
            help="""Also search for detonation solutions after deflagrations.""",
        )

        return argParser

    def assertCollisionModuleAvailable(self) -> None:
        """Failsafe, in general you should not worry about the collision module being unavailable as long as it has been properly installed (eg. with pip)"""

        assert WallGo.isCollisionModuleAvailable(), """WallGoCollision module could not be loaded, cannot proceed with collision integration.
        Please verify you have successfully installed the module ('pip install WallGoCollision')"""

    def configureCollisionIntegration(
        self, inOutCollisionTensor: "WallGoCollision.CollisionTensor"
    ) -> None:
        """Override to do model-specific configuration of collision integration.
        These settings are a feature of CollisionTensor objects, so the changes must be written directly to the input object.
        This base class version does nothing, so default options will be used unless overriden.
        """
        return

    def configureManager(self, inOutManager: "WallGo.WallGoManager") -> None:
        """Override to do model-specific configuration of the WallGo manager."""

        # Override basis size if it was passed via command line
        if self.cmdArgs.momentumGridSize > 0:
            inOutManager.config.set(
                "PolynomialGrid",
                "momentumGridSize",
                str(self.cmdArgs.momentumGridSize),
            )

    def processResultsForBenchmark(
        self, benchmarkPoint: ExampleInputPoint, results: WallGo.WallGoResults
    ) -> None:
        """Called by runExample() inside its loop over benchmark points after the wall solver finishes.
        You can override this to eg. write results to a file.
        The base class version just prints some quantities of interest to stdout."""

        header = (
            "\n=== Results with out-of-equilibrium effects included ==="
            if results.hasOutOfEquilibrium
            else "\n=== Results with equilibrium effects only ==="
        )

        print(header)
        print(f"wallVelocity:      {results.wallVelocity:.6f}")
        print(f"wallVelocityError: {results.wallVelocityError:.6f}")
        print(f"wallWidths:        {results.wallWidths}")
        print(f"wallOffsets:       {results.wallOffsets}")

    def runExample(self) -> None:
        """"""
        WallGo.initialize()

        argParser = self.initCommandLineArgs()
        # store the args so that subclasses can access them if needed
        self.cmdArgs = argParser.parse_args()

        manager = WallGo.WallGoManager()

        # Do model-dependent configuration of the manager
        self.configureManager(manager)

        model = self.initWallGoModel()
        manager.registerModel(model)

        """Collision model will be initialized only if new collision integrals are needed
        """
        collisionModel: "WallGoCollision.PhysicsModel" | None = None
        """CollisionTensor object to hold and compute the collision integrals,
        linked to the collision model that creates it. Will be initialized only if new collision integrals are needed.
        """
        collisionTensor: "WallGoCollision.CollisionTensor" | None = None

        # hacky
        momentumGridSize = manager.config.getint("PolynomialGrid", "momentumGridSize")

        benchmarkPoints = self.getBenchmarkPoints()
        if len(benchmarkPoints) < 1:
            print(
                "No benchmark points given, did you forget to override WallGoExampleBase.getBenchmarkPoints()?"
            )

        for benchmark in benchmarkPoints:

            """Update model parameters. Our examples store them internally in the model, through which they propagate to the effective potential.
            WallGo is not directly aware of model-specific parameters; it only requires EffectivePotential.evaluate() to be valid at field, temperature input,
            and similarly for particle masses. TODO update collision model
            """
            self.updateModelParameters(model, benchmark.inputParameters)

            # This needs to run before wallSpeedLTE() or solveWall(), as it does a lot of internal caching related to hydrodynamics
            """WallGo needs info about the phases at
            nucleation temperature. Use the WallGo.PhaseInfo dataclass for this purpose.
            Transition goes from phase1 to phase2.
            """
            manager.analyzeHydrodynamics(
                benchmark.phaseInfo,
                benchmark.veffDerivativeScales,
            )

            # ---- Solve wall speed in Local Thermal Equilibrium (LTE) approximation
            vwLTE = manager.wallSpeedLTE()
            print(f"LTE wall speed:    {vwLTE:.6f}")

            """Solve field EOM. For illustration, first solve it without any
            out-of-equilibrium contributions. The resulting wall speed should
            be close to the LTE result.
            """

            # Take copy of the input solver settings because we will do both off-eq = True/False cases
            wallSolverSettings = copy.deepcopy(benchmark.wallSolverSettings)
            wallSolverSettings.bIncludeOffEquilibrium = False

            print(f"\n=== Begin EOM with off-eq effects ignored ===")
            results = manager.solveWall(wallSolverSettings)
            self.processResultsForBenchmark(benchmark, results)

            """Solve field EOM with out-of-equilibrium effects included.
            This requires simulatenous solving of Boltzmann equations
            for all particle species that were defined to deviate from equilibrium.
            solveWall() automatically invokes the Boltzmann equations,
            however we must provide WallGo with collision integral data
            on the polynomial grid. Collision integrals are handled by the companion
            package WallGoCollision. Here we either recalculate them in full, or load
            pre-calculated collision data.
            """
            bNeedsNewCollisions = (
                self.cmdArgs.recalculateCollisions or self.bShouldRecalculateCollisions
            )

            # Specify where to load collision files from. The manager will load them when needed by the internal Boltzmann solver.
            # Can use existing collision data? => use data packaged with the example. Needs new data? => set new directory and run collision integrator there
            if not bNeedsNewCollisions:
                manager.setPathToCollisionData(
                    self.getDefaultCollisionDirectory(momentumGridSize)
                )

            else:
                newCollisionDir = (
                    self.exampleBaseDirectory
                    / f"CollisionOutput_N{momentumGridSize}_UserGenerated"
                )
                manager.setPathToCollisionData(newCollisionDir)

                ## Initialize collision model if not already done during an earlier benchmark point
                if collisionModel is None or collisionTensor is None:
                    collisionModel = self.initCollisionModel(model)

                    """Load matrix elements into the collision model.
                    If the load or parsing fails we abort here.
                    Subclasses should set matrixElementFile to a valid file path.
                    """
                    bShouldPrintMatrixElements = True
                    if not collisionModel.readMatrixElements(
                        str(self.matrixElementFile), bShouldPrintMatrixElements
                    ):
                        print("FATAL: Failed to load matrix elements")
                        exit()

                    collisionTensor = collisionModel.createCollisionTensor(
                        momentumGridSize
                    )

                    # Setup collision integration settings. Concrete example models can override this to do model-dependent setup
                    self.configureCollisionIntegration(collisionTensor)

                else:
                    # collisionModel exists already, update its parameters.
                    # Note that these changes propagate to all collisionTensor objects that have been created from the collision model
                    self.updateCollisionModel(model, collisionModel)

                """Run the collision integrator. This is a very long running function: For M out-of-equilibrium particle species and momentum grid size N,
                there are order M^2 x (N-1)^4 integrals to be computed. In your own runs you may want to handle this part in a separate script and offload it eg. to a cluster,
                especially if using N >> 11.
                """
                print(
                    "Entering collision integral computation, this may take long",
                    flush=True,
                )
                collisionResults: WallGoCollision.CollisionTensorResult = (
                    collisionTensor.computeIntegralsAll()
                )

                """Export the collision integration results to .hdf5. "individual" means that each off-eq particle pair gets its own file.
                This format is currently required for the main WallGo routines to understand the data. 
                """
                collisionResults.writeToIndividualHDF5(
                    str(manager.getCurrentCollisionDirectory())
                )

                self.bShouldRecalculateCollisions = False
                ## TODO we could convert the CollisionTensorResult object from above to CollisionArray directly instead of forcing write hdf5 -> read hdf5

            wallSolverSettings.bIncludeOffEquilibrium = True
            print(f"\n=== Begin EOM with off-eq effects included ===")

            try:
                results = manager.solveWall(wallSolverSettings)
                self.processResultsForBenchmark(benchmark, results)

            except Exception as e:
                print(f"Unhandled exception from wall solver: {e}")
                if isinstance(e, WallGo.CollisionLoadError):
                    print(
                        """\nLoad of collision integrals failed!
                        WallGo example models come with pre-generated collision files,
                        so load failure here probably means you've either moved files around
                        or changed to incompatible grid size.
                        If you were trying to generate your own collision data, make sure to
                        include the --recalculateCollisions command line flag when running the example.
                        """
                    )

            if self.cmdArgs.includeDetonations:
                print("\n=== Search for detonation solution ===")
                results = manager.solveWallDetonation(wallSolverSettings)
                print(f"\n=== Detonation results, {len(results)} solutions found ===")
                for res in results:
                    print(f"wallVelocity:      {res.wallVelocity}")
