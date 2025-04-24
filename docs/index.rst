Welcome to Linex's documentation!
==============================

**Linex** is a Python library for fast line-based random access to large text files.
It provides an efficient way to retrieve specific lines from text files without 
reading the entire file into memory.

.. image:: https://img.shields.io/pypi/v/linex.svg
    :target: https://pypi.org/project/linex/
    :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/linex.svg
    :target: https://pypi.org/project/linex/
    :alt: Python Versions

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

Features
--------

* O(1) random access to any line by number
* Memory-efficient handling of large files via memory mapping
* Optional file compression with BGZF/idzip format
* Parallel line retrieval for batch operations
* Command-line interface for shell script integration

Installation
-----------

You can install Linex via pip:

.. code-block:: bash

   pip install linex

For compression support, install the optional dependencies:

.. code-block:: bash

   pip install linex[compression]

Getting Started
--------------

Here's a simple example of how to use Linex:

.. code-block:: python

   from linex import Linex

   # Create an index for a text file
   db = Linex("large_file.txt")

   # Get a single line
   line = db[1000]  # Get the 1001st line (0-indexed)

   # Get a range of lines
   lines = db[1000:1010]  # Get 10 lines

   # Use parallel processing for better performance
   lines = db.get(1000:2000, workers=-1)  # Use all available cores

Contents
========

.. toctree::
   :maxdepth: 2
   
   installation
   usage
   api
   cli
   examples
   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`