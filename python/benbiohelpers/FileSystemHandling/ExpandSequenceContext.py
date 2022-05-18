# This script takes a bed file of genome positions and appends/substitutes a nucleotide sequence with additional context.
# E.g. 3 nucleotides added to each side. The original bed positions remain unchanged.
import os
from typing import List
from mutperiodpy.helper_scripts.UsefulFileSystemFunctions import getDataDirectory
from benbiohelpers.FileSystemHandling.BedToFasta import bedToFasta
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs
from benbiohelpers.FileSystemHandling.FastaFileIterator import FastaFileIterator
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.CustomErrors import UserInputError


def expandSequenceContext(inputBedFilePaths: List[str], genomeFilePath, expansionNum, writeColumn = None, 
                          outputFilePathSuffix = "_expanded", customOutputDirectory = None):
    """
    This function does all the legwork! 
    expansionNum represents the number of bases to expand by on each side.
    writeColumn tells which column to overwrite in the original file with the new sequence (or None to just append).
    """

    expandedFilePaths = list()
    for inputBedFilePath in inputBedFilePaths:

        print(f"\nWorking in {os.path.basename(inputBedFilePath)}")

        # Generate file paths for the analysis.
        workingDirectory = os.path.dirname(inputBedFilePath)
        intermediateFilesDir = os.path.join(workingDirectory, "intermediate_files")
        checkDirs(intermediateFilesDir)

        inputBedFileBasename = os.path.basename(inputBedFilePath).rsplit('.', 1)[0]
        intermediateExpansionFilePath = os.path.join(intermediateFilesDir, inputBedFileBasename + "_intermediate_expansion.bed")
        intermediateFastaFilePath = intermediateExpansionFilePath.rsplit('.',1)[0] + ".fa"

        if customOutputDirectory is None: outputDirectory = workingDirectory
        else: outputDirectory = customOutputDirectory
        expandedOutputFilePath = os.path.join(outputDirectory, inputBedFileBasename + outputFilePathSuffix + ".bed")
        expandedFilePaths.append(expandedOutputFilePath)

        # Create the intermediate bed file with expanded positions.
        with open(intermediateExpansionFilePath,'w') as intermediateExpansionFile:
            with open(inputBedFilePath, 'r') as inputBedFile:

                print("Writing expanded indicies to intermediate bed file...")
                for line in inputBedFile:

                    # Get a list of all the arguments for a single entry in the bed file.
                    choppedUpLine = line.strip().split('\t') 

                    # Get the relevant values
                    chromosome = choppedUpLine[0]
                    startPos = str(int(choppedUpLine[1])-expansionNum)
                    endPos = str(int(choppedUpLine[2])+expansionNum)
                    strand = choppedUpLine[5]

                    # Write the results to the intermediate expansion file as long as it is not at the start of the chromosome.
                    if int(startPos) > -1: 
                        intermediateExpansionFile.write("\t".join((chromosome, startPos, endPos, '.', '.', strand))+"\n")
                    else: print(f"Entry at chromosome {chromosome} with expanded start pos {startPos} "
                                "extends into invalid positions.  Skipping.")

        # Create the fasta file from the intermediate expansion file.
        print("Generating fasta file from expanded bed file...")
        bedToFasta(intermediateExpansionFilePath, genomeFilePath, intermediateFastaFilePath)

        # Open the un-expanded bed file and the expanded fasta reads that will be combined to create the expanded context.
        print("Using fasta file to write expanded context to new bed file...")
        with open(inputBedFilePath, 'r') as inputBedFile:
            with open(intermediateFastaFilePath, 'r') as fastaReadsFile:
                with open(expandedOutputFilePath, 'w') as expandedOutputFile:

                    # Work through the un-expanded bed file one mutation at a time.
                    for fastaEntry in FastaFileIterator(fastaReadsFile):

                        # Find the un-expanded entry corresponding to this entry.
                        while True:

                            # Read in the next line
                            nextLine = inputBedFile.readline()

                            # If we reached the end of the file without finding a match, we have a problem...
                            if not nextLine:
                                raise ValueError(f"Reached end of single base bed file without finding a match for:{fastaEntry.sequenceLocation}")

                            # Split the next line on tab characters and check for a match with the current read in the fasta file.
                            choppedUpLine = nextLine.strip().split("\t")
                            if (str(int(fastaEntry.startPos)+expansionNum) == choppedUpLine[1] and
                                str(int(fastaEntry.endPos)-expansionNum) == choppedUpLine[2] and
                                fastaEntry.chromosome == choppedUpLine[0] and fastaEntry.strand == choppedUpLine[5]): break

                        # Add/substitute the new sequence.
                        if writeColumn is None: choppedUpLine.append(fastaEntry.sequence)
                        else: choppedUpLine[writeColumn] = fastaEntry.sequence

                        # Write the result to the new expanded context file.
                        expandedOutputFile.write("\t".join(choppedUpLine)+"\n")

    return expandedFilePaths


def main():
    
    # Get information from the user on what files should be expanded and how.
    with TkinterDialog(workingDirectory = getDataDirectory()) as dialog:
        dialog.createMultipleFileSelector("Unexpanded Bed Files:", 0, ".bed", ("Bed Files",".bed"))
        dialog.createFileSelector("Genome File:", 1, ("Fasta Files",".fa"))
        dialog.createTextField("Nucleotides to expand by:", 2, 0, defaultText = "3")
        with dialog.createDynamicSelector(3, 0) as writeColDynSel:
            writeColDynSel.initDropdownController("Write Column:", options = ["Append", "Replace"])
            writeColDynSel.initDisplay("Replace", "replaceCol").createTextField("Column index to replace:", 0, 0, defaultText=4)
        dialog.createTextField("Output file path suffix:", 4, 0, defaultText = "_3bp_expanded")
        with dialog.createDynamicSelector(5, 0) as outputDirDynSel:
            outputDirDynSel.initCheckboxController("Specify single output dir")
            outputDirDialog = outputDirDynSel.initDisplay(True, "outputDir")
            outputDirDialog.createFileSelector("Output Directory:", 0, directory = True)

    selections = dialog.selections

    inputBedFilePaths = selections.getFilePathGroups()[0]
    genomeFilePath = selections.getIndividualFilePaths()[0]
    try: expansionNum = int(selections.getTextEntries()[0])
    except ValueError: raise UserInputError(f"Expansion number: {selections.getTextEntries()[0]} cannot be coerced to an integer")
    if writeColDynSel.getControllerVar() == "Append": writeColumn = None
    else:
        try: writeColumn = int(selections.getTextEntries("replaceCol")[0])
        except ValueError: raise UserInputError(f"Column index: {selections.getTextEntries()[0]} cannot be coerced to an integer")
    outputFilePathSuffix = selections.getTextEntries()[1]
    if outputDirDynSel.getControllerVar(): customOutputDir = selections.getIndividualFilePaths("outputDir")[0]
    else: customOutputDir = None

    expandSequenceContext(inputBedFilePaths, genomeFilePath, expansionNum, writeColumn, outputFilePathSuffix, customOutputDir)


if __name__ == "__main__": main()