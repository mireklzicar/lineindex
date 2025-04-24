"""LineIndex - Fast line-based random access for large text files."""

from .lineindex import LineIndex
from . import example
from ._version import __version__

__all__ = ["LineIndex", "example", "__version__"]
