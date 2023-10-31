import os, subprocess
from typing import List
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.Alignment.AlignReads import removeTrimmedAndTmp
from benbiohelpers.CustomErrors import InvalidPathError
from benbiohelpers.InputParsing.CheckForNumber import checkForNumber


# For each of the given reads files, run the accompanying bash script to perform the alignment.
def trimAdaptorSequences(rawReadsFilePaths: List[str], adapterSequencesFilePath, pairedEndInput = False,
                         threads = 1, legacyTrimming = False):

    trimmingBashScriptFilePath = os.path.join(os.path.dirname(__file__),"TrimAdaptorSequences.bash")

     # If performing paired end alignment, find pairs for all the given raw reads files.
    if pairedEndInput:
        read1FilePaths: List[str] = list(); read2FilePaths: List[str] = list()
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


    for i, rawReadsFilePath in enumerate(rawReadsFilePaths):
        
        # Run the trimming script.
        if pairedEndInput:
            arguments = ["bash", trimmingBashScriptFilePath, "-1", read1FilePaths[i], "-2", read2FilePaths[i]]
        else:
            arguments = ["bash", trimmingBashScriptFilePath, "-1", rawReadsFilePath]
        arguments += ["-t", str(threads)]
        arguments += ["-a", adapterSequencesFilePath]
        if legacyTrimming: arguments += ["--legacy-trimming"]
        subprocess.run(arguments, check = True)


def main():

    with TkinterDialog(workingDirectory = os.getenv("HOME"), title = "Trim Adapter Sequences") as dialog:
        dialog.createMultipleFileSelector("Raw fastq reads:", 0, ".fastq.gz", 
                                          ("Gzipped fastq Files", ".fastq.gz"))
        dialog.createCheckbox("Find paired files", 1, 0)
        dialog.createFileSelector("Adapter Sequences:", 2, ("Fasta Files", ".fa"))
        dialog.createTextField("How many Threads should be used?", 3, 0, defaultText="1")
        dialog.createCheckbox("Use legacy trimming (trimmomatic)", 4, 0)

    # Get the raw reads files, but make sure that no trimmed reads files have tagged along!
    unfilteredRawReadsFilePaths = dialog.selections.getFilePathGroups()[0]
    filteredRawReadsFilePaths = removeTrimmedAndTmp(unfilteredRawReadsFilePaths)

    adapterFilePath = dialog.selections.getIndividualFilePaths()[0]

    pairedEndInput = dialog.selections.getToggleStates()[0]
    legacyTrimming = dialog.selections.getToggleStates()[1]

    threads = checkForNumber(dialog.selections.getTextEntries()[0], True, lambda x:x>0, "Expected a positive-integer number of threads")


    trimAdaptorSequences(filteredRawReadsFilePaths, adapterFilePath,
                         pairedEndInput, threads, legacyTrimming)


if __name__ == "__main__": main()