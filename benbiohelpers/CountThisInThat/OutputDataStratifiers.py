# This script contains an abstract class as well as its children that represent different ways the 
# output data structure from the CounterOutputDataHandler can be stratified.
from abc import ABC, abstractmethod
from typing import List, Dict
from enum import Enum
from benbiohelpers.CountThisInThat.InputDataStructures import *


class AmbiguityHandling(Enum):
    """
    How is ambiguity handled?
    """
    tolerate = 0 # Encompassed features are recorded multiple times with the relevant value in each situation, regardless of ambiguity
    ignore = 1 # Ambiguous entries are discarded.  Non-ambiguous entries are recorded once.
    record = 2 # Ambiguous entries are recorded as such.  Non-ambiguous entries are recorded once.


class OutputDataStratifier(ABC):
    """
    This is an abstract class used to build the "layers" of the output data structure.
    Each one contains information on a level in the output data structure of the CounterOutputDataHandler,
    which are made up of one or more dictionaries.
    This class's children initialize those dictionaries, store information on how data is stored in them, and
    determine how the data should be accessed and modified as encompassed features are passed to it.
    """

    @abstractmethod
    def __init__(self, ambiguityHandling, outputDataDictionaries, outputName = "NO_NAME_GIVEN"):
        """
        Initializes the object by setting default values using the given parameters.
        """
        self.ambiguityHandling = ambiguityHandling # See related enum
        self.outputDataDictionaries: List[Dict] = outputDataDictionaries
        self.allKeys = set()
        self.outputName = outputName
        self.childDataStratifier: OutputDataStratifier = None

        if self.ambiguityHandling == AmbiguityHandling.record:
            for dictionary in self.outputDataDictionaries: dictionary[None] = 0
            self.allKeys.add(None)


    def addDictionaries(self, dictionaries: List[Dict]):
        """
        Initializes the given (empty) dictionaries using the keys already present in the current dictionaries,
        and adds them to the list of outputDataDictionaries.
        Also checks to see if there are any child data stratifiers that need to add further dictionaries.
        """
        childDictionaries = list()
        hasChildStratifier = self.childDataStratifier is not None

        for dictionary in dictionaries:

            self.outputDataDictionaries.append(dictionary)
            
            for key in self.allKeys:
                
                if hasChildStratifier:
                    dictionary[key] = dict()
                    childDictionaries.append(dictionary[key])
                else: dictionary[key] = 0

        if hasChildStratifier: self.childDataStratifier.addDictionaries(childDictionaries)


    def addKey(self, key):
        """
        Adds the key to all of the dictionaries in outputDataDictionaries.  
        Then, if this stratifier has any child stratifiers, creates new dictionaries at that key and passes them down through addDictionaries.
        """
        assert key not in self.allKeys, "Key: " + str(key) + " already exists.  Adding would overwrite current dictionaries."

        childDictionaries = list()
        hasChildStratifier = self.childDataStratifier is not None
        self.allKeys.add(key)

        for dictionary in self.outputDataDictionaries:

            if hasChildStratifier:
                dictionary[key] = dict()
                childDictionaries.append(dictionary[key])
            else: dictionary[key] = 0

        if hasChildStratifier: self.childDataStratifier.addDictionaries(childDictionaries)


    @abstractmethod
    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        """
        Update the given encompassed data as necessary to retrieve a key from it later.
        """

    def onNewEncompassingFeature(self, encompassingFeature: EncompassingData):
        """
        Actions to take (if any) when given a new encompassing feature and no encompassed feature.
        """

    def onNonCountedEncompassedFeature(self, encompassedFeature: EncompassedData):
        """
        Actions to take (if any) when given an encompassed feature that was never actually encompassed.
        """

    
    @abstractmethod
    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Retrieves the key associated with the given encompassed data for this level of stratification
        NOTE: Derivatives of this function will return None even if the ambiguity handling is ignore.
        """

    
    @abstractmethod
    def getKeysForOutput(self):
        """
        Returns all keys that are suitable for output.
        """
        if None in self.allKeys:
            return sorted(self.allKeys - {None}) + [None]
        else:
            return sorted(self.allKeys)


class RelativePosODS(OutputDataStratifier):
    """
    An output data stratifier which tracks the position of the encompassed feature relative to the encompassing feature.
    """

    def __init__(self, ambiguityHandling, outputDataDictionaries,
                 encompassingFeature: EncompassingData, centerRelativePos, extraRangeRadius, outputName):
        """
        Uses the size of the given encompassing feature to set up the given layer of the output data structure using the range of values encompassed.
        If center range is true, the "0" position in the dictionary is the middle of the range, rounded up.
        If prepForHalfBases is true, half positions are incorporated into the dictionary (but may not be incorporated into final output).
        extraRangeRadius adds 2*[value] positions to the given range. 
        """
        super().__init__(ambiguityHandling, outputDataDictionaries, outputName)

        # Set important class variables
        self.centerRelativePos = centerRelativePos
        self.relativePosIntPositions = list()
        self.relativePosHalfPositions = list()
        self.usedIntPosition = False
        self.usedHalfPosition = False

        # Calculate the output data range length
        outputDataRangeLength = encompassingFeature.endPos - encompassingFeature.startPos + extraRangeRadius*2 + 1

        # Center the range, if necessary.
        if centerRelativePos:
            halfOutputDataRangeLength = int(outputDataRangeLength / 2)
            if outputDataRangeLength % 2 == 0: outputDataRange = range(-halfOutputDataRangeLength + 1, halfOutputDataRangeLength)
            else: outputDataRange = range(-halfOutputDataRangeLength, halfOutputDataRangeLength + 1)
        else:
            outputDataRange = range(outputDataRangeLength)
        
        # Set up this stratification level of the output data structure.
        for z,dictionary in enumerate(self.outputDataDictionaries):

            if outputDataRangeLength % 2 == 0 and centerRelativePos:
                dictionary[outputDataRange.start - 0.5] = 0

            for i in outputDataRange:

                dictionary[i] = 0
                if z == 0: self.relativePosIntPositions.append(i)

                if (outputDataRangeLength % 2 == 0 and centerRelativePos) or i != outputDataRange.stop - 1:
                    dictionary[i+0.5] = 0
                    if z == 0: self.relativePosHalfPositions.append(i+0.5)

        self.allKeys.update(self.relativePosIntPositions + self.relativePosHalfPositions)

        # Convert the lists of int and half positions to sets for easier lookup.
        self.relativePosIntPositions = set(self.relativePosIntPositions)
        self.relativePosHalfPositions = set(self.relativePosHalfPositions)


    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        """
        Checks the position of the encompassed feature relative to the encompassing feature.
        """
        if self.centerRelativePos:
            relativePosition = encompassedFeature.position - encompassingFeature.center
        else:
            relativePosition = encompassedFeature.position - encompassingFeature.startPos

        if (encompassedFeature.positionRelativeToEncompassingData is not None and
            encompassedFeature.positionRelativeToEncompassingData != relativePosition):
            encompassedFeature.ambiguousRelativePos = True

        encompassedFeature.positionRelativeToEncompassingData = relativePosition


    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Gets the position of the encompassed feature relative to its encompassing feature as the key.
        """       
        if self.ambiguityHandling == AmbiguityHandling.tolerate or not encompassedFeature.ambiguousRelativePos:

            # We also need to keep track of whether or half and int positions have been used at least once.
            if not self.usedIntPosition and encompassedFeature.positionRelativeToEncompassingData in self.relativePosIntPositions:
                self.usedIntPosition = True
            if not self.usedHalfPosition and encompassedFeature.positionRelativeToEncompassingData in self.relativePosHalfPositions:
                self.usedHalfPosition = True

            return encompassedFeature.positionRelativeToEncompassingData

        else: return None

        
    def getKeysForOutput(self):
        """
        Returns the positions as keys for output, sorted numerically.
        Int and half values are only used if the relevant category has been accessed at least one.
        If neither has been accessed, int values are returned.
        """
        if self.usedHalfPosition and self.usedIntPosition:
            outputKeys = self.relativePosIntPositions | self.relativePosHalfPositions
        elif self.usedHalfPosition:
            outputKeys = self.relativePosHalfPositions
        else:
            outputKeys = self.relativePosIntPositions

        outputKeys = sorted(outputKeys)

        if self.ambiguityHandling == AmbiguityHandling.record: outputKeys.append(None)
        return outputKeys


