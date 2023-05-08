import pytest

from slick.main import slick, main

__author__ = "David M. Rogers"
__copyright__ = "David M. Rogers"
__license__ = "MIT"


def test_slick():
    """API Tests"""
    assert slick(1) == 1
    assert slick(2) == 1
    assert slick(7) == 13
    with pytest.raises(AssertionError):
        slick(-10)


def test_main(capsys):
    """CLI Tests"""
    # capsys is a pytest fixture that allows asserts against stdout/stderr
    # https://docs.pytest.org/en/stable/capture.html
    main(["7"])
    captured = capsys.readouterr()
    assert "The 7-th Fibonacci number is 13" in captured.out
