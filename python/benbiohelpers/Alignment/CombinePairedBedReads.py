# Takes a bed file of paired-end reads and combines reads that aligned concordantly.
import os, subprocess
from enum import Enum
from typing import List
from benbiohelpers.CustomErrors import UnsortedInputError
from benbiohelpers.FileSystemHandling.DirectoryHandling import getTempDir
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.InputParsing.CheckForNumber import checkForNumber

class CombinationMethod(Enum):

    FIVE_PRIME_END = 1
    THREE_PRIME_END = 2
    LONGEST_READ = 3


def combinePairedBedReads(pairedBedReadsFilePaths: List[str], maxConcordantDistance = 500, combinationMethod = CombinationMethod.FIVE_PRIME_END,
                          checkSorting = True, outputToTmpDir = False, verbose = True) -> List[str]:
    """
    Takes a list of bed files containing aligned reads and combines reads which align concordantly, as decided by the maxConcordantDistance parameter.
    Each bed file is assumed to contain information from both reads. (i.e., reads should not be split across multiple bed files.)
    Note that unpaired reads (those with sequencing IDs not ending in /1 or /2) can also be passed through this function and will simply be written as they are.
    """

    pairedCombinedBedReadsFilePaths = list()

    for pairedBedReadsFilePath in pairedBedReadsFilePaths:

        if verbose: print(f"Working in {os.path.basename(pairedBedReadsFilePath)}...")

        # Ensure that reads are sorted on their ID so that pairs can be found.
        if checkSorting:
            try:
                subprocess.check_output(("sort","-k4,4", "-s", "-c", pairedBedReadsFilePath))
            except subprocess.CalledProcessError:
                raise UnsortedInputError(pairedBedReadsFilePath, "Expected sorting based on readID.")
            
        pairedCombinedBedReadsFilePath = pairedBedReadsFilePath.rsplit(".bed",1)[0] + "_combined_reads.bed"
        if outputToTmpDir: pairedCombinedBedReadsFilePath = os.path.join(os.path.dirname(pairedCombinedBedReadsFilePath),
                                                                         getTempDir(pairedCombinedBedReadsFilePath),
                                                                         os.path.basename(pairedCombinedBedReadsFilePath))
        pairedCombinedBedReadsFilePaths.append(pairedCombinedBedReadsFilePath)

        with open(pairedBedReadsFilePath, 'r') as pairedBedReadsFile, open(pairedCombinedBedReadsFilePath, 'w') as pairedCombinedBedReadsFile:

            lastRead = pairedBedReadsFile.readline().split()

            for line in pairedBedReadsFile:

                thisRead = line.split()

                # Check if we have paired reads.
                if thisRead[3][:-1] == lastRead[3][:-1] and thisRead[3][-2] == "/":

                    # Make sure the reads are given in order.
                    assert lastRead[3][-1] == "1"

                    # First, check if the paired reads aligned to the same chromosome.
                    # If they didn't, they can't be combined and need to be written separately.
                    if thisRead[0] != lastRead[0]:

                        pairedCombinedBedReadsFile.write('\t'.join(lastRead) + '\n' + '\t'.join(thisRead) + '\n')

                    else:

                        # Determine how to combine the reads.

                        # Get the five prime end of each read and use them to determine the start and end of the region.
                        if combinationMethod == CombinationMethod.FIVE_PRIME_END:
                            if lastRead[5] == '+':
                                combinedStart = int(lastRead[1])
                                combinedEnd = int(thisRead[2])
                            else:
                                combinedStart = int(thisRead[1])
                                combinedEnd = int(lastRead[2])

                        # Get the three prime end of reach read and use them to determine the start and end of the region.
                        # (Not sure if this will ever be useful, tbh...)
                        elif combinationMethod == CombinationMethod.THREE_PRIME_END:
                            if lastRead[5] == '+':
                                combinedStart = int(thisRead[1])
                                combinedEnd = int(lastRead[2])
                            else:
                                combinedStart = int(lastRead[1])
                                combinedEnd = int(thisRead[2])

                        # Determine the longest possible region contained by the two reads.
                        # Notably, determining the combined region this way is permissive of alignments which overlap, contain one another, or dovetail.
                        elif combinationMethod == CombinationMethod.LONGEST_READ:
                            if int(thisRead[1]) < int(lastRead[1]): combinedStart = int(thisRead[1])
                            else: combinedStart = int(lastRead[1])
                            if int(thisRead[2]) > int(lastRead[2]): combinedEnd = int(thisRead[2])
                            else: combinedEnd = int(lastRead[2])
                        else:
                            raise ValueError("Expected instance of CombinationMethod but received " + combinationMethod)

                        # If the combined region is a valid bed region that meets the maxConcordantDistance threshold,
                        # write the combined region. Otherwise, write each read separately.
                        if combinedEnd-combinedStart <= maxConcordantDistance and combinedEnd > combinedStart:
                            pairedCombinedBedReadsFile.write('\t'.join((lastRead[0],str(combinedStart),str(combinedEnd), lastRead[3][:-1]+'*',
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

    return pairedCombinedBedReadsFilePaths


def main():

    with TkinterDialog(workingDirectory = os.getenv("HOME"), title = "Combine Paired Bed Reads") as dialog:
        dialog.createMultipleFileSelector("Aligned Reads:", 0, ".bed", ("bed Files", ".bed"))
        dialog.createTextField("Max Concordant Distance:", 1, 0, defaultText = "500")
        dialog.createDropdown("Combination Method", 2, 0, [combinationMethod.name.lower().replace('_', ' ') for combinationMethod in CombinationMethod])
        dialog.createCheckbox("Check sorting", 3, 0)

    combinePairedBedReads(dialog.selections.getFilePathGroups()[0], checkForNumber(dialog.selections.getTextEntries()[0]),
                          CombinationMethod[dialog.selections.getDropdownSelections()[0].upper().replace(' ', '_')],
                          dialog.selections.getToggleStates()[0])


if __name__ == "__main__": main()