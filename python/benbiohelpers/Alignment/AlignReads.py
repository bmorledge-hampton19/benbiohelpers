import os, subprocess, time, re
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs, getIsolatedParentDir
from benbiohelpers.CustomErrors import InvalidPathError, UserInputError
from benbiohelpers.Alignment.FindAdapters import findAdapters as findAdaptersFunc
from benbiohelpers.InputParsing.CheckForNumber import checkForNumber
from typing import List


# Write metadata on the parameters for the alignment, for future reference.
def writeMetadata(rawReadsFilePath: str, pairedEndAlignment, bowtie2IndexBasenamePath,
                  adapterSequencesFilePath = None, bowtie2Version = None, customBowtie2Arguments = None):

    if pairedEndAlignment: basename = os.path.basename(rawReadsFilePath).rsplit('_', 1)[0]
    else: basename = os.path.basename(rawReadsFilePath).rsplit(".fastq", 1)[0]
    checkDirs(os.path.join(os.path.dirname(rawReadsFilePath),".metadata"))
    metadataFilePath = os.path.join(os.path.dirname(rawReadsFilePath),".metadata",f"{basename}_alignment.metadata")
    with open(metadataFilePath, 'w') as metadataFile:

        if bowtie2Version is None: bowtie2Version = subprocess.check_output(("bowtie2","--version"), encoding=("utf-8"))

        metadataFile.write("Path_to_Index:\n" + bowtie2IndexBasenamePath + "\n\n")
        if adapterSequencesFilePath is not None:
            metadataFile.write("Path_to_Adapter_Sequences:\n" + adapterSequencesFilePath + "\n\n")
        metadataFile.write("Bowtie2_Version:\n" + bowtie2Version + "\n")
        metadataFile.write("Bowtie2_Stats:\n")
        bowtie2StatsFilePath = os.path.join(os.path.dirname(rawReadsFilePath),".tmp",f"{basename}_bowtie2_stats.txt")
        with open(bowtie2StatsFilePath, 'r') as bowtie2StatsFile:
            atStats = False
            for line in bowtie2StatsFile:
                if not atStats and line.endswith("reads; of these:\n"): atStats = True
                if atStats: metadataFile.write(line)
            if not atStats: raise InvalidPathError("Malformed bowtie2 stats.")
        metadataFile.write('\n')
        os.remove(bowtie2StatsFilePath)
        if customBowtie2Arguments is not None and customBowtie2Arguments:
            metadataFile.write(f"Custom_Bowtie2_arguments: {customBowtie2Arguments}\n\n")


