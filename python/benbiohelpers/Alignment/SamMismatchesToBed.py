# This script takes a sam file and locates all the mismatches (potential deamination events) in it.
# The results are written to a bed file along with a metadata file containing the total number of
# reads analyzed, and the number of mismatches found.
import os, gzip
from typing import List
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.DNA_SequenceHandling import reverseCompliment
from benbiohelpers.FileSystemHandling.DirectoryHandling import getMetadataFilePath

strandFromIsReverseComplement = {True:'-', False:'+'}
R1 = 0x40
R2 = 0x80
readEndToString = {R1:"R1", R2:"R2"}

def samMismatchesToBed(samFilePaths: List[str], omitIndels = True, outputDir = None,
                       verbose = False, processSpecificReads = [], appendReadID = False):
    
    for samFilePath in samFilePaths:

        print(f"\nWorking in {os.path.basename(samFilePath)}")

        gzipped = samFilePath.endswith(".gz")

        # Create output file paths (bed file + metadata)
        if outputDir is None: thisOutputDir = os.path.dirname(samFilePath)
        else: thisOutputDir = outputDir

        if gzipped:
            outputBedFileBasename = os.path.basename(samFilePath).rsplit('.',2)[0] + "_mismatches_by_read.bed"
            openFunction = gzip.open
        else:
            outputBedFileBasename = os.path.basename(samFilePath).rsplit('.',1)[0] + "_mismatches_by_read.bed"
            openFunction = open

        outputBedFilePath = os.path.join(thisOutputDir, outputBedFileBasename)
        metadataFilePath = getMetadataFilePath(outputBedFilePath)

        # Prepare counter variables for metadata output
        totalReads = 0
        readsWithInvalidAlignments = 0
        readsWithInvalidEnd = 0
        readsWithoutMismatches = 0
        readsWithIndels = 0
        outputReads = 0
        mismatchesCounter = 0

        # Read through the sam file line by line, looking for mismatches and recording them.
        with openFunction(samFilePath, "rt") as samFile:
            with open(outputBedFilePath, 'w') as outputBedFile:
                for line in samFile:

                    # Skip header lines.
                    if line.startswith('@'):
                        if verbose: print("Skipping header")
                        continue

                    totalReads += 1
                    splitLine = line.split()

                    # Skip lines that shouldn't be processed.
                    if splitLine[2] == '*':
                        if verbose: print("Skipping unaligned read")
                        readsWithInvalidAlignments += 1
                        continue
                    if splitLine[5] == '*':
                        if verbose: print("Skipping read without CIGAR string")
                        readsWithInvalidAlignments += 1
                        continue
                    if processSpecificReads:
                        foundValidRead = False
                        for readFlag in processSpecificReads:
                            if int(splitLine[1]) & readFlag: foundValidRead = True
                        if not foundValidRead:
                            if verbose: print("Skipping read without valid read order flag")
                            readsWithInvalidEnd += 1
                            continue
                    

                    # Find the XM and MD fields and derive information about mismatches from them.
                    # For those reads that don't contain mismatches, skip them.
                    if splitLine[13].startswith("XM"):
                        mismatchCount = int(splitLine[13].rsplit(':',1)[1])
                        assert splitLine[17].startswith("MD"), f"MD field not found at expected location:\n{line}"
                        mismatchDesignations = splitLine[17].rsplit(':',1)[1]

                    elif splitLine[14].startswith("XM"): 
                        mismatchCount = int(splitLine[14].rsplit(':',1)[1])
                        assert splitLine[18].startswith("MD"), f"MD field not found at expected location:\n{line}"
                        mismatchDesignations = splitLine[18].rsplit(':',1)[1]

                    else: raise ValueError(f"XM field not at expected position:\n{line}")

                    if mismatchCount == 0:
                        if verbose: print("Skipping read with no mismatches")
                        readsWithoutMismatches += 1
                        continue

                    # Get the cigar string and determine if the read should be skipped for the presence of indels.
                    cigarString = splitLine[5]
                    if omitIndels and ('I' in cigarString or 'D' in cigarString):
                        readsWithIndels += 1
                        if verbose: print("Skipping read with indel")
                        continue

                    # Get the sequence (and determine if it should actually be the reverse compliment).
                    readSequence = splitLine[9]
                    isReverseCompliment = bool(int(splitLine[1]) & 0b10000)

                    # Next, produce a reference-relative sequence, removing inserted bases and
                    # putting in placeholders for deleted bases.
                    referenceRelativeSequence = ''
                    readPos = 0
                    alphaPositions = [i for i,char in enumerate(cigarString) if char.isalpha()]
                    lastAlphaPosition = -1
                    for alphaPosition in alphaPositions:
                        numeric = int(cigarString[lastAlphaPosition+1:alphaPosition])
                        alpha = cigarString[alphaPosition]
                        if alpha == 'M':
                            referenceRelativeSequence += readSequence[readPos:readPos+numeric]
                            readPos += numeric
                        elif alpha == 'I':
                            readPos += numeric
                        elif alpha == 'D':
                            referenceRelativeSequence += '-'*numeric
                        else: raise ValueError(f"Unexpected cigar string character {alpha} in {cigarString}")
                        lastAlphaPosition = alphaPosition
                    if len(alphaPositions) == 0: referenceRelativeSequence = readSequence
                    refSeqLength = len(referenceRelativeSequence)

                    # Catalogue all the mismatches based on their position in the reference sequence.
                    i = 0
                    refSeqPos = 0
                    mismatches = dict()
                    while i < len(mismatchDesignations):
                        
                        # First, determine how many bases to advance on the reference sequence (matches).
                        numericString = ''
                        while mismatchDesignations[i:i+1].isnumeric():
                            numericString += mismatchDesignations[i]
                            i += 1
                        refSeqPos += int(numericString)

                        # If the next character is a '^', advance the reference position for every directly trailing alpha character.
                        if mismatchDesignations[i:i+1] == '^':
                            i += 1
                            while mismatchDesignations[i:i+1].isalpha():
                                i += 1
                                refSeqPos += 1
                        # Otherwise, directly trailing alpha characters represent mismatches!
                        else:
                            while mismatchDesignations[i:i+1].isalpha():
                                mismatchesCounter += 1
                                mismatches[refSeqPos] = mismatchDesignations[i] + '>' + referenceRelativeSequence[refSeqPos]
                                i += 1
                                refSeqPos += 1

                    # Ensure that the expected number of mismatches were found.
                    assert len(mismatches) == mismatchCount, f"Expected mismatch count of {mismatchCount} but found {len(mismatches)}:\n{line}"

                    # Write the pertinent data for this read to the bed output file.
                    # Adjust values as necessary if the read is on the '-' strand.
                    threePrimeMismatchPositions = list()
                    mismatchSequences = list()
                    for pos in mismatches:
                        if isReverseCompliment:
                            threePrimeMismatchPositions.append(str(-pos - 1))
                            mismatchSequences.append(reverseCompliment(mismatches[pos][0]) + '>' + reverseCompliment(mismatches[pos][2]))
                        else:
                            threePrimeMismatchPositions.append(str(pos - refSeqLength))
                            mismatchSequences.append(mismatches[pos])

                    if isReverseCompliment: readSequence = reverseCompliment(readSequence)

                    thisBedEntry = [splitLine[2], str(int(splitLine[3]) - 1), str(int(splitLine[3]) - 1 + refSeqLength), 
                                    ':'.join(threePrimeMismatchPositions), ':'.join(mismatchSequences),
                                    strandFromIsReverseComplement[isReverseCompliment], readSequence]

                    if appendReadID:
                        readID = splitLine[0]
                        if int(splitLine[1]) & R1 and not int(splitLine[1]) & R2: readID += ":R1"
                        elif int(splitLine[1]) & R2 and not int(splitLine[1]) & R1: readID += ":R2"
                        thisBedEntry.append(readID)

                    outputBedFile.write('\t'.join(thisBedEntry) + '\n')

                    outputReads += 1

                    if verbose:
                        print(f"Byte flag: {splitLine[1]}")
                        print(f"Read sequence: {readSequence}")
                        print(f"CIGAR string: {cigarString}")
                        print(f"Derived reference sequence: {referenceRelativeSequence}")
                        print(f"MD string: {splitLine[17]}")
                        print("Bed line:", '\t'.join((splitLine[2], str(int(splitLine[3]) - 1), str(int(splitLine[3]) - 1 + refSeqLength),
                                                      ':'.join(threePrimeMismatchPositions), ':'.join(mismatchSequences),
                                                      strandFromIsReverseComplement[isReverseCompliment])) + '\n')
                        pass


        # Write the metadata
        with open(metadataFilePath, 'w') as metadataFile:
            metadataFile.write(f"Total_Reads:\t{totalReads}\n")
            metadataFile.write(f"Reads_With_Invalid_Alignment:\t{readsWithInvalidAlignments}\n")
            if processSpecificReads:
                metadataFile.write(f"Output_Specific_Read_End:\t{':'.join(readEndToString[readEnd] for readEnd in processSpecificReads)}\n")
                metadataFile.write(f"Reads_Without_Specified_End:\t{readsWithInvalidEnd}\n")
            else:
                metadataFile.write("Output_Specific_Read_End:\tANY\n")
            metadataFile.write(f"Reads_Without_Mismatches:\t{readsWithoutMismatches}\n")
            if omitIndels:
                metadataFile.write("Omit_Reads_With_Indels:\tTrue\n")
                metadataFile.write(f"Reads_With_Indels:\t{readsWithIndels}\n")
            else:
                metadataFile.write("Omit_Reads_With_Indels:\tFalse\n")
            metadataFile.write(f"Reads_In_Output:\t{outputReads}\n")
            metadataFile.write(f"Mismatches_In_Output:\t{mismatchesCounter}\n")


