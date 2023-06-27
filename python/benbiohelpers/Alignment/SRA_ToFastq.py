# This script takes a list of SRA run accession IDs and corresponding names 
# (both formatted as simple newline-separated text files),
# and uses sra-tools to download and convert the reads to fastq.gz format.

import os, subprocess, time, shutil
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.FileSystemHandling.DirectoryHandling import checkDirs

# Given a file path to a list of run accession IDs and an optional file path to their corresponding names,
# uses sra-tools to retrieve the fastq sequences.
def sRA_ToFastq(runAccessionIDsFilePath, getNamesFromCol2 = False):
    
    startTime = time.time()
    gzippedFastqFiles = list()
    with open(runAccessionIDsFilePath, 'r') as runAccessionIDsFile:
        for line in runAccessionIDsFile:

            # Retrieve the accession ID and name from the current line.
            if getNamesFromCol2:
                runAccessionID, name = line.strip().split('\t')
            else:
                runAccessionID = line.strip().split('\t')[0]
                name = runAccessionID

            print(f"\nRetrieving reads for {runAccessionID}")
            

            # Generate the paths for output.
            alignmentFilesDir = os.path.join(os.path.dirname(runAccessionIDsFilePath), name, "alignment_files")
            checkDirs(alignmentFilesDir)
            fastqOutputFilePath = os.path.join(alignmentFilesDir, name + ".fastq")

            # Run prefetch.
            prefetchStartTime = time.time()
            print("\nRunning prefetch...")
            subprocess.check_call(("prefetch", "-p", "-O", alignmentFilesDir, runAccessionID))
            print(f"Time to fetch: {time.time() - prefetchStartTime} seconds")

            # Run fasterqdump.
            fasterqDumpStartTime = time.time()
            print("\nRunning fasterq-dump...")
            subprocess.check_call(("fasterq-dump", "-p", "-o", fastqOutputFilePath, runAccessionID), cwd = alignmentFilesDir)
            print(f"Time to retrieve fastq: {time.time() - fasterqDumpStartTime} seconds")

            # gzip the results.
            print("\ngzipping results...")
            gzipStartTime = time.time()
            for item in os.listdir(alignmentFilesDir):
                if item.endswith(".fastq"): 
                    print(f"gzipping {item}")
                    subprocess.check_call(("gzip", "-f", os.path.join(alignmentFilesDir, item)))
                    gzippedFastqFiles.append(os.path.join(alignmentFilesDir, item+".gz"))
            print(f"Time to gzip files: {time.time() - gzipStartTime} seconds")

            # Delete prefetched directory
            print("\nDeleting prefetched directory...")
            shutil.rmtree(os.path.join(alignmentFilesDir,runAccessionID))

            print(f"**Total time so far: {time.time() - startTime} seconds**")

    return gzippedFastqFiles


def main():

    # Create the UI.
    with TkinterDialog(title = "SRA to Fastq") as dialog:
        dialog.createFileSelector("SRA run accession IDs:", 0, ("text file",".txt"), ("Tab separated values file", ".tsv"))
        dialog.createCheckbox("Get names from second column in file (tab-separated).", 1, 0)

    sRA_ToFastq(dialog.selections.getIndividualFilePaths()[0], dialog.selections.getToggleStates()[0])
    

if __name__ == "__main__": main()