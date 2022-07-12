# This script contains a series of classes for managing metadata in projects with a large degree of data stratification.
from abc import ABC, abstractmethod
from enum import Enum
from operator import eq
from typing import Any, Dict, Iterator, Type, Union
from benbiohelpers.CustomErrors import MetadataPathError
import os, warnings

class MetadataFeatureID(Enum):
    """
    An Enum baseclass to hold IDs for all the potential features of a Metadata class. It essentially serves as
    an abstract class, but due to the inability to extend or manually instantiate Enums, no ABC metaclass is necessary.
    This is useful when Metadata methods need to act on a specific feature, so an identifier for that feature needs to
    be passed as a parameter.
    The enum value is split into two parts:
    - ID: The auto-generated ID for the enum instance
    - type: The type of the associated metadata feature. This is especially important if the feature will be
        an instance of a MetadataFeatureEnum subclass, as accessing the the desired information
        will require a call to its value or other parameters
    """

    def __init__(self, id, type: type):
        self._id = id
        self.type = type


class MetadataFeatureValue(Enum):
    """
    This is an Enum for metadata features which have a discrete range of possible values, and those
    values need to be constrained/standardized. It essentially serves as an abstract class, but
    due to the inability to extend or manually instatiate Enums, no ABC metaclass is necessary.
    """


class Metadata(ABC):
    """
    This is an abstract class for handling metadata.
    It is used to keep track of the features that stratify different data files in a single project.
    Those features can be passed to functions to standaradize/define parameters for data handling, figure generation, etc.
    """

    defaultValues = dict() 
    """
    Keys: Should be instances of self.FeatureIDEnum
    Values: Default value for the associated metadata feature
    Note: Metadta features not in the dictionary will default to NoneType.
    """

    @property
    @abstractmethod
    def FeatureIDEnum(self) -> Type[MetadataFeatureID]:
        """
        An abstract property that must be instantiated as a subclass of MetadataFeatureIDs to keep track
        of IDs for all of the features of the metadata.
        """


    def __init__(self, initializationFilePath: str = None, directory: str = None, verboseDirectoryCreation = True):
        """
        The optional initializationFilePath option can be used to intialize this instance using either a metadata file (ending
        in .metadata) or a data file with metadata at ".metadata/[data file base name].metadata" relative to the data file's
        parent directory. For initialization by file path, this instance's directory is set to the parent directory of the
        retrieved metadata file.

        If no initializationFilePath is given, values for all Metadata parameters are set to None and
        a directory may be specified manually.
        """

        self.features: Dict[MetadataFeatureID, Any] = dict()
        self.initializeFeatures()

        if initializationFilePath is not None:
            if initializationFilePath.endswith(".metadata"):
                if not os.path.exists(initializationFilePath):
                    raise MetadataPathError(initializationFilePath, "Metadata file not found at expected location:")
            else:
                initializationFilePath = os.path.join(os.path.dirname(initializationFilePath),".metadata",
                                                      os.path.basename(initializationFilePath) + ".metadata")
                if not os.path.exists(initializationFilePath):
                    raise MetadataPathError(initializationFilePath,
                                            "Given initialization file does not end with \".metadata\", and a companion "
                                            "file is not found at:")
            self.directory = os.path.dirname(initializationFilePath)
            assert directory is None or directory == self.directory, "Directory given that doesn't match metadata file path."
            self.readFeaturesFromFile(initializationFilePath)
        elif directory is not None:
            if not directory.endswith(".metadata"):
                warnings.warn(f"Given metadata directory, {directory} does not end with \".metadata\" and may be incompatible "
                               "with further metadata initializations.")
            if not os.path.exists(directory):
                if not os.path.exists(os.path.dirname(directory)):
                    raise MetadataPathError(directory, "Neither the given metadata directory nor its parent directory exist:")
                else:
                    if verboseDirectoryCreation:
                        print(f"Creating metadata directory at {directory}")
                    os.mkdir(directory)
            self.directory = directory
        else: self.directory = None


    def __getitem__(self, metadataFeatureID: MetadataFeatureID) -> Union[MetadataFeatureValue, Any]:
        return self.features[metadataFeatureID]

    def __setitem__(self, metadataFeatureID: MetadataFeatureID, metadataFeature):
        self.features[metadataFeatureID] = metadataFeature


    def initializeFeatures(self):
        """
        Iterates through the class's feature IDs to initialize the dictionary of features (using NoneTypes).
        """
        for featureID in self.FeatureIDEnum: 
            if featureID in self.defaultValues: self[featureID] = self.defaultValues[featureID]
            else: self[featureID] = None


    def readFeaturesFromFile(self, metadataFilePath):
        """
        Given a file path, this function initializes this object using the data therein.
        """

        # Read through the file, retrieving id's and values for each line and using them
        # to initialize the self.features dictionary.
        with open(metadataFilePath, 'r') as metadataFile:
            for line in metadataFile:
                id, value = line.strip().split(":\t")
                metadataFeatureID = self.FeatureIDEnum[id]

                # If the feature's value is an enum name, convert accordingly
                if issubclass(metadataFeatureID.type,MetadataFeatureValue):
                    value = metadataFeatureID.type[value]

                self[metadataFeatureID] = value


    def getFilePath(self, useParentDirectory = True):
        """
        This function derives a file path from the metadata features.
        (Not required to be implemented by subclasses, but will raise an error if not implemented and called)
        The useParentDirectory parameter will typically determine whether the returned file path is directly under
        the Metadata object's directory (usually "\.metadata") or under its parent directory (usually also the parent
        directory for the metadata's companion data file.)
        """
        raise NotImplementedError


    def getFeaturesFromString(self, featuresString):
        """
        This function derives metadata features from a given string (usually a file path using strict naming conventions).
        (Not required to be implemented by subclasses, but will raise an error if not implemented and called)
        """
        raise NotImplementedError


    def writeFeaturesToFile(self, metadataFilePath = None):
        """
        Given a file path, write all the features of the metadata in a standard format that can
        also be read using the readFeaturesFromFile function.
        - MetadataFilePath: If set to NoneType, it will be auto-acquired using getFilePath
        """

        # If no metadata file path is given, try to derive one from the metadata itself.
        if metadataFilePath is None: metadataFilePath = self.getFilePath(False)+".metadata"

        # Loop through the metadata feature ID's, writing their respective features (if present)
        with open(metadataFilePath, 'w') as metadataFile:
            for metadataFeatureID in self.FeatureIDEnum:

                value = self[metadataFeatureID]

                # Skip any features that don't have associated values.
                if value is None: continue

                # If the feature's value is an enum name, convert accordingly
                if issubclass(metadataFeatureID.type,MetadataFeatureValue):
                    value = value.name

                metadataFile.write(f"{metadataFeatureID.name}:\t{value}\n")


    def copy(self):
        "Returns a deep copy of the metadata object."
        newMetadata = self.__class__(directory = self.directory)
        for metadataFeatureID in self.features:
            newMetadata[metadataFeatureID] = self[metadataFeatureID]
        return newMetadata


