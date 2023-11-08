import os, platform
from benbiohelpers.DataPipelineManagement.DataDir import DataDir
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs

def getDataDir(): return TESTDataDir.getDataDirectory()

class TESTDataDir(DataDir):

    @staticmethod
    def _getPackageDirectory():
        """
        Returns the path to the package directory to be used by the child of the DataDir class. Also ensures that directory exists.
        This directory will be used to store the text file that will contain the path to the data directory so that its location is static and reliable.
        It will also be used as the default location for the directory selection GUI.
        """

        if platform.system() == "Linux":
            packageDirectory = os.path.join(os.getenv("HOME"), ".TEST")
        elif platform.system() == "Windows":
            packageDirectory = os.path.join(os.getenv("APPDATA"), ".TEST")
        checkDirs(packageDirectory)
        return packageDirectory


    @staticmethod
    def _getDataDirectoryPath(dataDirectoryDirectory):
        """
        Returns the path to the data directory given its parent directory.
        """

        return os.path.join(dataDirectoryDirectory,"TEST_data")