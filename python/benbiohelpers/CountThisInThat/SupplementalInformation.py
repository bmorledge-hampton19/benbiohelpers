# This script houses the SupplementalInformation class and subclasses.
# These classes are used to add additional information to the output data stratifiers.
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Union
from benbiohelpers.CountThisInThat.InputDataStructures import *
from benbiohelpers.DNA_SequenceHandling import reverseCompliment

SUP_INFO_KEY = "SIK"

class SupplementalInformationHandler(ABC):
    """
    A class which allows ODS's to output additional information at any stage prior to final counts.
    """

    def __init__(self, outputName, updateUntilExit, updateOnCount):
        # NOTE: There are two update flags. I THINK that updateUntilExit means that the update function is called on every
        # case of encompassment, whereas updateOnCount means that the update function is called only when the feature is
        # actually counted, which can change based on ambiguity handling.
        self.outputName = outputName
        self.updateUntilExit = updateUntilExit
        self.updateOnCount = updateOnCount

    @abstractmethod
    def initializeSupplementalInfo(self) -> Any:
        """
        Returns the default value for the supplemental info
        """

    @abstractmethod
    def updateSupplementalInfo(self, currentInfo, encompassedData: EncompassedData, encompassingData: EncompassingData) -> Any:
        """
        Takes the given "currentInfo" and modifies it based on the given encompassed data.
        Returns the result.
        """

    @abstractmethod
    def getFormattedOutput(self, info) -> str:
        """
        Returns the info as some string, formatted for file output.
        """


class TfbsSupInfoHandler(SupplementalInformationHandler):
    """
    Stores a list of transcription factor binding sites found at each
    stratification condition.
    """

    def __init__(self, outputName = "Transcription_Factor_Binding_Sites", updateUntilExit = True, updateOnCount = False):
        super().__init__(outputName, updateUntilExit, updateOnCount)

    def initializeSupplementalInfo(self):
        return set()    

    def updateSupplementalInfo(self, currentInfo: Set[str], encompassedData: EncompassedData, encompassingData: TfbsData):
        currentInfo.add(encompassingData.tfbsName+encompassingData.strand)
        return currentInfo

    def getFormattedOutput(self, info):
        return ','.join(sorted(info))


class BaseInEncompassingSequenceSupInfoHandler(SupplementalInformationHandler):
    """
    Keeps track of the position(s) (multiple if half base position) of the encompassed feature within encompassing features.
    If there are multiple encompassing features, the longest is the one displayed.
    Information appears as the sequence associated with the longest encompassing feature with the encompassed position(s) capitalized
    """

    def __init__(self, outputName = "Encompassed_Base_In_Encompassing_Sequence", updateUntilExit = True, updateOnCount = False):
        super().__init__(outputName, updateUntilExit, updateOnCount)
    
    def initializeSupplementalInfo(self):
        return [0,'']

    def updateSupplementalInfo(self, currentInfo, encompassedData: EncompassedData, encompassingData: TfbsData):

        # If this is the first time the supplemental information has been updated, we'll need to pinpoint the encompassed data position.
        # Also, if this encompassing data is larger than the sequence associated with the current info, overwrite it!
        if currentInfo is None or currentInfo[0] < encompassingData.endPos - encompassingData.startPos:

            # First, find out if we're dealing with a single base or half base position and set the position(s) relative to the encompassing sequence.
            # Don't forget to account for the strand of the encompassing feature!
            if encompassingData.strand == '-': posDiff = encompassingData.endPos - encompassedData.position
            else: posDiff = encompassedData.position - encompassingData.startPos

            if int(encompassedData.position) == encompassedData.position: relativePos = (int(posDiff),)
            else: relativePos = (int(posDiff-0.5),int(posDiff+0.5))

            # Now, construct the sequence with the capital letter(s) representing the encompassed feature
            sequenceWithCaps = encompassingData.sequence.lower()
            sequenceWithCaps = (
                sequenceWithCaps[:min(relativePos)] + # Portion before capitals
                ''.join([sequenceWithCaps[pos].upper() for pos in relativePos]) + # Capitals
                sequenceWithCaps[max(relativePos) + 1:] # Portion after capitals
            )

            return [encompassingData.endPos - encompassingData.startPos, sequenceWithCaps]

        else: return currentInfo
    
    def getFormattedOutput(self, info) -> str:
        return info[1]
            

class MutationTypeSupInfoHandler(SupplementalInformationHandler):
    """
    Keeps track of the mutation types seen.
    Returns each mutation type seen, along with the number of times it was seen.  E.g. "C>A:4,C>T:2"
    """

    def __init__(self, outputName = "Mutation_Types", updateUntilExit = False, updateOnCount = True):
        super().__init__(outputName, updateUntilExit, updateOnCount)

    def initializeSupplementalInfo(self):
        return dict()

    def updateSupplementalInfo(self, currentInfo: Dict, encompassedData: EncompassedDataWithContext, encompassingData: EncompassingData):
        currentInfo[encompassedData.getMutation()] = currentInfo.setdefault(encompassedData.getMutation(),0) + 1
        return currentInfo

    def getFormattedOutput(self, info) -> str:
        return ','.join([mutation + ':' + str(info[mutation]) for mutation in info])


class SimpleColumnSupInfoHandler(SupplementalInformationHandler):
    """
    Returns the string at a given column index, either for encompassed or encompassing data (defined by relevantData in __init__).
    By default, duplicates are removed, and if more than one string is found, they are joined with semicolons.
    """

    def __init__(self, outputName = "Col_Data", updateUntilExit = True, updateOnCount = False,
                 relevantData = ENCOMPASSED_DATA, dataCol = 0, emptyInfoSub = "NONE", removeDups = True,
                 separator = ';'):
        super().__init__(outputName, updateUntilExit, updateOnCount)
        self.relevantData = relevantData
        self.dataCol = dataCol
        self.emptyInfoSub = emptyInfoSub
        self.removeDups = removeDups
        self.separator = separator

    def initializeSupplementalInfo(self):
        if self.removeDups: return dict()
        else: return list()

    def updateSupplementalInfo(self, currentInfo: Union[Dict,List], encompassedData: EncompassedData, encompassingData: EncompassingData):
        if self.relevantData == ENCOMPASSED_DATA: relevantData = encompassedData
        elif self.relevantData == ENCOMPASSING_DATA: relevantData = encompassingData
        else: raise ValueError("Invalid relevant data value. Should be ENCOMPASSED_DATA or ENCOMPASSING_DATA.")
        colData = relevantData.choppedUpLine[self.dataCol]
        if self.removeDups: currentInfo[colData] = None
        else: currentInfo.append(colData)
        return currentInfo

    def getFormattedOutput(self, info: Union[Dict,List]) -> str:
        if len(info) == 0: return self.emptyInfoSub
        else:
            if self.removeDups: return self.separator.join(info.keys())
            else: return self.separator.join(info)
