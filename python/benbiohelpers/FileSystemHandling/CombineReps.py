# This script combines repetitions within a directory using unique repetition naming strings.
# For example, upon finding a file with "rep1" in the name, it looks for one with "rep2", "rep3", etc.
# and combines them into one file with a new repetition naming string.
# Also recurses into any other directories it encounters along the way.

import gzip
import os, shutil, warnings
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog


def combineReps(parentDirectory, expectedRepetitions, repetitionStringBase = "rep", combinedRepetitionString = "all_reps", verbose = True):

    firstRepString = f"{repetitionStringBase}1"

    # Iterate through the given directory
    for item in os.listdir(parentDirectory):
        path = os.path.join(parentDirectory,item)

        # Recursively search directories
        if os.path.isdir(path): 
            if verbose: print(f"\nRecursing into directory: {item}")
            combineReps(path, expectedRepetitions, repetitionStringBase, combinedRepetitionString, verbose)

        # Check for the repetition string, and then check for other repetitions to combine.
        if firstRepString in item:

            if verbose: 
                print(f"Found item with first repetition string: {item}")
                print("Searching for other repetitions...")
            repetitionFilePaths = [path]

            for repNum in range(2, expectedRepetitions+1):            
                nextRepetitionFilePath = path.replace(firstRepString, f"{repetitionStringBase}{repNum}")
                if os.path.exists(nextRepetitionFilePath):
                    if verbose: print(f"\tFound repetition {repNum}.")
                    repetitionFilePaths.append(nextRepetitionFilePath)
                else: warnings.warn(f"Expected repetition {repNum} at {nextRepetitionFilePath}, but it does not exist.")

            if verbose: print(f"\tCombining repetitions...")
            # Make sure all paths are either gzipped or not gzipped (no mixing)
            assert (all(filePath.endswith(".gz") for filePath in repetitionFilePaths) or
                    all(not filePath.endswith(".gz") for filePath in repetitionFilePaths)), (
                        f"Non-uniform compression across repetitions: {repetitionFilePaths}"
                    )
            if repetitionFilePaths[0].endswith(".gz"): openFunction = gzip.open
            else: openFunction = open
            combinedRepetitionsFilePath = path.replace(firstRepString, combinedRepetitionString)
            with openFunction(combinedRepetitionsFilePath, 'w') as combinedRepetitionsFile:
                for repetitionFilePath in repetitionFilePaths:
                    with openFunction(repetitionFilePath, 'r') as repetitionFile:
                        shutil.copyfileobj(repetitionFile, combinedRepetitionsFile)


def main():

    # Get the working directory from mutperiod if possible. Otherwise, just use this script's directory.
    try:
        from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
        workingDirectory = getDataDirectory()
    except ImportError:
        workingDirectory = workingDirectory = os.getenv("HOME"), 

    #Create the Tkinter UI
    with TkinterDialog(workingDirectory=workingDirectory, title = "Combine Reps") as dialog:
        dialog.createFileSelector("Parent Directory:", 0, directory = True)
        dialog.createTextField("Expected Repetitions:", 1, 0, defaultText='2')
        dialog.createTextField("Repetition String Base:", 2, 0, defaultText = "rep")
        dialog.createTextField("Combined Repetition String:", 3, 0, defaultText = "all_reps")

    selections = dialog.selections
    combineReps(selections.getIndividualFilePaths()[0], int(selections.getTextEntries()[0]),
                selections.getTextEntries()[1], selections.getTextEntries()[2])


if __name__ == "__main__": main()