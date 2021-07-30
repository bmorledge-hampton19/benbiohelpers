# This script houses the SupplementalInformation class and subclasses.
# These classes are used to add additional information to the output data stratifiers.
from abc import ABC, abstractmethod
from typing import Any, Set
from benbiohelpers.CountThisInThat.InputDataStructures import *

SUP_INFO_KEY = "SIK"

class SupplementalInformationHandler(ABC):
    """
    A class which allows ODS's to output additional information at any stage prior to final counts.
    """

    def __init__(self, outputName):
        """
        Right now, just sets the name for the data column in the output file.
        """
        self.outputName = outputName

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

    def __init__(self, outputName = "Transcription_Factor_Binding_Sites"):
        super().__init__(outputName)

    def initializeSupplementalInfo(self):
        return set()    

    def updateSupplementalInfo(self, currentInfo: Set[str], encompassedData: EncompassedData, encompassingData: TfbsData):
        currentInfo.add(encompassingData.tfbsName+encompassingData.strand)
        return currentInfo

    def getFormattedOutput(self, info):
        return ','.join(sorted(info))