# For each of the given reads files, run the accompyaning bash script to perform the alignment.
def alignReads(rawReadsFilePaths: List[str], bowtie2IndexBasenamePath, adapterSequencesFilePath = None, 
                    readCountsOutputFilePath = None, bowtie2BinaryPath = None, threads = 1, customBowtie2Arguments = '',
                    findAdapters = False, pairedEndAlignment = False, interleavedPairedEndFiles = False,
                    pipelineEndpoint = ".bed", retainSamOutput = False):

    # Get the bash alignment script file path.
    alignmentBashScriptFilePath = os.path.join(os.path.dirname(__file__),"ParseRawReadsToBed.bash")

    # Make sure a valid pipelineEndpoint was given.
    if pipelineEndpoint not in (".bed", ".bed.gz", ".sam", ".sam.gz"):
        raise UserInputError(f"Unrecognized pipeline endpoint given: {pipelineEndpoint}\n"
                             'Expected ".bed", ".bed.gz", ".sam", or ".sam.gz"')

    # If performing paired end alignment, find pairs for all the given raw reads files.
    if pairedEndAlignment and not interleavedPairedEndFiles:
        read1FilePaths = list(); read2FilePaths = list()
        for rawReadsFilePath in rawReadsFilePaths:

            # It's possible we have already assigned this file path as a pair of a previous path. Double check!
            if rawReadsFilePath in read1FilePaths or rawReadsFilePath in read2FilePaths: continue

            # Find the pair and assign each pair to their respective list.
            baseName = rawReadsFilePath.rsplit(".fastq",1)[0]
            if baseName.endswith("_1") or baseName.endswith("_R1"):
                read1FilePaths.append(rawReadsFilePath)
                pairedBaseName = baseName[:-1] + '2'
                pairedList = read2FilePaths
            elif baseName.endswith("_2") or baseName.endswith("_R2"):
                read2FilePaths.append(rawReadsFilePath)
                pairedBaseName = baseName[:-1] + '1'
                pairedList = read1FilePaths
            else: raise InvalidPathError(rawReadsFilePath, "Given path does not end with \"_1\", \"_R1\", \"_2\" or \"_R2\" "
                                                           "(prior to file extension; e.g. my_reads_2.fastq.gz is valid.)")

            pairFound = False
            for fileExtension in (".fastq", ".fastq.gz"):
                pairedFilePath = pairedBaseName + fileExtension
                if os.path.exists(pairedFilePath): 
                    pairedList.append(pairedFilePath)
                    print(f"Found fastq file pair with basename: {os.path.basename(pairedBaseName).rsplit('_',1)[0]}")
                    pairFound = True
                    break

            if not pairFound: raise InvalidPathError(rawReadsFilePath, "No matching pair found. Expected paired files (in same "
                                                                       "directory) ending in \"1\" and \"2\", but only found:")

        rawReadsFilePaths = read1FilePaths

    readCounts = dict()
    scriptStartTime = time.time()
    currentReadFileNum = 0
    totalReadsFiles = len(rawReadsFilePaths)

    for i, rawReadsFilePath in enumerate(rawReadsFilePaths):

        # Print information about the current file
        currentReadFileNum += 1
        readsFileStartTime = time.time()
        print()
        if pairedEndAlignment: 
            print(f"Processing file pair with basename {os.path.basename(rawReadsFilePath).rsplit('_',1)[0]}")
        else: print("Processing file",os.path.basename(rawReadsFilePath))
        print('(',currentReadFileNum,'/',totalReadsFiles,')', sep = '') 

        # If requested find adapters in the current fastq file(s) based on the given list of adapters.
        if findAdapters and not pairedEndAlignment:
            thisAdapterSequencesFilePath = findAdaptersFunc([rawReadsFilePath], adapterSequencesFilePath)[0]
        elif findAdapters and pairedEndAlignment:
            thisAdapterSequencesFilePath = findAdaptersFunc([read1FilePaths[i], read2FilePaths[i]],
                                                            adapterSequencesFilePath, aggregateOutput = True)[0]
        else: thisAdapterSequencesFilePath = adapterSequencesFilePath

        # Make sure the .tmp directory exists and create a path to the bowtie2 stats file.
        tempDir = os.path.join(os.path.dirname(rawReadsFilePath),".tmp")
        checkDirs(tempDir)

        # Run the alignment script.
        if pairedEndAlignment and not interleavedPairedEndFiles:
            arguments = ["bash", alignmentBashScriptFilePath, "-1", read1FilePaths[i], "-2", read2FilePaths[i]]
        elif pairedEndAlignment and interleavedPairedEndFiles:
            arguments = ["bash", alignmentBashScriptFilePath, "-1", rawReadsFilePath, "--interleaved"]
        else:
            arguments = ["bash", alignmentBashScriptFilePath, "-1", rawReadsFilePath]
        arguments += ["-i", bowtie2IndexBasenamePath, "-t", str(threads), "-c", customBowtie2Arguments, "-p", pipelineEndpoint]
        if thisAdapterSequencesFilePath is not None: arguments += ["-a", thisAdapterSequencesFilePath]
        if bowtie2BinaryPath is not None: arguments += ["-b", bowtie2BinaryPath]
        if retainSamOutput: arguments += ["-s"]
        subprocess.run(arguments, check = True)

        # If requested, count the number of reads in the original input file(s).
        if readCountsOutputFilePath is not None:
            print("Counting reads in original reads file(s)...")

            zcatProcess = subprocess.Popen(("zcat", rawReadsFilePath), stdout = subprocess.PIPE)
            readCountProcess = subprocess.Popen(("wc", "-l"), stdin = zcatProcess.stdout, stdout = subprocess.PIPE)
            readCount = readCountProcess.communicate()[0].decode("utf8")
            readCounts[os.path.basename(rawReadsFilePath)] = str( round(int(readCount)/4) )

            if pairedEndAlignment:
                zcatProcess = subprocess.Popen(("zcat", read2FilePaths[i]), stdout = subprocess.PIPE)
                readCountProcess = subprocess.Popen(("wc", "-l"), stdin = zcatProcess.stdout, stdout = subprocess.PIPE)
                readCount = readCountProcess.communicate()[0].decode("utf8")
                readCounts[os.path.basename(read2FilePaths[i])] = str( round(int(readCount)/4) )

        # Output information on time elapsed.
        if pairedEndAlignment:
            print(f"Time taken to align reads in this file pair: {time.time() - readsFileStartTime} seconds")
        else:
            print(f"Time taken to align reads in this file: {time.time() - readsFileStartTime} seconds")
        print(f"Total time spent aligning across all files: {time.time() - scriptStartTime} seconds")

        # Write the metadata.
        writeMetadata(rawReadsFilePath, pairedEndAlignment, bowtie2IndexBasenamePath, 
                      thisAdapterSequencesFilePath, bowtie2BinaryPath, customBowtie2Arguments)

    # Write the read counts if requested.
    if readCountsOutputFilePath is not None:
        with open(readCountsOutputFilePath, 'w') as readCountsOutputFile:
            for rawReadsFileBasename in readCounts:
                readCountsOutputFile.write(rawReadsFileBasename + ": " + readCounts[rawReadsFileBasename] + '\n')


