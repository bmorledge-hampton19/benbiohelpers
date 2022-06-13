# This script combines repititions within a directory using unique repitition naming strings.
# For example, upon finding a file with "rep1" in the name, it looks for one with "rep2", "rep3", etc.
# and combines them into one file with a new repitition naming string.
# Also recurses into any other directories it encounters along the way.

import gzip
import os, shutil, warnings
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog


def combineReps(parentDirectory, expectedRepititions, repititionStringBase = "rep", combinedRepititionString = "all_reps", verbose = True):

    firstRepString = f"{repititionStringBase}1"

    # Iterate through the given directory
    for item in os.listdir(parentDirectory):
        path = os.path.join(parentDirectory,item)

        # Recursively search directories
        if os.path.isdir(path): 
            if verbose: print(f"\nRecursing into directory: {item}")
            combineReps(path, expectedRepititions, repititionStringBase, combinedRepititionString, verbose)

        # Check for the repitition string, and then check for other repititions to combine.
        if firstRepString in item:

            if verbose: 
                print(f"Found item with first repitition string: {item}")
                print("Searching for other repititions...")
            repititionFilePaths = [path]

            for repNum in range(2, expectedRepititions+1):            
                nextRepititionFilePath = path.replace(firstRepString, f"{repititionStringBase}{repNum}")
                if os.path.exists(nextRepititionFilePath):
                    if verbose: print(f"\tFound repitition {repNum}.")
                    repititionFilePaths.append(nextRepititionFilePath)
                else: warnings.warn(f"Expected repitition {repNum} at {nextRepititionFilePath}, but it does not exist.")

            if verbose: print(f"\tCombining repititions...")
            # Make sure all paths are either gzipped or not gzipped (no mixing)
            assert (all(filePath.endswith(".gz") for filePath in repititionFilePaths) or
                    all(not filePath.endswith(".gz") for filePath in repititionFilePaths)), (
                        f"Non-uniform compression across repititions: {repititionFilePaths}"
                    )
            if repititionFilePaths[0].endswith(".gz"): openFunction = gzip.open
            else: openFunction = open
            combinedRepititionsFilePath = path.replace(firstRepString, combinedRepititionString)
            with openFunction(combinedRepititionsFilePath, 'w') as combinedRepititionsFile:
                for repititionFilePath in repititionFilePaths:
                    with openFunction(repititionFilePath, 'r') as repititionFile:
                        shutil.copyfileobj(repititionFile, combinedRepititionsFile)


def main():

    # Get the working directory from mutperiod if possible. Otherwise, just use this script's directory.
    try:
        from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
        workingDirectory = getDataDirectory()
    except ImportError:
        workingDirectory = os.path.dirname(__file__)

    #Create the Tkinter UI
    with TkinterDialog(workingDirectory=workingDirectory) as dialog:
        dialog.createFileSelector("Parent Directory:", 0, directory = True)
        dialog.createTextField("Expected Repititions:", 1, 0, defaultText='2')

    selections = dialog.selections
    combineReps(selections.getIndividualFilePaths()[0], int(selections.getTextEntries()[0]))


if __name__ == "__main__": main()