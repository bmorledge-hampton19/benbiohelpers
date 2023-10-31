#!/bin/bash
# This script takes a gzipped fastq file and a file of adapater sequences to trim and uses them to run trimmomatic
# and trim the adaptor sequences off of the reads.

# Get trimmomatic's jar path.
trimmomaticPath=$(dpkg -L trimmomatic | grep .jar$ | head -1)

while [[ $# > 0 ]]; do
  case $1 in
    -1|--read-file-1)
      inputReads1="$2"
      shift
      shift
      ;;
    -2|--read-file-2)
      inputReads2="$2"
      shift
      shift
      ;;
    -a|--adapterFile)
      adapterFile="$2"
      shift
      shift
      ;;
    -t|--threads)
      threads="$2"
      shift
      shift
      ;;
    --legacy-trimming)
      legacyTrimming=true
      shift
      ;;
    -*|--*)
      echo "Unknown option: $1"
      exit 1
      ;;
    *)
      echo "Unexpected positional argument: $1"
      shift
      ;;
  esac
done

# Determine whether the file is gzipped or not and set the dataName variable accordingly.
dataDirectory=${inputReads1%/*}
dataName=${inputReads1##*/}
if [[ $inputReads1 == *\.fastq ]]
then
    echo "fastq given."
    dataName=${dataName%.fastq}
elif [[ $inputReads1 == *\.fastq\.gz ]]
then
    echo "gzipped fastq given."
    dataName=${dataName%.fastq.gz}
else
    echo "Error: given file: $inputReads1 is not a fastq file or a gzipped fastq file."
    exit 1
fi

# Don't forget to trim the read identifier off of the data name if the data is paired-end.
if [[ ! -z "$inputReads2" ]]
then
    if [[ $dataName == *_R1 ]]
    then
        dataName=${dataName%_R1}
    else
        dataName=${dataName%_1}
    fi
fi

if [[ -z "$inputReads2" ]]
then
    echo "Working with $inputReads1"
else
    echo "Working with $inputReads1 and $inputReads2"
fi

# Create the the trimmed output file(s).
trimmedFastq="$dataDirectory/${dataName}_trimmed.fastq.gz"
if [[ ! -z "$inputReads2" ]]
then
    trimmedFastqP1="$dataDirectory/${dataName}_trimmed_1P.fastq.gz"
    trimmedFastqP2="$dataDirectory/${dataName}_trimmed_2P.fastq.gz"
fi

# Trim the data
if [[ -z "$inputReads2" ]]
then
    if [[ "$legacyTrimming" == true ]]
    then
        echo "Trimming adapters using trimmomatic..."
        java -jar $trimmomaticPath SE -threads $threads $inputReads1 $trimmedFastq "ILLUMINACLIP:$adapterFile:2:30:10"
    else
        echo "Trimming adapters using bbduk..."
        bbduk.sh in=$inputReads1 out=$trimmedFastq ref=$adapterFile ktrim=r k=23 mink=16 hdist=2 threads=$threads
    fi
else
    if [[ "$legacyTrimming" == true ]]
    then
        echo "Trimming adapters using trimmomatic..."
        java -jar $trimmomaticPath PE -threads $threads $inputReads1 $inputReads2 \
        -baseout $trimmedFastq "ILLUMINACLIP:$adapterFile:2:30:10"
    else
        echo "Trimming adapters using bbduk..."
        bbduk.sh in=$inputReads1 in2=$inputReads2 out=$trimmedFastqP1 out2=$trimmedFastqP2 \
        ref=$adapterFile ktrim=r k=23 mink=16 hdist=2 threads=$threads tpe tbo
    fi
fi