# Removes trimmed reads file paths from a list of fastq reads file paths.
# Returns the filtered list of file paths. Does not alter the original list.
def removeTrimmedAndTmp(unfilteredReadsFilePaths: List[str]):
    return [filePath for filePath in unfilteredReadsFilePaths if 
            getIsolatedParentDir(filePath) != ".tmp"]
            # and not "trimmed.fastq" in filePath and
            # re.search("trimmed_..\.fastq", filePath) is None]


def parseArgs(args):
    pass
    # TODO: Implement this


def main():

    # Create a simple dialog for selecting the relevant files.
    with TkinterDialog(title = "Benbiohelpers Read Aligner") as dialog:
        dialog.createMultipleFileSelector("Raw fastq reads:", 0, ".fastq.gz",
                                        ("Fastq Files", (".fastq.gz", ".fastq")), ("fastq Files", ".fastq"),
                                        additionalFileEndings=[".fastq"])
        dialog.createFileSelector("Bowtie2 Index File (Any):", 1, ("Bowtie2 Index File", ".bt2"))

        with dialog.createDynamicSelector(2, 0) as endModeDS:
            endModeDS.initDropdownController("Alignment method:", ("Single-end", "Paired-end"))
            endModeDS.initDisplay("Paired-end", "Paired-end").createDropdown(
                "Paired-end file format", 0, 0, ("One file per end (two files)", "Interleaved reads (single file)")
            )

        with dialog.createDynamicSelector(3, 0) as adapterSequencesDS:
            adapterSequencesDS.initDropdownController("Adapter type",
                                                      ("Custom", "Find Adapters", "XR-seq Adapters", "None"))
            adapterSequencesSelector = adapterSequencesDS.initDisplay("Custom", selectionsID = "customAdapterSequences")
            adapterSequencesSelector.createFileSelector("Custom Adapters Sequences File:", 0, ("Fasta Files", ".fa"))
            adapterSequencesSelector = adapterSequencesDS.initDisplay("Find Adapters", selectionsID = "potentialAdapterSequences")
            adapterSequencesSelector.createFileSelector("Potential Adapter Sequences File:", 0, ("Fasta Files", ".fa"))

        dialog.createTextField("How many Threads should be used?", 4, 0, defaultText="1")

        with dialog.createDynamicSelector(5, 0) as additionalOptions:
            additionalOptions.initDropdownController("Additional Options:", ("Ignore", "Use"))
            additionalOptionsDialog = additionalOptions.initDisplay("Use", "AddOps")

            with additionalOptionsDialog.createDynamicSelector(0, 0) as bowtie2BinaryDS:
                bowtie2BinaryDS.initCheckboxController("Choose alternative bowtie2 binary")
                bowtie2BinarySelector = bowtie2BinaryDS.initDisplay(True, selectionsID = "bowtieBinary")
                bowtie2BinarySelector.createFileSelector("bowtie2 binary:", 0, ("Any File", "*"))

            with additionalOptionsDialog.createDynamicSelector(1, 0) as readCountsDS:
                readCountsDS.initCheckboxController("Record initial read counts")
                readCountsSelector = readCountsDS.initDisplay(True, selectionsID = "readCounts")
                readCountsSelector.createFileSelector("Save read counts at:", 0, ("Text File", ".txt"), newFile = True)

            with additionalOptionsDialog.createDynamicSelector(2, 0) as customArgsDS:
                customArgsDS.initDropdownController("Custom Bowtie2 Arguments:", ("None", "From File", "Direct Input"))
                customArgsDS.initDisplay("From File", selectionsID = "customArgs").createFileSelector(
                    "Custom Arguments File:", 0, ("Text File", ".txt")
                )
                customArgsDS.initDisplay("Direct Input", selectionsID = "customArgs").createTextField(
                    "Custom Arguments:", 0, 0, defaultText = ''
                )

            with additionalOptionsDialog.createDynamicSelector(3,0) as pipelineEndpointDS:
                pipelineEndpointDS.initDropdownController("Pipeline endpoint", (".bed",".bed.gz",".sam",".sam.gz"))
                pipelineEndpointDS.initDisplay(".bed", ".bed").createCheckbox("Retain sam file in main directory", 0, 0)
                pipelineEndpointDS.initDisplay(".bed.gz", ".bed.gz").createCheckbox("Retain sam file in main directory", 0, 0)

    # Get the raw reads files, but make sure that no trimmed reads files have tagged along!
    unfilteredRawReadsFilePaths = dialog.selections.getFilePathGroups()[0]
    filteredRawReadsFilePaths = removeTrimmedAndTmp(unfilteredRawReadsFilePaths)

    bowtie2IndexBasenamePath: str = dialog.selections.getIndividualFilePaths()[0]
    bowtie2IndexBasenamePath = bowtie2IndexBasenamePath.rsplit('.', 2)[0]
    if bowtie2IndexBasenamePath.endswith(".rev"): bowtie2IndexBasenamePath = bowtie2IndexBasenamePath.rsplit('.', 1)[0]

    interleavedPairedEndFiles = False
    if endModeDS.currentDisplayKey == "Paired-end":
        pairedEndAlignment = True
        if dialog.selections.getDropdownSelections("Paired-end")[0].startswith("Interleaved"): interleavedPairedEndFiles = True
    else: pairedEndAlignment = False

    findAdapters = False
    if adapterSequencesDS.getControllerVar() == "XR-seq Adapters":
        adapterSequencesFilePath = os.path.join(os.path.dirname(__file__), "XR-seq_primers.fa")
    elif adapterSequencesDS.getControllerVar() == "Custom":
        adapterSequencesFilePath = dialog.selections.getIndividualFilePaths("customAdapterSequences")[0]
    elif adapterSequencesDS.getControllerVar() == "Find Adapters":
        adapterSequencesFilePath = dialog.selections.getIndividualFilePaths("potentialAdapterSequences")[0]
        findAdapters = True
    else: adapterSequencesFilePath = None

    threads = checkForNumber(dialog.selections.getTextEntries()[0], True, lambda x:x>0, "Expected a positive-integer number of threads")

    if readCountsDS.getControllerVar():
        readCountsOutputFilePath = dialog.selections.getIndividualFilePaths("readCounts")[0]
    else: readCountsOutputFilePath = None

    if bowtie2BinaryDS.getControllerVar():
        bowtie2BinaryPath = dialog.selections.getIndividualFilePaths("bowtieBinary")[0]
    else: bowtie2BinaryPath = None

    if customArgsDS.getControllerVar() == "None":
        customBowtie2Arguments = ''
    elif customArgsDS.getControllerVar() == "From File":
        customBowtie2ArgsFilePath = dialog.selections.getIndividualFilePaths("customArgs")[0]
        with open(customBowtie2ArgsFilePath, 'r') as customBowtie2ArgsFile:
            customBowtie2Arguments = customBowtie2ArgsFile.readline().strip()
    elif customArgsDS.getControllerVar() == "Direct Input":
        customBowtie2Arguments = dialog.selections.getTextEntries("customArgs")[0]


    if additionalOptions.getControllerVar() == "Use":
        pipelineEndpoint = pipelineEndpointDS.getControllerVar()
        if pipelineEndpoint == ".bed": retainSamOutput = dialog.selections.getToggleStates(".bed")[0]
        elif pipelineEndpoint == ".bed.gz": retainSamOutput = dialog.selections.getToggleStates(".bed.gz")[0]
        else: retainSamOutput = True
    else:
        pipelineEndpoint = ".bed"
        retainSamOutput = False

    alignReads(filteredRawReadsFilePaths, bowtie2IndexBasenamePath, adapterSequencesFilePath, readCountsOutputFilePath,
               bowtie2BinaryPath, threads, customBowtie2Arguments, findAdapters, pairedEndAlignment, interleavedPairedEndFiles,
               pipelineEndpoint, retainSamOutput)


if __name__ == "__main__": main()