class StrandComparisonODS(OutputDataStratifier):
    """
    Stratifies by whether or not the strands of the encompassed and encompassing features match
    """

    def __init__(self, ambiguityHandling, outputDataDictionaries, outputName):
        """
        Pretty basic setup.
        """
        super().__init__(ambiguityHandling, outputDataDictionaries, outputName)

        for dictionary in self.outputDataDictionaries:
            dictionary[True] = 0 # For strand matching
            dictionary[False] = 0 # For strand mismatching
        self.allKeys.update((True, False))
        

    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        """
        Checks the difference between strands on the current encompassed and encompassing features.
        """
        strandComparison = encompassedFeature.strand == encompassingFeature.strand
        if (encompassedFeature.matchesEncompassingDataStrand is not None and 
            encompassedFeature.matchesEncompassingDataStrand != strandComparison):
            encompassedFeature.ambiguousStrandMatching = True
        encompassedFeature.matchesEncompassingDataStrand = strandComparison


    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Returns whether or not the strand of the encompassed feature matches its encompassing feature.
        """
        if self.ambiguityHandling == AmbiguityHandling.tolerate or not encompassedFeature.ambiguousStrandMatching:
            return encompassedFeature.matchesEncompassingDataStrand
        else: return None


    def getKeysForOutput(self):
        """
        Returns True and False for strand matching and mismatching and None if recording ambiguity
        """
        if None in self.allKeys: return [True, False, None]
        else: return [True, False]


class EncompassingFeatureODS(OutputDataStratifier):
    """
    Stratifies the output data structure by the position of encompassing features.
    """
    
    def __init__(self, ambiguityHandling, outputDataDictionaries, outputName):
        """
        Nothing too special here!
        All keys (except None if recording ambiguity) cannot be pre-determined and are added as they are encountered.
        """
        super().__init__(ambiguityHandling, outputDataDictionaries, outputName=outputName)


    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        """
        Keep track of the feature encompassing the encompassed feature.
        Also, use this to count non-encompassed features and track all encompassing features, 
        even if they don't contain encompassed features.
        """
        if encompassedFeature.encompassingFeature is not encompassingFeature:
            encompassedFeature.ambiguousEncompassingFeature = True
        encompassedFeature.encompassingFeature = encompassingFeature


    def onNewEncompassingFeature(self, encompassingFeature: EncompassingData):
        """
        Create a new key based on the position ID of the new encompassing feature and add it to the set.
        """
        encompassingFeatureStr = (encompassingFeature.chromosome + ':' + str(encompassingFeature.startPos) + '-' +
                                    str(encompassingFeature.endPos) + '(' + encompassingFeature.strand + ')')

        # Check to see if we have encountered this encompassing feature before.  If not, add it as a new key.
        assert encompassingFeatureStr not in self.allKeys, (
            "2 encompassing features have the same location data: " + encompassingFeatureStr)
        self.addKey(encompassingFeatureStr)

    
    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Format the position of the encompassing feature as a string and pass it back as a key.
        """
        if self.ambiguityHandling == AmbiguityHandling.tolerate or not encompassedFeature.ambiguousEncompassingFeature:

            # Construct the string to represent the encompassing feature's position and ID
            encompassingFeature = encompassedFeature.encompassingFeature
            encompassingFeatureStr = (encompassingFeature.chromosome + ':' + str(encompassingFeature.startPos) + '-' +
                                      str(encompassingFeature.endPos) + '(' + encompassingFeature.strand + ')')

            return encompassingFeatureStr

        else: return None


    def getKeysForOutput(self):
        return super().getKeysForOutput()


