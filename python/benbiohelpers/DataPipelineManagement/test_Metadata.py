from benbiohelpers.DataPipelineManagement.Metadata import *
from operator import is_
from enum import auto
import pytest

class FruitType(MetadataFeatureValue):
    APPLE = auto()
    BUNCH_OF_GRAPES = auto()
    ORANGE = auto()

class TestMetadataFeatureID(MetadataFeatureID):
    FRUIT = auto(), FruitType
    AMOUNT = auto(), float
    NAME = auto(), str
    COMPANY = auto(), str
TMFID = TestMetadataFeatureID

class TestMetadata(Metadata):
    FeatureIDEnum = TestMetadataFeatureID

    def getFilePath(self, fileExtension=None):

        filePathPieces = list()

        for testMetadataFeatureID in TestMetadataFeatureID:
            if self[testMetadataFeatureID] is not None:
                if testMetadataFeatureID is TMFID.FRUIT:
                    filePathPieces.append(self[TMFID.FRUIT].name)
                else: filePathPieces.append(str(self[testMetadataFeatureID]))

        if fileExtension is None: filePathPieces.append(".txt")
        else: filePathPieces.append(fileExtension)

        return os.path.join(self.directory,'_'.join(filePathPieces))
        

testDirectory = os.path.dirname(__file__)

def test_FAIL_invalid_FeatureIDEnum():
    
    class InvalidMetadata(Metadata):
        def getFilePath(self):
            return("Foo")
    
    with pytest.raises(TypeError): invalidMetadata = InvalidMetadata()


def test_FAIL_not_implemented_getFilePath():

    class TestMetadataWithoutGetFilePath(Metadata):
        FeatureIDEnum = TestMetadataFeatureID

    testMetadata = TestMetadataWithoutGetFilePath()
    with pytest.raises(NotImplementedError): _ = testMetadata.getFilePath()


def test_metadata_creation():
    testMetadata = TestMetadata()


def test_initialization_and_retrieval():
    testMetadata = TestMetadata()
    assert testMetadata[TMFID.FRUIT] is None


def test_assignment():
    testMetadata = TestMetadata()
    testMetadata[TMFID.FRUIT] = FruitType.ORANGE
    assert testMetadata[TMFID.FRUIT] is FruitType.ORANGE


def test_automated_metadata_read_write():
    testMetadata = TestMetadata(directory = testDirectory)
    testMetadata[TMFID.FRUIT] = FruitType.BUNCH_OF_GRAPES
    testMetadata[TMFID.AMOUNT] = 2.99
    testMetadata[TMFID.COMPANY] = "Grapes_R_Us"
    testMetadata.writeFeaturesToFile()
    newTestMetadata = TestMetadata(testMetadata.getFilePath(".metadata"))
    assert newTestMetadata[TMFID.FRUIT] is FruitType.BUNCH_OF_GRAPES


def test_basic_metadata_list_ops():

    testMetadata1 = TestMetadata()
    testMetadata1[TMFID.FRUIT] = FruitType.BUNCH_OF_GRAPES

    testMetadata2 = TestMetadata()
    testMetadata2[TMFID.FRUIT] = FruitType.ORANGE

    testMetadatas = MetadataList([testMetadata1,testMetadata2])

    testMetadatas[1] = TestMetadata()

    testMetadatas.append(TestMetadata())
    testMetadatas[2][TMFID.COMPANY] = "Orange_Mart"

    assert testMetadatas[0][TMFID.FRUIT] is FruitType.BUNCH_OF_GRAPES
    assert testMetadatas[1][TMFID.FRUIT] is None
    assert testMetadatas[1:][1][TMFID.COMPANY] == "Orange_Mart"


def test_metadata_list_subset():

    testMetadatas = MetadataList(TestMetadata() for _ in range(3))
    testMetadatas[0][TMFID.FRUIT] = FruitType.APPLE
    testMetadatas[1][TMFID.FRUIT] = FruitType.ORANGE
    testMetadatas[2][TMFID.FRUIT] = FruitType.APPLE

    assert len(testMetadatas.subset(TMFID.FRUIT, FruitType.APPLE, is_)) == 2

    testMetadatas = MetadataList(TestMetadata() for _ in range(3))
    testMetadatas[0][TMFID.AMOUNT] = 1.99
    testMetadatas[1][TMFID.AMOUNT] = 1.99
    testMetadatas[2][TMFID.AMOUNT] = 2.99

    assert len(testMetadatas.subset(TMFID.AMOUNT, 2.99)) == 1


def test_metadata_list_copy_with_changes():

    testMetadatas = MetadataList(TestMetadata() for _ in range(2))
    testMetadatas[0][TMFID.FRUIT] = FruitType.APPLE
    testMetadatas[1][TMFID.FRUIT] = FruitType.ORANGE

    testMetadatas += testMetadatas.copyWithChanges(TMFID.COMPANY, "Green_Bluff")

    assert len(testMetadatas) == 4
    assert sum(metadata[TMFID.COMPANY] == "Green_Bluff" for metadata in testMetadatas) == 2

    testMetadatas[3][TMFID.FRUIT] = FruitType.BUNCH_OF_GRAPES

    assert testMetadatas[0][TMFID.FRUIT] is FruitType.APPLE
    assert testMetadatas[1][TMFID.FRUIT] is FruitType.ORANGE
    assert testMetadatas[3][TMFID.FRUIT] is FruitType.BUNCH_OF_GRAPES

