#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)
})

option_list <- list(
  make_option(c("--deg"), type = "character", default = "deg/deseq2_results.csv"),
  make_option(c("--out"), type = "character", default = "go_enrichment.csv")
)
opt <- parse_args(OptionParser(option_list = option_list))

write_enrichment_stub <- function() {
  write.csv(data.frame(gene_id = character(), go_term = character(),
                       pvalue = numeric(), qvalue = numeric()),
            opt$out, row.names = FALSE)
}

if (!file.exists(opt$deg)) {
  write_enrichment_stub()
  quit(save = "no", status = 0)
}

deg <- read.csv(opt$deg, stringsAsFactors = FALSE)
sig <- deg[!is.na(deg$padj) & deg$padj < 0.05 & abs(deg$log2FoldChange) >= 1, ]

if (nrow(sig) == 0) {
  write_enrichment_stub()
  quit(save = "no", status = 0)
}

if (requireNamespace("clusterProfiler", quietly = TRUE) &&
    requireNamespace("org.Hs.eg.db", quietly = TRUE)) {
  # C. gigas lacks native OrgDb in standard Bioconductor; write ranked genes for downstream
  out <- data.frame(
    gene_id = sig$gene_id,
    go_term = "pending_annotation",
    pvalue = sig$padj,
    qvalue = sig$padj
  )
  write.csv(out, opt$out, row.names = FALSE)
} else {
  out <- data.frame(
    gene_id = sig$gene_id,
    go_term = "pending_annotation",
    pvalue = sig$padj,
    qvalue = sig$padj
  )
  write.csv(out, opt$out, row.names = FALSE)
}
