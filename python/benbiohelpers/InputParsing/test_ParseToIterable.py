from benbiohelpers.InputParsing.ParseToIterable import parseToIterable
from benbiohelpers.CustomErrors import UserInputError
import pytest

def test_FAIL_invalid_range_start():
    with pytest.raises(UserInputError): parseToIterable("1r-5$2")

def test_FAIL_invalid_range_stop():
    with pytest.raises(UserInputError): parseToIterable("1-5r$2")

def test_FAIL_invalid_range_step():
    with pytest.raises(UserInputError): parseToIterable("1-5$2r")

def test_FAIL_0_step():
    with pytest.raises(UserInputError): parseToIterable("1-5$0")

def test_FAIL_multiple_range_characters():
    with pytest.raises(UserInputError): parseToIterable("1-5-2")

def test_FAIL_invalid_cast():
    with pytest.raises(UserInputError): parseToIterable("Hello, world", castType = int)


def test_default_sep_char():
    assert parseToIterable("a, b, c") == ['a','b','c']

def test_custom_sep_char():
    assert parseToIterable("a* b* c", sepChar = '*') == ['a','b','c']

def test_default_range_char():
    assert parseToIterable("1-4") == range(1,5)

def test_custom_range_char():
    assert parseToIterable("1*4", rangeChar = '*') == range(1,5)

def test_default_step_char():
    assert parseToIterable("3-11$2") == range(3,12,2)

def test_custom_step_char():
    assert parseToIterable("3-11*2", stepChar = '*') == range(3,12,2)


def test_empty_input():
    assert parseToIterable("") == []


def test_int_range_default_step():
    assert parseToIterable("1-3") == range(1,4) # Default step

def test_int_range_positive_step():
    assert parseToIterable("1-3$2") == range(1,4,2) # Positive step

def test_int_range_negative_step():
    assert parseToIterable("3:1$-2", rangeChar = ':') == range(3,0,-2) # Negative step

def test_multiple_int_range():
    assert parseToIterable("3-5,10-20$2") == [3,4,5,10,12,14,16,18,20]

def test_int_range_with_trailing_nothing():
    assert parseToIterable("1-3,") == range(1,4)

def test_float_range_default_step():
    assert parseToIterable("3.5-5.5") == [3.5, 4.5, 5.5] # Default step

def test_float_range_positive_step():
    assert parseToIterable("3-6$0.75") == [3, 3.75, 4.5, 5.25, 6] # Positive step
    assert parseToIterable("3-3$0.75") == [3] # Positive step, single output
    assert parseToIterable("2-0$0.25") == [] # Positive step, empty output

def test_float_range_negative_step():
    assert parseToIterable("5.5:5$-0.25", rangeChar = ':') == [5.5, 5.25, 5] # Negative step 
    assert parseToIterable("4.5:4.5$-64", rangeChar = ':') == [4.5] # Negative step, single output
    assert parseToIterable("4.5:6$-0.5", rangeChar = ':') == [] # Negative step, empty output


def test_the_whole_enchilada():
    iterable = parseToIterable("64.26; 1|3; 4.5 | 3.5 ? -0.5", sepChar = ';', rangeChar = '|', stepChar = '?', castType = float)
    assert iterable == [64.26, 1, 2, 3, 4.5, 4, 3.5]