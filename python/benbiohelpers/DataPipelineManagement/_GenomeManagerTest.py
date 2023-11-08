# This script is used to test the genome manager and also provides a way to easily add new genomes.
from benbiohelpers.TkWrappers.TkinterDialog import TkinterDialog
from benbiohelpers.DataPipelineManagement.GenomeManager import getGenomeFastaFilePath, getIndexPathPrefix

with TkinterDialog() as genomeTestDialog: genomeTestDialog.createGenomeSelector(0, 0)

print(genomeTestDialog.selections.getGenomes()[0])
print(genomeTestDialog.selections.getGenomes(returnType = "fasta")[0])
print(genomeTestDialog.selections.getGenomes(returnType="btindex")[0])