# Benchmarks

## Where LineIndex Fits

| Family                           | Typical access pattern    | Key examples                                                                                                       | Where LineIndex differs                                                  |
| -------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| **Line-based helpers**           | address by *line number*  | `indxr` ([link.springer.com][1]), `random-line-access` ([github.com][2])                                           | LineIndex adds BGZF, NumPy-vectorised batch fetch and threaded slicing   |
| **Generic gzip/BGZF indexers**   | address by *byte offset*  | `indexed_gzip` ([github.com][3]), `zindex` ([github.com][4]), `gztool` ([biostars.org][5])                         | LineIndex hides byte offsets behind Python slices; no C-extension needed |
| **Domain-specific region tools** | address by *semantic key* | Tabix (chrom \:start-end) ([pmc.ncbi.nlm.nih.gov][6], [htslib.org][7]), `pyfaidx` (sequence IDs) ([github.com][8]) | LineIndex is format-agnostic; region look-ups are outside its scope      |

[1]: https://link.springer.com/chapter/10.1007/978-3-031-56069-9_27?utm_source=chatgpt.com "indxr: A Python Library for Indexing File Lines - SpringerLink"
[2]: https://github.com/brycedrennan/random-line-access/blob/master/README.md?utm_source=chatgpt.com "README.md - brycedrennan/random-line-access - GitHub"
[3]: https://github.com/pauldmccarthy/indexed_gzip?utm_source=chatgpt.com "pauldmccarthy/indexed_gzip: Fast random access of gzip ... - GitHub"
[4]: https://github.com/mattgodbolt/zindex?utm_source=chatgpt.com "mattgodbolt/zindex: Create an index on a compressed text file - GitHub"
[5]: https://www.biostars.org/p/9517260/?utm_source=chatgpt.com "Random Access Of Lines In A Compressed File Having A Custom ..."
[6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3042176/?utm_source=chatgpt.com "Tabix: fast retrieval of sequence features from generic TAB-delimited ..."
[7]: https://www.htslib.org/doc/tabix.html?utm_source=chatgpt.com "tabix(1) manual page - Samtools"
[8]: https://github.com/mdshw5/pyfaidx?utm_source=chatgpt.com "mdshw5/pyfaidx: Efficient pythonic random access to fasta ... - GitHub"


## Alternatives overview
| Tool                                                               | Language / CLI       | Compression  | Primary index      | Sweet-spot use-case          | Notes for your README “Alternatives” table            |
| ------------------------------------------------------------------ | -------------------- | ------------ | ------------------ | ---------------------------- | ----------------------------------------------------- |
| **indxr** ([link.springer.com][1])                                 | Python               | none         | every line         | RAM-constrained notebooks    | Pure-Python but no compression; slower for slices     |
| **indexed\_gzip** ([github.com][2])                                | C extension + Python | any GZIP     | byte checkpoints   | NIfTI / neuroimaging         | Requires compiled C; line counting extra step         |
| **zindex** ([github.com][3])                                       | C++ tool             | GZIP         | byte checkpoints   | log forensics                | Excellent for one-off CLI extraction; no Python API   |
| **gztool** ([biostars.org][4])                                     | C CLI                | GZIP         | byte checkpoints   | ad-hoc line fetch            | Good gzip random access, but no persistent index file |
| **rapidgzip / indexed\_bzip2** ([github.com][5], [github.com][6])  | C++/Python           | gzip / bzip2 | byte / block       | multithreaded decompression  | Blazing decompression, but still byte-oriented        |
| **xsv index + slice** ([github.com][7], [news.ycombinator.com][8]) | Rust CLI             | none         | every 1000th line  | CSV analytics                | Limited to CSV; project unmaintained                  |
| **Tabix** ([pmc.ncbi.nlm.nih.gov][9], [htslib.org][10])            | C library + CLI      | BGZF only    | genomic coordinate | FASTA/VCF sub-region queries | Needs sorted, coordinate-aware data; not random‐line  |

[1]: https://link.springer.com/chapter/10.1007/978-3-031-56069-9_27?utm_source=chatgpt.com "indxr: A Python Library for Indexing File Lines - SpringerLink"
[2]: https://github.com/pauldmccarthy/indexed_gzip?utm_source=chatgpt.com "pauldmccarthy/indexed_gzip: Fast random access of gzip ... - GitHub"
[3]: https://github.com/mattgodbolt/zindex?utm_source=chatgpt.com "mattgodbolt/zindex: Create an index on a compressed text file - GitHub"
[4]: https://www.biostars.org/p/9517260/?utm_source=chatgpt.com "Random Access Of Lines In A Compressed File Having A Custom ..."
[5]: https://github.com/mxmlnkn/rapidgzip?utm_source=chatgpt.com "mxmlnkn/rapidgzip: Gzip Decompression and Random ... - GitHub"
[6]: https://github.com/mxmlnkn/indexed_bzip2?utm_source=chatgpt.com "mxmlnkn/indexed_bzip2: Fast parallel random access to bzip2 and ..."
[7]: https://github.com/BurntSushi/xsv?utm_source=chatgpt.com "BurntSushi/xsv: A fast CSV command line toolkit written in Rust."
[8]: https://news.ycombinator.com/item?id=9088805&utm_source=chatgpt.com "XSV – A fast CSV toolkit in Rust | Hacker News"
[9]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3042176/?utm_source=chatgpt.com "Tabix: fast retrieval of sequence features from generic TAB-delimited ..."
[10]: https://www.htslib.org/doc/tabix.html?utm_source=chatgpt.com "tabix(1) manual page - Samtools"
