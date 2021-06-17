import subprocess

def bedToFasta(bedFilePath, genomeFilePath, fastaOutputFilePath, 
               incorporateBedName = False, includeStrand = True, verbose = False):
    "Uses bedtools to convert a bed file to fasta format."

    if verbose:
        print("Calling shell subprocess to use bedtools to generate a fasta file from the given bed file...")

    optionalParameters = list()
    if includeStrand: optionalParameters.append("-s")
    if incorporateBedName: optionalParameters.append("-name")

    subprocess.run(("bedtools","getfasta") + tuple(optionalParameters) + ("-fi",genomeFilePath,
                    "-bed",bedFilePath,"-fo",fastaOutputFilePath), check = True)