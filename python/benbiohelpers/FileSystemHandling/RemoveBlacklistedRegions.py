# This script takes a removes blacklisted regions from files of genomic features, like nucleosomes.
# I decided not to use the usual CountThisInThat paradigm because it actually treats encompassed features
# that span regions as the midpoint of that region. Thus, it wouldn't detect overlaps properly for 
# features that span regions of different sizes (e.g., genes).

import os, subprocess
from typing import List
from benbiohelpers.InputParsing.CheckForNumber import checkForNonNegativeInteger
from benbiohelpers.CustomErrors import UnsortedInputError
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog


class GenomicRegion:
    """
    A genomic region defined by its chromosome, start position, and end position (both 1-based).
    Used to define blacklisted regions and features to potentially blacklist.
    """

    def __init__(self, bedLine: str, expansionRadius = 0):
        self.bedLine = bedLine
        splitLine = bedLine.strip().split('\t')
        self.chromosome = splitLine[0]
        self.startPos = int(splitLine[1]) - expansionRadius + 1 # Make this 1-based.
        self.endPos = int(splitLine[2]) + expansionRadius


class BlacklistFilterer:
    """
    The class which removes blacklisted regions from a given set of genomic regions.
    """

    def __init__(self, unfilteredFilePath: str, blacklistedRegionsFilePath: str, filteredFilePath: str,
                 filteringExpansionRadius = 0, checkSorting = True, verbose = True):
        
        self.verbose = verbose # Have to initialize this guy before checking for sorting.

        # Check sorting, if requested.
        if checkSorting: self.checkSorting(blacklistedRegionsFilePath, unfilteredFilePath)

        # Open files for reading and writing.
        self.unfilteredFile = open(unfilteredFilePath, 'r')
        self.blacklistedRegionsFile = open(blacklistedRegionsFilePath, 'r')
        self.filteredFile = open(filteredFilePath, 'w')

        # Initialize variables.
        self.filteringExpansionRadius = filteringExpansionRadius
        self.currentBlacklistedRegion = None
        self.unconfirmedFeatures: List[GenomicRegion] = list()
        self.currentChromosome = None
        self.getNextBlacklistedRegion()
        self.getNextFeature()

        if self.currentBlacklistedRegion == None: raise ValueError("Empty blacklist file given.")


    def checkSorting(self, blacklistedRegionsFilePath, unfilteredFilePath):
        """
        Ensures that the two given files are properly sorted.
        Files should be sorted by the first column alphabetically followed by the next two columns numerically.
        """
        if self.verbose: print("Checking input files for proper sorting...")

        if self.verbose: print("Checking blacklist file for proper sorting...")
        try:
            subprocess.check_output(("sort","-k1,1","-k2,2n", "-k3,3n", "-s", "-c", blacklistedRegionsFilePath))
        except subprocess.CalledProcessError:
            raise UnsortedInputError(blacklistedRegionsFilePath,
                                     "Expected sorting based on chromosome name, alphabetically, "
                                     "followed by start and end position.")

        if self.verbose: print("Checking file of features to filter for proper sorting...")
        try:
            subprocess.check_output(("sort","-k1,1","-k2,2n", "-k3,3n", "-s", "-c", unfilteredFilePath))
        except subprocess.CalledProcessError:
            raise UnsortedInputError(unfilteredFilePath,
                                     "Expected sorting based on chromosome name, alphabetically, "
                                     "followed by start and end position.")


    def doesFeatureOverlapBlacklistedRegion(self, feature: GenomicRegion, blacklistedRegion: GenomicRegion) -> bool:
        "Determines whether or not a given feature overlaps a given blacklisted region."
        return (
            feature.chromosome == blacklistedRegion.chromosome and (
                (feature.startPos >= blacklistedRegion.startPos and feature.startPos <= blacklistedRegion.endPos)
                or
                (feature.endPos >= blacklistedRegion.startPos and feature.endPos <= blacklistedRegion.endPos)
            )
        )

    def isBlacklistedRegionBeyondFeature(self, feature: GenomicRegion, blacklistedRegion: GenomicRegion) -> bool:
        """
        Determines whether or not a given blacklisted region is beyond a given feature.
        Useful for determining when a feature is guaranteed to not be blacklisted.
        """
        return (
            blacklistedRegion.chromosome > feature.chromosome
            or
            (blacklistedRegion.chromosome == feature.chromosome and blacklistedRegion.startPos > feature.endPos)
        )

    def isFeatureBeyondBlacklistedRegion(self, feature: GenomicRegion, blacklistedRegion: GenomicRegion) -> bool:
        """
        Determines whether or not a given feature is beyond a given blacklisted region.
        Useful for determining when it is appropriate to read in a new blacklisted region.
        """
        return (
            feature.chromosome > blacklistedRegion.chromosome
            or
            (feature.chromosome == blacklistedRegion.chromosome and feature.startPos > blacklistedRegion.endPos)
        )


    def getNextBlacklistedRegion(self) -> GenomicRegion:
        """
        Read in a new line from the blacklisted features file, convert it to a GenomicRegion object, and
        handle interactions between the previous blacklisted region and unconfirmed features.
        Alternatively, if the file has no more data to be read, set currentBlacklistedRegion to None.
        """
        self.previousBlacklistedRegion = self.currentBlacklistedRegion
        bedLine = self.blacklistedRegionsFile.readline()
        if bedLine:
            self.currentBlacklistedRegion = GenomicRegion(bedLine, self.filteringExpansionRadius)
            if self.verbose and self.currentBlacklistedRegion.chromosome != self.currentChromosome:
                self.currentChromosome = self.currentBlacklistedRegion.chromosome
                print(f"Blacklisting regions in {self.currentChromosome}")
        else: self.currentBlacklistedRegion = None
        self.onNewBlacklistRegion()

    def onNewBlacklistRegion(self, finalCheck = False):
        """
        Check all unconfirmed features to see if they should be blacklisted, based on the previous blacklisted region.
        Then, check to see if any of the remaining features can be confirmed by being completely behind that same region.
        If they are, they are written to the output file.
        Altlernatively, if this is the final check, anything that isn't blacklisted is good to go!
        """
        stillUnconfirmedFeatures = list()
        for feature in self.unconfirmedFeatures:
            if self.doesFeatureOverlapBlacklistedRegion(feature, self.previousBlacklistedRegion):
                pass # Effectively, remove this feature.
            elif self.isBlacklistedRegionBeyondFeature(feature, self.previousBlacklistedRegion) or finalCheck:
                self.filteredFile.write(feature.bedLine)
            else:
                stillUnconfirmedFeatures.append(feature)
        self.unconfirmedFeatures = stillUnconfirmedFeatures


    def getNextFeature(self) -> GenomicRegion:
        """
        Read in a new line from the unfiltered features file, convert it to a GenomicRegion object, and
        add it to the list of unconfirmed features.
        Alternatively, if the file has no more data to be read, set currentFeature to None.
        """
        bedLine = self.unfilteredFile.readline()
        if bedLine:
            self.currentFeature = GenomicRegion(bedLine)
            self.unconfirmedFeatures.append(self.currentFeature)
        else: self.currentFeature = None



    def filter(self):
        """
        The core loop for the class. Reads through both files incrementally, based on whether or not the feature
        is beyond the current blacklisted region, until they both have been read completely.
        """

        # Read through the files incrementally.
        while self.currentBlacklistedRegion is not None or self.currentFeature is not None:
            while (
                self.currentFeature is not None
                and (
                    self.currentBlacklistedRegion is None
                    or 
                    not self.isFeatureBeyondBlacklistedRegion(self.currentFeature, self.currentBlacklistedRegion)
                )
            ):
                self.getNextFeature()
            self.getNextBlacklistedRegion()

        # Run the final check. 
        self.onNewBlacklistRegion(finalCheck=True)