class EncompassedFeatureODS(OutputDataStratifier):
    """
    Stratifies the output data structure by the position of encompassed features.
    """
    
    def __init__(self, outputDataDictionaries, outputName):
        """
        Ambiguity handling is forced to be tolerant as there can be no ambiguity as to an encompassed data's own identity.
        All keys cannot be pre-determined and are added as they are encountered.
        """
        super().__init__(AmbiguityHandling.tolerate, outputDataDictionaries, outputName=outputName)


    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        """
        There's nothing to update since the encompassed feature's position ID is an intrinsic property.
        """


    def onNonCountedEncompassedFeature(self, encompassedFeature: EncompassedData):
        """
        Create a new key based on the position ID of the non-encompassed feature and add it to the set.
        This ensures that all encompassed features are properly tracked.
        """
        encompassedFeatureStr = (encompassedFeature.chromosome + ':' + str(encompassedFeature.position) + '(' + encompassedFeature.strand + ')')

        # Check to see if we have encountered this encompassing feature before.  If not, add it as a new key.
        if encompassedFeatureStr not in self.allKeys: self.addKey(encompassedFeatureStr)

    
    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Format the position of the encompassed feature as a string and pass it back as a key.
        Also, check to see if the key has been seen before, and if not, add it.
        """
        encompassedFeatureStr = (encompassedFeature.chromosome + ':' + str(encompassedFeature.position) + '(' + encompassedFeature.strand + ')')

        # Check to see if we have encountered this encompassing feature before.  If not, add it as a new key.
        if encompassedFeatureStr not in self.allKeys: self.addKey(encompassedFeatureStr)

        return encompassedFeatureStr


    def getKeysForOutput(self):
        return super().getKeysForOutput()


class EncompassedFeatureContextODS(OutputDataStratifier):
    """
    An output data stratifier which stratifies based on the context (dinuc, trinuc, etc.) of encompassed features.
    """

    def __init__(self, outputDataDictionaries, outputName, contextSize, includeAlteredTo):
        """
        This is similar to the parent constructor with just a few tweaks.
        First, ambiguity is impossible for this stratifier, since the context is independent of the encompassing feature.
        Also, all keys to the outputDataDictionaries are determined on the fly.
        """
        super().__init__(AmbiguityHandling.tolerate, outputDataDictionaries, outputName)
        self.contextSize = contextSize
        self.includeAlteredTo = includeAlteredTo


    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        """
        Nothing to update!  The context is an intrinsic property of the encompassed feature.
        """
        return


    def getRelevantKey(self, encompassedFeature: EncompassedDataWithContext):
        """
        Retrieve the context of the desired size from the encompassed feature's context.
        If the retrieved context hasn't been seen before, add it to the dictionaries.
        """

        # Run some checks to make sure we can get the desired context from the given data.
        assert len(encompassedFeature.context) >= self.contextSize, ("Encompassed feature's context, " + encompassedFeature.context + 
                                                                     ", has insufficient length for desired size: " + str(self.contextSize))
        assert len(encompassedFeature.context) % 2 == self.contextSize % 2, ("Encompassed feature's context length, " + encompassedFeature.context + 
                                                                             ", does not have the same parity as context size.")

        # Get the context of desired size.
        contextSizeDifference = len(encompassedFeature.context) - self.contextSize
        context = encompassedFeature.context[int(contextSizeDifference/2):self.contextSize+int(contextSizeDifference/2)]

        # If requested, add information on the mutant base (or other alteration)
        if self.includeAlteredTo: context = context + ">" + encompassedFeature.alteredTo

        # Add this context to the output data dictionaries if we haven't seen it before.
        if context not in self.allKeys:
            self.addKey(context)

        return context

    
    def getKeysForOutput(self):
        """
        Return the sorted list of contexts seen throughout the encompassed features.
        """
        return super().getKeysForOutput()


class PlaceholderODS(OutputDataStratifier):
    """
    An output data stratifier which actually doesn't stratify by anything and just counts all encompassed features.
    Useful to ensure that the previous stratifier is organized within a single column instead of rows.
    """

    def __init__(self, outputDataDictionaries, outputName = "Counts"):
        super().__init__(AmbiguityHandling.tolerate, outputDataDictionaries, outputName=outputName)

        for dictionary in self.outputDataDictionaries: dictionary[None] = 0
        self.allKeys.add(None)

    
    def updateConfirmedEncompassedFeature(self, encompassedFeature: EncompassedData, encompassingFeature: EncompassingData):
        return


    def getRelevantKey(self, encompassedFeature: EncompassedData):
        return None

    
    def getKeysForOutput(self):
        return super().getKeysForOutput()