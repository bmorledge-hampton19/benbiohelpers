import os
from typing import List

# Returns just the name of the first directory above a given path. (e.g. test/file/path.txt would return "file")
def getIsolatedParentDir(filePath: str):

    filePath = os.path.abspath(filePath)

    assert os.path.sep in filePath, "Given path \"" + filePath + "\" has no parent directory.  Are you sure you passed a file path?"

    if os.path.isdir(filePath): return filePath.rsplit(os.path.sep,1)[-1]
    else: return filePath.rsplit(os.path.sep,2)[-2]


# Checks to see if the given directories exist and creates them if they do not.
# Raises an error if an existing file is passed instead
def checkDirs(*directoryPaths):
    for directoryPath in directoryPaths:
        if not os.path.exists(directoryPath): os.makedirs(directoryPath)
        elif os.path.isfile(directoryPath): raise NotADirectoryError(f"Existing file passed to checkDirs: {directoryPath}")


# By default, recursively searches the given directory for files with the specified ending. Returns a list of the resulting file paths.
# In addition, if the path contains list is not empty, at least one of the items in the list must be a substring of the path basename.
# If searchRecursively is set to false, only searches the given directory and returns the first match (or None if none are found).
def getFilesInDirectory(directory, validEnding, *additionalValidEndings, searchRecursively = True, basenameContains = list()):
    """Recursively searches the given directory(ies) for files of the specified type."""

    if validEnding is None: return list()

    if searchRecursively: filePaths = list()

    # Iterate through the given directory
    for item in os.listdir(directory):
        path = os.path.join(directory,item)

        # Recursively search any directories
        if os.path.isdir(path) and searchRecursively:
            filePaths += getFilesInDirectory(path,validEnding, *additionalValidEndings)

        # Check files for the valid ending(s)
        else:

            # Perform the "contains check" if necessary.
            if len(basenameContains) == 0: containsCheck = True
            else: containsCheck = any(substring in item for substring in basenameContains)

            if containsCheck and any(path.endswith(ending) for ending in (validEnding,) + additionalValidEndings): 
                if not searchRecursively: return path
                else: filePaths.append(path)

    if not searchRecursively: return None
    else: return filePaths

# Filters out any files directly with in a ".tmp" directory.
def filterTempFiles(filePaths: List[str]):
    return [filePath for filePath in filePaths if getIsolatedParentDir(filePath) != ".tmp"]

# Returns the most appropriate .tmp directory for a path, creating it if necessary.
def getTempDir(filePath: str):

    # Remove any trailing path separators.
    if filePath.endswith(os.sep): filePath = filePath[:-1]

    # Get the nearest directory.
    if not os.path.isdir(filePath): filePath = os.path.dirname(filePath)

    # Make sure the directory is a .tmp directory, altering it if necessary.
    if not filePath.endswith(".tmp"): filePath = os.path.join(filePath,".tmp")

    # Check the new path and return it.
    checkDirs(filePath)
    return filePath

def getMetadataDir(filePath: str):

    # Remove any trailing path separators.
    if filePath.endswith(os.sep): filePath = filePath[:-1]

    # Get the nearest directory.
    if not os.path.isdir(filePath): filePath = os.path.dirname(filePath)

    # Make sure the directory is a .tmp directory, altering it if necessary.
    if not filePath.endswith(".metadata"): filePath = os.path.join(filePath,".metadata")

    # Check the new path and return it.
    checkDirs(filePath)
    return filePath