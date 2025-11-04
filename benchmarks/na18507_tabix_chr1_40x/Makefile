# Simple orchestrator
.PHONY: all runlist download hg18 align merge chr1 downsample clean

all: runlist download hg18 align merge chr1 downsample

runlist:
	bash scripts/ena_make_runlist.sh

download:
	bash scripts/ena_download_fastqs.sh

hg18:
	bash scripts/get_hg18.sh

align:
	bash scripts/align_bwa_hg18.sh

merge:
	bash scripts/merge_markdup.sh

chr1:
	bash scripts/make_chr1.sh

downsample:
	TARGET=40 bash scripts/downsample_chr1_40x.sh

clean:
	rm -rf work/fastq work/aln work/out work/ref
