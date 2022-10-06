# This script contains a function for subsetting a file, potentially at intermediate positions.
# This is especially helpful for subsetting fastq files which tend to be lower quality at the
# beginning. There is also a helper function for subsetting fastq files specifically.
import os, gzip
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog

def getFileSubset(filePath: str, startPos = 0, endPos = 1, fileSuffix = "_test_subset", outputDir = None):
    """
    This function subsets a given file by writing the lines from the start position (0-based) to the
    end position (1-based). The subsetted file is renamed based on the fileSuffix parameter and
    written to a given directory (The same directory as the input file by default).
    If the file is gzipped, this state is maintained in the subset.
    Returns the path to the new subset file.
    """

    if not fileSuffix: raise ValueError("Empty file suffix will rewrite original file. Aborting.")
    if endPos <= startPos: raise ValueError("End position should exceed start position.")

    # Is the file gzipped?
    gzipped = filePath.endswith(".gz")

    # Derive the output file path from input parameters.
    if outputDir is None: outputDir = os.path.dirname(filePath)

    if gzipped:
        splitFilePath = os.path.basename(filePath).rsplit('.',2)
        outputFileBaseName = '.'.join([splitFilePath[0] + fileSuffix]+splitFilePath[1:])
        openFunction = gzip.open
    else:
        splitFilePath = os.path.basename(filePath).rsplit('.',1)
        outputFileBaseName = splitFilePath[0] + fileSuffix + '.' + splitFilePath[1]
        openFunction = open

    outputFilePath = os.path.join(outputDir, outputFileBaseName)

    # Open the files 
    with openFunction(filePath, "rt") as inputFile:
        with openFunction(outputFilePath, 'wt') as outputFile:

            # Skip lines as necessary. (Also make sure we don't reach EOF here.)
            for _ in range(startPos):
                if not inputFile.readline(): raise ValueError("Start pos is greater than the number of lines in the file.")

            # Write the relevant lines to the output file.
            for _ in range(endPos-startPos): outputFile.write(inputFile.readline())

    return outputFilePath


def getFastqSubset(filePath: str, reads = 10000, outputDir = None):
    """
    A helper function which leverages getFileSubset to subset fastq files.
    Skips the first 100,000 reads, where quality is lower, and writes the
    next 10,000 (by default). Returns the output file path.
    """
    return getFileSubset(filePath, 10**5*4, 10**5*4+reads*4, outputDir = outputDir)


def main():
    with TkinterDialog() as dialog:
        dialog.createMultipleFileSelector("Files to subset: ", 0, None)
        dialog.createTextField("Start Position (0-based)", 1, 0, defaultText = str(0))
        dialog.createTextField("End Position (1-based)", 2, 0, defaultText = str(10**5*4+10**4*4))

    for filePath in dialog.selections.getFilePathGroups()[0]:
        getFileSubset(filePath, int(dialog.selections.getTextEntries()[0]), int(dialog.selections.getTextEntries()[1]))


if __name__ == "__main__": main()