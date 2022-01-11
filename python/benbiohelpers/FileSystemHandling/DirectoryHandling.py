import os

# Returns just the name of the first directory above a given path. (e.g. test/file/path.txt would return "file")
def getIsolatedParentDir(filePath: str):

    filePath = os.path.abspath(filePath)

    assert os.path.sep in filePath, "Given path \"" + filePath + "\" has no parent directory.  Are you sure you passed a file path?"

    if os.path.isdir(filePath): return filePath.rsplit(os.path.sep,1)[-1]
    else: return filePath.rsplit(os.path.sep,2)[-2]


# Checks to see if the given directories exist and creates them if they do not.
def checkDirs(*directoryPaths):
    for directoryPath in directoryPaths:
        if not os.path.exists(directoryPath): os.makedirs(directoryPath)


# By default, recursively searches the given directory for files with the specified ending. Returns a list of the resulting file paths.
# If searchRecursively is set to false, only searches the given directory and returns the first match (or None if none are found).
def getFilesInDirectory(directory, validEnding, *additionalValidEndings, searchRecursively = True):
    """Recursively searches the given directory(ies) for files of the specified type."""

    if searchRecursively: filePaths = list()

    # Iterate through the given directory
    for item in os.listdir(directory):
        path = os.path.join(directory,item)

        # Recursively search any directories
        if os.path.isdir(path) and searchRecursively:
            filePaths += getFilesInDirectory(path,validEnding, *additionalValidEndings)

        # Check files for the valid ending(s)
        else:
            if path.endswith(validEnding): 
                if not searchRecursively: return path
                else: filePaths.append(path)
            else:
                for additionalValidEnding in additionalValidEndings:
                    if path.endswith(additionalValidEnding): 
                        if not searchRecursively: return path
                        else: filePaths.append(path)
                        break

    if not searchRecursively: return None
    else: return filePaths