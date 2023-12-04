# This script takes a given directory, a substring to search for, and a string to replace that substring with.
# Using this information, the script recursively renames files and directories with the given substring.
# This script is potentially DANGEROUS. Use with care.

import os
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog


def massRename(parentDirectory, searchString: str, replaceString: str, caseInsensitive = False, renameDirectories = False,
               verbose = False):

    # Define a generic function for renaming a path, if appropriate.
    def attemptPathRename(directory: str, basename: str):

        # Check to see if the search string is in the filename.
        # Whether or not this check is case sensitive is determined by the relevent parameter.
        if caseInsensitive: searchStringFound = searchString.lower() in basename.lower()
        else: searchStringFound = searchString in basename

        # Check for the search string, and replace it if found.
        if searchStringFound:

            # Generate a new file name by replacing the relevant strings.
            # Case sensitivity counts here too.
            if verbose: print(f"Found item with search string: {basename}")
            if caseInsensitive: newBasename = basename.lower().replace(searchString.lower(), replaceString)
            else: newBasename = basename.replace(searchString, replaceString)
            if verbose: print(f"Replacing with new name: {newBasename}")

            # Generate the old and new file paths.
            oldPath = os.path.join(directory, basename)
            newPath = os.path.join(directory, newBasename)

            try:
                os.rename(oldPath, newPath)
                # NOTE: I think there was a WSL bug before that made it difficult to rename files that only changed case.
                #       Not sure if I need to implement a fix for that again though or if it can be circumvented by
                #       ensuring this script runs in the OS's native file system.
            except PermissionError:
                print(f"WARNING: Permission denied at {oldPath}\nUnable to rename.")

    assert searchString, "Search string cannot be empty."

    # Iterate through the given directory
    for dirPath, _, fileNames in os.walk(parentDirectory, topdown=False):
        
        if verbose: print(f"\nWorking in {dirPath}")

        # Iterate through all the files in the current directory.
        for fileName in fileNames: attemptPathRename(dirPath, fileName)

        # Repeat the process for the directory, if desired.
        if renameDirectories: attemptPathRename(os.path.dirname(dirPath), os.path.basename(dirPath))


def main():

    #Create the Tkinter UI
    with TkinterDialog(workingDirectory=os.path.abspath(os.path.join(__file__,"..","..",".."))) as dialog:
        dialog.createFileSelector("Parent Directory:", 0, directory = True)
        dialog.createTextField("String to search for:", 1, 0, defaultText='')
        dialog.createTextField("String to replace with:", 2, 0, defaultText='')
        dialog.createCheckbox("Case insensitive:", 3, 0)
        dialog.createCheckbox("Rename directories:", 4, 0)
        dialog.createCheckbox("Verbose:", 5, 0)

    selections = dialog.selections
    massRename(selections.getIndividualFilePaths()[0], selections.getTextEntries()[0],
               selections.getTextEntries()[1], selections.getToggleStates()[0],
               selections.getToggleStates()[1], selections.getToggleStates()[2])

if __name__ == "__main__": main()