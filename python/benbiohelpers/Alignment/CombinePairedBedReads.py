# Takes a bed file of paired-end reads and combines reads that aligned concordantly.
import os, subprocess
from typing import List
from benbiohelpers.CustomErrors import UnsortedInputError
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.InputParsing.CheckForNumber import checkForNumber


def combinePairedBedReads(pairedBedReadsFilePaths: List[str], maxConcordantDistance = 500, checkSorting = True):
    """
    Takes a list of bed files containing aligned reads and combines reads which align concordantly, as decided by the maxConcordantDistance parameter.
    Each bed file is assumed to contain information from both reads. (i.e., reads should not be split across multiple bed files.)
    """

    pairedCombinedBedReadsFilePaths = list()

    for pairedBedReadsFilePath in pairedBedReadsFilePaths:

        print(f"Working in {os.path.basename(pairedBedReadsFilePath)}...")

        # Ensure that reads are sorted on their ID so that pairs can be found.
        if checkSorting:
            try:
                subprocess.check_output(("sort","-k4,4", "-s", "-c", pairedBedReadsFilePath))
            except subprocess.CalledProcessError:
                raise UnsortedInputError(pairedBedReadsFilePath, "Expected sorting based on readID.")
            
        pairedCombinedBedReadsFilePath = pairedBedReadsFilePath.rsplit(".bed",1)[0] + "_combined_reads.bed"
        pairedCombinedBedReadsFilePaths.append(pairedCombinedBedReadsFilePath)

        with open(pairedBedReadsFilePath, 'r') as pairedBedReadsFile, open(pairedCombinedBedReadsFilePath, 'w') as pairedCombinedBedReadsFile:

            lastRead = pairedBedReadsFile.readline().split()

            for line in pairedBedReadsFile:

                thisRead = line.split()

                # Check if we have paired reads.
                if thisRead[3][:-1] == lastRead[3][:-1]:

                    assert lastRead[3][-1] == "1"

                    # First, check if the paired reads aligned to the same chromosome.
                    # If they didn't, they can't be combined and need to be written separately.
                    if thisRead[0] != lastRead[0]:

                        pairedCombinedBedReadsFile.write('\t'.join(lastRead) + '\n' + '\t'.join(thisRead) + '\n')

                    else:

                        # Determine the longest possible region contained by the two reads.
                        # Notably, determining the combined region this way is permissive of alignments which overlap, contain one another, or dovetail.
                        if int(thisRead[1]) < int(lastRead[1]): combinedStart = thisRead[1]
                        else: combinedStart = lastRead[1]
                        if int(thisRead[2]) > int(lastRead[2]): combinedEnd = thisRead[2]
                        else: combinedEnd = lastRead[2]
                        
                        # If the combined region meets the maxConcordantDistance threshold, write the combined region.
                        # Otherwise, write each read separately.
                        if int(combinedEnd)-int(combinedStart) <= maxConcordantDistance:
                            pairedCombinedBedReadsFile.write('\t'.join((lastRead[0],combinedStart,combinedEnd, lastRead[3][:-1]+'*',
                                                                        lastRead[4], lastRead[5])) + '\n')
                        else:
                            pairedCombinedBedReadsFile.write('\t'.join(lastRead) + '\n' + '\t'.join(thisRead) + '\n')

                    # Regardless of how the pair was handled, both reads were consumed, so a new "lastRead" needs to be read in.
                    lastRead = pairedBedReadsFile.readline().split()

                # Unpaired reads are simply written as they are.
                else:

                    pairedCombinedBedReadsFile.write('\t'.join(lastRead) + '\n')
                    lastRead = thisRead

            # Make sure to include the last read! (If it wasn't already consumed as part of a pair)
            if lastRead: pairedCombinedBedReadsFile.write('\t'.join(lastRead) + '\n')


def main():

    with TkinterDialog(workingDirectory = os.getenv("HOME"), title = "Combine Paired Bed Reads") as dialog:
        dialog.createMultipleFileSelector("Aligned Reads:", 0, ".bed", ("bed Files", ".bed"))
        dialog.createTextField("Max Concordant Distance:", 1, 0, defaultText = "500")
        dialog.createCheckbox("Check sorting", 2, 0)

    combinePairedBedReads(dialog.selections.getFilePathGroups()[0], checkForNumber(dialog.selections.getTextEntries()[0]),
                          dialog.selections.getToggleStates()[0])


if __name__ == "__main__": main()