def removeBlacklistedRegions(unfilteredFilePaths: List[str], blacklistedRegionsFilePath: str,
                             filteringExpansionRadius = 0, checkSorting = True, verbose = True) -> List[str]:
    """
    This function takes a file of bed-formatted features (e.g., nucleosomes) and a file of blacklisted regions as input.
    Features which overlap the blacklisted regions are removed, producing a filtered output file.
    The filteringExpansionRadius parameter increases the start and stop positions of blacklisted regions by the given amount.
        (This is useful when filtering larger features defined by their midpoints, such as nucleosomes.)
    """

    filteredFilePaths = list()

    for unfilteredFilePath in unfilteredFilePaths:

        filteredFilePath = (unfilteredFilePath.rsplit('.',1)[0] + "_" +
                            os.path.basename(blacklistedRegionsFilePath.rsplit('.',1)[0]) + "_filtered.bed")
        filteredFilePaths.append(filteredFilePath)

        BlacklistFilterer(unfilteredFilePath, blacklistedRegionsFilePath, filteredFilePath,
                          filteringExpansionRadius, checkSorting, verbose).filter()

    return filteredFilePaths


def main():

    with TkinterDialog(workingDirectory = os.getenv("HOME"), title = "Remove Blacklisted Regions") as dialog:
        dialog.createMultipleFileSelector("Files to filter", 0, "unfiltered.bed", ("Bed files", ".bed"))
        dialog.createFileSelector("Blacklisted regions", 1, ("Bed files", ".bed"))
        dialog.createTextField("Extra blacklist radius (bp)", 2, 0, defaultText = "0")
        dialog.createCheckbox("Check for sorting", 3, 0)
        dialog.createCheckbox("Verbose", 3, 1)

    removeBlacklistedRegions(dialog.selections.getFilePathGroups()[0], dialog.selections.getIndividualFilePaths()[0],
                             checkForNonNegativeInteger(dialog.selections.getTextEntries()[0]),
                             dialog.selections.getToggleStates()[0], dialog.selections.getToggleStates()[1])


if __name__ == "__main__": main()