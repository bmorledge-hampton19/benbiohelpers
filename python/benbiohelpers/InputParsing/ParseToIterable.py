import warnings

# Make a function for parsing input in range or list format.
def parseToIterable(input: str, rangeChar = '-', sepChar = ',', castValuesToInt = True):

    # Remove trailing and leading whitespace
    input = input.strip()

    # If there are separator characters in the input, split it into multiple inputs,
    # and recursively perform this function on each, concatenating the results into a single list.
    if sepChar in input:
        return([
            item for inputIterable in input.split(sepChar)
                for item in parseToIterable(inputIterable, rangeChar, sepChar, castValuesToInt)
        ])

    # If there is a range separator in the input (and no separator characters),
    # return a range object as the iterable.
    elif rangeChar in input:
        start, stop = input.split(rangeChar)
        if int(stop) < int(start): warnings.warn(f"Stop comes before start in range {input}.  Range will contain no values.")
        return(range(int(start),int(stop)+1))

    # Otherwise, the input is a single item that just needs to be turned into an iterable and returned.
    # (Unless of course it's empty, in which case an empty list should be returned.)
    else:
        if not input: return([])
        elif castValuesToInt: return([int(input)])
        else: return([input])