Usage
=====

This page provides detailed usage examples for the LineIndex library.

Basic Usage
----------

Initialize a LineIndex object by providing a file path:

.. code-block:: python

   from lineindex import LineIndex
   
   # Create an index for a text file
   db = LineIndex("large_file.txt")

Accessing Lines
--------------

LineIndex supports several ways to access lines in a file:

Single Line Access
~~~~~~~~~~~~~~~~~

Get a single line by its index (0-based):

.. code-block:: python

   # Get the first line (index 0)
   first_line = db[0]
   
   # Get the 1001st line (index 1000)
   line = db[1000]
   
   # Negative indices work too (gets the last line)
   last_line = db[-1]

Slicing
~~~~~~~

Get a range of lines using Python's slice notation:

.. code-block:: python

   # Get lines 10-19 (inclusive-exclusive, like Python lists)
   lines = db[10:20]
   
   # Get every other line from 100-199
   lines = db[100:200:2]
   
   # Get the last 10 lines
   lines = db[-10:]

Parallel Processing
-----------------

For better performance when retrieving many lines, use parallel processing:

.. code-block:: python

   # Get 1000 lines using 4 worker threads
   lines = db.get(1000:2000, workers=4)
   
   # Use all available CPU cores
   lines = db.get(1000:2000, workers=-1)

Working with CSV Files
--------------------

When working with CSV files or other data formats with headers:

.. code-block:: python

   # Create an index with header=True to skip the first line
   db = LineIndex("data.csv", header=True)
   
   # Now db[0] will give you the first data row (not the header)
   first_data_row = db[0]

Compression
----------

LineIndex supports working with compressed files:

.. code-block:: python

   # Create a compressed version of the file
   db = LineIndex("large_file.txt", compress=True)
   
   # This creates large_file.txt.dz (BGZF format)
   # Future accesses will use the compressed file

   # You can then access lines the same way
   line = db[1000]

Performance Considerations
------------------------

- The first time you access a file, LineIndex creates an index file
- Subsequent access to the same file will reuse the index
- Memory usage remains low even for very large files
- For batch operations, using multiple workers can significantly improve performance
- Compression reduces disk usage but may slightly increase access time