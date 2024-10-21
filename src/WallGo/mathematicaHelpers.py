import pathlib
import subprocess
import logging

# Put common Wolfram Mathematica and WallGoMatrix related functions here.
# Common physics/math functions should go into helpers.py

def generateMatrixElementsViaSubprocess(
    inFilePath: pathlib.Path, outFilePath: pathlib.Path
) -> None:
    """
    Generates matrix elements by executing a Mathematica script via a subprocess.

    This function takes the input and output file paths, converts them to
    string representations, and constructs a command to run a Mathematica
    script using `wolframscript`.
    The command is executed using the `subprocess.run` method, and
    the output is printed to the console.
    If the command fails, an error message is printed.

    This requires a licensed installation of WolframEngine.

    Args:
        inFilePath (pathlib.Path):
            The path to the input file containing the Mathematica script.
        outFilePath (pathlib.Path):
            The path to the output file where the results will be saved.

    Raises:
        subprocess.CalledProcessError: If the subprocess command fails.
    """
    # Ensure filePath is string representation of the path

    inFilePathStr = str(inFilePath)
    outFilePathStr = str(outFilePath)

    banner = f"""\n
================================================
    WallGoMatrix recomputing Matrix Elements:
    Input file  : {inFilePathStr}
    Output path : {outFilePathStr}
================================================
"""
    print(banner)

    command = ["wolframscript", "-script", inFilePathStr, outFilePathStr]

    try:
        # run wolframscript
        result = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(result.stdout.decode("utf-8"))  # print the output

    except subprocess.CalledProcessError as e:
        # Handle errors in case the command fails
        logging.error(
            """
            Fatal: Error when generating matrix elements from Mathematica via WallGoMatrix.
            Ensure a licensed installation of WolframEngine."""
        )
        logging.error(e.stderr.decode("utf-8"))