class MetadataList(list):
    """
    A list for managing Metadata objects and only metadata objects (or their subclasses).
    The highlights of this extension of the list class are the abilities to:
    - Deep copy all of the items in the list.
    - Update the values for a given metadata feature across all items in the list.
    - Retrieve items in the list that all have a specific value for a given feature.
    - Chain together the above operations since they each return a MetadataList object!
    """

    def __getitem__(self, __i) -> Metadata:
        return super().__getitem__(__i)

    def __iter__(self) -> Iterator[Metadata]:
        return super().__iter__()

    def copy(self):
        "Returns a deep copy of the list"
        newList = MetadataList()
        for metadata in self:
            newList.append(metadata.copy())
        return(newList)

    def copyWithChanges(self, features, newValues):
        """
        Alternative for stringing together a copy and update option.
        """
        return(self.copy().update(features, newValues))


    def update(self, features, newValues):
        """
        Updates the given feature(s) to the given value(s) in place.
        Also returns itself so it can be chained together with other operations.
        """

        if not isinstance(features,(list,tuple)): features = (features,)
        if not isinstance(newValues,(list,tuple)): newValues = (newValues,)

        if not len(features) == len(newValues):
            raise ValueError("Number of features given is not equal to number of values.")

        for metadata in self:
            for feature, newValue in zip(features, newValues):
                metadata[feature] = newValue

        return self


    def subset(self, featureID: MetadataFeatureID, value, operator = eq, metadataShallowCopy = True):
        """
        Subsets the list based on the comparisons made against the given feature of each item and the given value.
        By default, this comparison is a simple equality check, but this can be changed with the operator argument.
        Note that this makes a shallow copy of the metadata by default, but this can be changed with the 
        metadataShallowCopy argument. 
        """

        subsettedList = MetadataList()
        for metadata in self:
            if operator(metadata[featureID], value):
                if metadataShallowCopy: subsettedList.append(metadata)
                else: subsettedList.append(metadata.copy())

        return subsettedList
