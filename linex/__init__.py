"""
Linex - Fast line-based random access for large text files.
"""

from .linex import Linex
from . import example

try:
    from ._version import __version__
except ImportError:
    __version__ = '0.1.0'

__all__ = ['Linex', 'example']