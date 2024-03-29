# This script centralizes the storage and access of different genome fasta file paths as well as associated bowtie2 index file paths.
import os, platform
from typing import Dict
from benbiohelpers.CustomErrors import checkIfPathExists, InvalidPathError, UserInputError
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs


class GenomeManagerError(Exception):
    "An error class to be raised when a stored genome fasta files cannot be accessed."

class UnrecognizedGenomeError(GenomeManagerError):
    """
    An error class for when a genome name is given that is not recognized
    (i.e. it is not stored in the genome manager's text file).
    """

    def __init__(self, genomeName: str):
        self.genomeName = genomeName

    def __str__(self):
        return f"Could not find a genome with the name \"{self.genomeName}\"."
    
class MissingGenomeFileError(GenomeManagerError):
    "An error class for when the stored file path for a genome no longer exists."
    def __init__(self, genomeName: str, genomeFastaFilePath: str):
        self.genomeName = genomeName
        self.genomeFastaFilePath = genomeFastaFilePath

    def __str__(self):
        return f"Genome Fasta file for {self.genomeName} was not found at the expected location: {self.genomeFastaFilePath}"

class MissingIndexFilesError(GenomeManagerError):
    "An error class for when a given index path prefix no longer points to full index files."
    def __init__(self, genomeName: str, indexPrefixPath: str):
        self.genomeName = genomeName
        self.indexPrefixPath = indexPrefixPath

    def __str__(self):
        return (f"Bowtie2 index path prefix {self.indexPrefixPath} for {self.genomeName} no longer points to full index files. "
                f"(e.g. {self.indexPrefixPath}.1.bt2)")


def _getPackageDir():
    "Get the path to the .benbiohelpers package directory, creating it if necessary."
    if platform.system() == "Linux":
        packageDirectory = os.path.join(os.getenv("HOME"), ".benbiohelpers")
    elif platform.system() == "Windows":
        packageDirectory = os.path.join(os.getenv("APPDATA"), ".benbiohelpers")
    checkDirs(packageDirectory)
    return packageDirectory


def _getGenomeListFilePath():
    "Get the path to the file containing the list of known genomes."
    return os.path.join(_getPackageDir(),"genomes.txt")


def _getIndexListFilePath():
    "Get the path to the file containing the list of bowtie2 index file path prefixes."
    return os.path.join(_getPackageDir(),"genomes_index_path_prefixes.txt")


def getGenomes() -> Dict[str,str]:
    "Return a dictionary of genome fasta file paths with genome names as keys"
    genomes = dict()
    if os.path.exists(_getGenomeListFilePath()):
        with open(_getGenomeListFilePath(), 'r') as genomeManagerFile:
            for line in genomeManagerFile:
                genomeName,genomeFilePath = line.strip().split(':')
                genomes[genomeName] = genomeFilePath
    return genomes


def getIndexPathPrefixes() -> Dict[str,str]:
    "Return a dictionary of index path prefixes with genome names as keys"
    indexPathPrefixes = dict()
    if os.path.exists(_getIndexListFilePath()):
        with open(_getIndexListFilePath(), 'r') as indexListFile:
            for line in indexListFile:
                genomeName,indexPathPrefix = line.strip().split(':')
                indexPathPrefixes[genomeName] = indexPathPrefix
    return indexPathPrefixes


def getGenomeFastaFilePath(genomeName):
    "Return the path to given genome's fasta file"
    genomes = getGenomes()
    if genomeName not in genomes: raise UnrecognizedGenomeError(genomeName)
    genomeFastaFilePath = genomes[genomeName]
    if os.path.exists(genomeFastaFilePath): return genomeFastaFilePath
    else: raise MissingGenomeFileError(genomeName, genomeFastaFilePath)


def getIndexPathPrefix(genomeName):
    "Return the path prefix of the genome's bowtie2 index."
    indexPathPrefixes = getIndexPathPrefixes()
    if genomeName in indexPathPrefixes: indexPathPrefix = indexPathPrefixes[genomeName]
    else: indexPathPrefix = getGenomeFastaFilePath(genomeName).rsplit('.',1)[0]
    if os.path.exists(indexPathPrefix+".1.bt2"): return indexPathPrefix
    else: raise MissingIndexFilesError(genomeName, indexPathPrefix)


def addGenome(genomeFastaFilePath: str, alias = None, indexPath: str = None):
    """
    Add the given genome fasta file to the genome manager file.
    If no alias (the colloquial name for the genome) is given, it is generated from the fasta file's name.
    Returns the alias.
    """

    # Make sure the given path exists and is valid.
    checkIfPathExists(genomeFastaFilePath)
    if not genomeFastaFilePath.endswith(".fa"):
        raise InvalidPathError(genomeFastaFilePath, postPathMessage = "Expected uncompressed fasta file.")
    
    # If no alias was given, derive it from the fasta file name.
    if alias is None: alias = os.path.basename(genomeFastaFilePath).rsplit('.', 1)[0]
    alias = alias.strip() # Also remove leading and trailing whitespace.
    if ':' in alias: raise UserInputError("Invalid character \":\" used in genome alias.")
    if '\n' in alias: raise UserInputError("Invalid character \"\\n\" used in genome alias.")

    # Add the alias and fasta file path to the dictionary of known genomes, overwriting an old entry if necessary.
    print(f"Adding genome fasta file {genomeFastaFilePath} as {alias}.")
    genomes = getGenomes()
    if alias in genomes and genomes[alias] != genomeFastaFilePath:
        print(f"NOTE: This action overwrites an entry which previously pointed to {genomes[alias]}")
    genomes[alias] = genomeFastaFilePath

    # Rewrite the genome manager file with the updated dictionary.
    with open(_getGenomeListFilePath(), 'w') as genomeManagerFile:
        for genomeName in sorted(genomes):
            genomeManagerFile.write(f"{genomeName}:{genomes[genomeName]}\n")

    # Write the custom index path, if given.
    if indexPath is not None:

        # Make sure the given path appears to point to a real index.
        if not (os.path.exists(indexPath) or os.path.exists(indexPath+".1.bt2")):
            raise InvalidPathError(indexPath, "Given path does not exist and is not a valid prefix of existing index files.")

        # If the full path was given, trim it down to the prefix.
        if os.path.exists(indexPath):
            indexPathPrefix = indexPath.rsplit('.', 2)[0]
            if indexPathPrefix.endswith(".rev"): indexPathPrefix = indexPathPrefix.rsplit('.', 1)[0]

        # Add the index and fasta file path to the dictionary of known genomes, overwriting an old entry if necessary.
        print(f"Adding custom bowtie2 index path prefix: {indexPathPrefix}")
        indexPathPrefixes = getIndexPathPrefixes()
        if alias in indexPathPrefixes and indexPathPrefixes[alias] != indexPathPrefix:
            print(f"NOTE: This action overwrites an entry which previously pointed to {indexPathPrefixes[alias]}")
        indexPathPrefixes[alias] = indexPathPrefix

        # Rewrite the genome manager file with the updated dictionary.
        with open(_getIndexListFilePath(), 'w') as indexListFile:
            for genomeName in sorted(indexPathPrefixes):
                indexListFile.write(f"{genomeName}:{indexPathPrefixes[genomeName]}\n")

    return alias