def main():
    # Create the Tkinter dialog.
    with TkinterDialog(workingDirectory=os.path.join(__file__,"..",".."), title = "Sam Mismatches to Bed") as dialog:
        dialog.createMultipleFileSelector("Sam Read Files:",0,".sam.gz",("Sam Files",(".sam.gz",".sam")), 
                                        additionalFileEndings = [".sam"])
        dialog.createCheckbox("Omit reads with indels", 1, 0)
        dialog.createDropdown("Process specific reads", 2, 0, ["All reads", "Only R1", "Only R2"])
        with dialog.createDynamicSelector(3, 0) as outputDirDynSel:
                outputDirDynSel.initCheckboxController("Specify single output dir")
                outputDirDialog = outputDirDynSel.initDisplay(True, "outputDir")
                outputDirDialog.createFileSelector("Output Directory:", 0, directory = True)
        dialog.createCheckbox("Append Read ID to bed entries", 4, 0)
        dialog.createCheckbox("Verbose print statements (for debugging)", 5, 0)

    # If no input was received (i.e. the UI was terminated prematurely), then quit!
    if dialog.selections is None: quit()

    # Get the user's input from the dialog.
    selections = dialog.selections

    if outputDirDynSel.getControllerVar(): outputDir = selections.getIndividualFilePaths("outputDir")[0]
    else: outputDir = None

    processSpecificReads = list()
    if selections.getDropdownSelections()[0] == "Only R1":
        processSpecificReads.append(R1)
    elif selections.getDropdownSelections()[0] == "Only R2":
        processSpecificReads.append(R2)

    samMismatchesToBed(selections.getFilePathGroups()[0], selections.getToggleStates()[0], outputDir,
                       selections.getToggleStates()[2], processSpecificReads, selections.getToggleStates()[1])


if __name__ == "__main__": main()