# This script contains an abstract class as well as its children that represent different ways the 
# output data structure from the CounterOutputDataHandler can be stratified.
from abc import ABC, abstractmethod
from benbiohelpers.CountThisInThat.SupplementalInformation import SUP_INFO_KEY, SupplementalInformation, SupplementalInformationHandler
from typing import List, Dict, Tuple, Union
from enum import Enum
from benbiohelpers.CountThisInThat.InputDataStructures import *


class AmbiguityHandling(Enum):
    """
    How is ambiguity handled?
    """
    tolerate = 0 # Encompassed features are recorded multiple times with the relevant value in each situation, regardless of ambiguity
    ignore = 1 # Ambiguous entries are discarded.  Non-ambiguous entries are recorded once.
    record = 2 # Ambiguous entries are recorded as such.  Non-ambiguous entries are recorded once.


def sortPositionIDs(positionIDs: Union[List[str], List[Tuple]]):
    """
    Sorts the position IDs derived from the Encompassed Data and Encompassing Data ODS's.
    Can handle input as a list of strings or tuples, and with a single position or both a start and end position.
    However, it is assumed that all members of the list are formatted the same with respect to the above variations.
    """

    # Sorting for list of strings:
    if isinstance(positionIDs[0], str):

        # If both start and end positions are given (Represented by a '-' between positions, before the strand designation), sort on end position first
        if '-' in positionIDs[0].split('(')[0]:
            positionIDs.sort(key = lambda positionID: float(positionID.split('(')[0].split('-')[1]))

        # Next, sort on the first (potentially only) given position.
        positionIDs.sort(key = lambda positionID: float(positionID.split('(')[0].split(':')[1].split('-')[0]))

        # Finally, sort on the chromosome identifier.
        positionIDs.sort(key = lambda positionID: positionID.split(':')[0])

        return positionIDs # Do this as a formality, even though this sorts in place (I think).

    # Otherwise, assume we have some iterable.
    else:

        # If the iterable has 4 items, sort on item 3 first, which represents the end position
        if len(positionIDs[0]) == 4: positionIDs.sort(key = lambda positionID: positionID[2])

        # Next, sort by the start position and then the chromosome
        positionIDs.sort(key = lambda positionID: positionID[1])
        positionIDs.sort(key = lambda positionID: positionID[0])


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
        self.sortedKeys = None
        self.keysFormattedForOutput = None
        self.outputName = outputName
        self.childDataStratifier: OutputDataStratifier = None
        self.supplementalInfoHandlers: List[SupplementalInformationHandler] = list()

        if self.ambiguityHandling == AmbiguityHandling.record:
            for dictionary in self.outputDataDictionaries: dictionary[None] = 0
            self.allKeys.add(None)


    def addSuplementalInfo(self, supplementalInfoHandler: SupplementalInformationHandler):
        """
        Adds supplemental information to the child stratifier's dictionaries (so that the data
        is stratified by this stratifier's condition as well.)
        Also initializes supplemental information for all child dictionaries.
        """
        self.supplementalInfoHandlers.append(supplementalInfoHandler)
        for dictionary in self.childDataStratifier.outputDataDictionaries:
            if len(self.supplementalInfoHandlers) == 1: dictionary[SUP_INFO_KEY] = list()
            dictionary[SUP_INFO_KEY].append(supplementalInfoHandler.initializeSupplementalInfo())


    def initializeChildDictionaries(self, dictionary, keys):
        """
        Given a dictionary and a list of keys,
        Initialize the dictionaries and return them in a list.
        """
        newChildDictionaries = list()

        for key in keys:
            dictionary[key] = dict()
            newChildDictionaries.append(dictionary[key])

        if len(self.supplementalInfoHandlers > 0):
            for key in keys:
                dictionary[key][SUP_INFO_KEY] = list()
                for supplementalInfoHandler in self.supplementalInfoHandlers:
                    dictionary[key][SUP_INFO_KEY].append(supplementalInfoHandler.initializeSupplementalInfo())

        return newChildDictionaries


    def addDictionaries(self, dictionaries: List[Dict]):
        """
        Initializes the given (empty) dictionaries using the keys already present in the current dictionaries,
        and adds them to the list of outputDataDictionaries.
        Also initializes any supplemental information.
        Finally, checks to see if there are any child data stratifiers that need to add further dictionaries.
        """
        newChildDictionaries = list()
        hasChildStratifier = self.childDataStratifier is not None

        for dictionary in dictionaries:

            self.outputDataDictionaries.append(dictionary)
                
            if hasChildStratifier:
                newChildDictionaries.extend(self.initializeChildDictionaries(dictionary))
            else: 
                for key in self.allKeys: dictionary[key] = 0

        if hasChildStratifier: 
            self.childDataStratifier.addDictionaries(newChildDictionaries)


    def attemptAddKey(self, key):
        """
        Adds the key to all of the dictionaries in outputDataDictionaries, if it isn't already present.  
        Then, if this stratifier has any child stratifiers, creates new dictionaries at that key and passes them down through addDictionaries.
        Also initializes supplemental information for all child dictionaries.
        """
        assert key is SUP_INFO_KEY or key != SUP_INFO_KEY, "Collision with SUP_INFO_Key"

        if key in self.allKeys:
            self.onKeyAlreadyPresent(key)
            return

        newChildDictionaries = list()
        hasChildStratifier = self.childDataStratifier is not None
        self.allKeys.add(key)

        for dictionary in self.outputDataDictionaries:

            if hasChildStratifier: newChildDictionaries.extend(self.initializeChildDictionaries(dictionary, (key,)))
            else: dictionary[key] = 0

        if hasChildStratifier: self.childDataStratifier.addDictionaries(newChildDictionaries)


    def onKeyAlreadyPresent(self, key):
        """
        What should be done if the key is already present and couldn't be added?
        (Not an abstract function, because I think it'll be pretty common to put nothing here.)
        """


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
    def getSortedKeysForOutput(self):
        """
        A function which implements some functionality previously handled by getKeysForOutput by
        sorting the list of keys properly formatted for output.  This function is defined separately
        and only called once since getKeysForOutput may be called many times, but sorting the keys
        may be computationally expensive.
        """
        if None in self.allKeys:
            return sorted(self.allKeys - {None}) + [None]
        else:
            return sorted(self.allKeys)


    @abstractmethod
    def formatKeyForOutput(self, key):
        """
        Performs any formatting necessary to prepare the key for output. (String casting does NOT need to occur here.)
        """
        return key


    def getKeysForOutput(self):
        """
        Returns all keys that are suitable for output.
        """
        if self.sortedKeys is None: self.sortedKeys = self.getSortedKeysForOutput
        if self.keysFormattedForOutput is None: self.keysFormattedForOutput = (self.formatKeyForOutput(key) for key in self.sortedKeys)
        return self.keysFormattedForOutput

    
    def getSupplementalInfoOutput(self):
        """
        Returns a (potentially empty) list of lists of outputs for each supplemental information handler in the ODS
        Each output in the list corresponds to the key in the list of sorted keys at the same list index.
        """
        supplementalInfoOutput = list()

        for i, supplementalInfoHandler in enumerate(self.supplementalInfoHandlers):
            supplementalInfoOutput.append(
                (supplementalInfoHandler.getFormattedOutput(self.outputDataDictionaries[key][SUP_INFO_KEY][i]) 
                    for key in self.sortedKeys)
            )
        
        return supplementalInfoOutput


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


    def getSortedKeysForOutput(self):
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


    def formatKeyForOutput(self, key):
        return super().formatKeyForOutput(key)


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


    def getSortedKeysForOutput(self):
        """
        Returns True and False for strand matching and mismatching and also None if recording ambiguity
        """
        if None in self.allKeys: return [True, False, None]
        else: return [True, False]


    def formatKeyForOutput(self, key):
        return super().formatKeyForOutput(key)


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
        Add the encompassing feature to the set of keys.
        """

        # Check to see if we have encountered this encompassing feature before.  If not, add it as a new key.
        assert encompassingFeature not in self.allKeys, (
            "2 encompassing features have the same location data: " + encompassingFeature.getLocationString())
        self.attemptAddKey(encompassingFeature)

    
    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Retrieve the encompassing feature for the given encompassed feature and pass it back as a key.
        """
        if self.ambiguityHandling == AmbiguityHandling.tolerate or not encompassedFeature.ambiguousEncompassingFeature:
            return encompassedFeature.encompassingFeature

        else: return None


    def getSortedKeysForOutput(self):
        """
        Leverage the '<' operator between EncompassedData objects to sort the keys directly.
        """
        return super().getSortedKeysForOutput()


    def formatKeyForOutput(self, key):
        if key is None: return key
        else: return key.getLocationString()


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
        Pass back the encompassed feature as a key and add it to the set.
        This ensures that all encompassed features are properly tracked.
        """

        # Check to see if we have encountered this encompassed feature before.  If not, add it as a new key.
        if encompassedFeature not in self.allKeys: self.attemptAddKey(encompassedFeature)

    
    def getRelevantKey(self, encompassedFeature: EncompassedData):
        """
        Pass back the encompassed feature as a key.
        Also, check to see if the key has been seen before, and if not, add it.
        """

        # Check to see if we have encountered this encompassed feature before.  If not, add it as a new key.
        if encompassedFeature not in self.allKeys: self.attemptAddKey(encompassedFeature)

        return encompassedFeature


    def getSortedKeysForOutput(self):
        """
        Leverage the '<' operator between EncompassignData objects to sort the keys directly.
        """
        return super().getSortedKeysForOutput()


    def formatKeyForOutput(self, key):
        if key is None: return key
        else: return key.getLocationString()


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
            self.attemptAddKey(context)

        return context

    
    def getSortedKeysForOutput(self):
        """
        Return the sorted list of contexts seen throughout the encompassed features.
        """
        return super().getSortedKeysForOutput()


    def formatKeyForOutput(self, key):
        return super().formatKeyForOutput(key)


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

    
    def getSortedKeysForOutput(self):
        return super().getSortedKeysForOutput()


    def formatKeyForOutput(self, key):
        return super().formatKeyForOutput(key)