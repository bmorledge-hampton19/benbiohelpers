from benbiohelpers.DataPipelineManagement.Metadata import *
from operator import is_
from enum import auto
import pytest, shutil

class FruitType(MetadataFeatureValue):
    APPLE = "apple"
    BUNCH_OF_GRAPES = "bunch_of_grapes"
    ORANGE = "orange"

class TestMetadataFeatureID(MetadataFeatureID):
    FRUIT = auto(), FruitType
    COST = auto(), float
    NAME = auto(), str
    COMPANY = auto(), str
TMFID = TestMetadataFeatureID

class TestMetadata(Metadata):
    FeatureIDEnum = TestMetadataFeatureID

    def getFilePath(self, useParentDirectory = True):

        filePathPieces = list()

        for testMetadataFeatureID in TestMetadataFeatureID:
            if self[testMetadataFeatureID] is not None:
                if testMetadataFeatureID is TMFID.FRUIT:
                    filePathPieces.append(self[TMFID.FRUIT].value)
                else: filePathPieces.append(str(self[testMetadataFeatureID]))

        if useParentDirectory: directory = os.path.dirname(self.directory)
        else: directory = self.directory

        return os.path.join(directory,'_'.join(filePathPieces) + ".tsv")
        

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
    shutil.rmtree(os.path.join(testDirectory,".metadata"))
    testMetadata = TestMetadata(directory = os.path.join(testDirectory,".metadata"))
    testMetadata[TMFID.FRUIT] = FruitType.BUNCH_OF_GRAPES
    testMetadata[TMFID.COST] = 2.99
    testMetadata[TMFID.COMPANY] = "Grapes_R_Us"
    testMetadata.writeFeaturesToFile()

    newTestMetadata = TestMetadata(testMetadata.getFilePath(False)+".metadata")
    assert newTestMetadata[TMFID.FRUIT] is FruitType.BUNCH_OF_GRAPES

    newTestMetadata = TestMetadata(os.path.join(testDirectory, "bunch_of_grapes_2.99_Grapes_R_Us.tsv"))
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
    testMetadatas[0][TMFID.COST] = 1.99
    testMetadatas[1][TMFID.COST] = 1.99
    testMetadatas[2][TMFID.COST] = 2.99

    assert len(testMetadatas.subset(TMFID.COST, 2.99)) == 1


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

