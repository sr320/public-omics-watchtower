#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(optparse)
  library(DESeq2)
  library(tximport)
})

option_list <- list(
  make_option(c("--quant-dir"), type = "character", default = "quant"),
  make_option(c("--outdir"), type = "character", default = "."),
  make_option(c("--contrast"), type = "character", default = "treatment_vs_control"),
  make_option(c("--min-count"), type = "integer", default = 10),
  make_option(c("--alpha"), type = "double", default = 0.05),
  make_option(c("--lfc"), type = "double", default = 1.0)
)
opt <- parse_args(OptionParser(option_list = option_list))

dir.create(file.path(opt$outdir, "deg"), showWarnings = FALSE, recursive = TRUE)
dir.create(file.path(opt$outdir, "plots"), showWarnings = FALSE, recursive = TRUE)

quant_files <- list.files(opt$`quant-dir`, pattern = "quant.sf$", full.names = TRUE)
if (length(quant_files) < 2) {
  write.csv(data.frame(gene_id = character(), log2FoldChange = numeric(),
                       pvalue = numeric(), padj = numeric()),
            file.path(opt$outdir, "deg", "deseq2_results.csv"), row.names = FALSE)
  png(file.path(opt$outdir, "plots", "pca.png"), width = 800, height = 600)
  plot(1, 1, main = "Insufficient samples for PCA")
  dev.off()
  png(file.path(opt$outdir, "plots", paste0("volcano_", opt$contrast, ".png")),
      width = 800, height = 600)
  plot(1, 1, main = "Insufficient samples for volcano")
  dev.off()
  quit(save = "no", status = 0)
}

sample_ids <- gsub(".quant.sf$", "", basename(quant_files))
conditions <- ifelse(grepl("control|ctrl|mock", sample_ids, ignore.case = TRUE),
                     "control", "treatment")
if (all(conditions == "control") || all(conditions == "treatment")) {
  conditions <- rep(c("control", "treatment"), length.out = length(sample_ids))
}

txi <- tximport(quant_files, type = "salmon", txOut = TRUE)
col_data <- data.frame(condition = factor(conditions), row.names = sample_ids)
dds <- DESeqDataSetFromTximport(txi, colData = col_data, design = ~ condition)
dds <- dds[rowSums(counts(dds)) >= opt$`min-count`, ]
dds <- DESeq(dds)
res <- results(dds, contrast = c("condition", "treatment", "control"),
               alpha = opt$alpha, lfcThreshold = opt$lfc)

res_df <- as.data.frame(res)
res_df$gene_id <- rownames(res_df)
write.csv(res_df, file.path(opt$outdir, "deg", "deseq2_results.csv"), row.names = FALSE)

vsd <- vst(dds, blind = FALSE)
pca_data <- plotPCA(vsd, intgroup = "condition", returnData = TRUE)
png(file.path(opt$outdir, "plots", "pca.png"), width = 800, height = 600)
plot(pca_data$PC1, pca_data$PC2, col = as.numeric(pca_data$condition),
     pch = 19, xlab = "PC1", ylab = "PC2", main = "PCA")
legend("topright", legend = levels(pca_data$condition),
       col = seq_along(levels(pca_data$condition)), pch = 19)
dev.off()

png(file.path(opt$outdir, "plots", paste0("volcano_", opt$contrast, ".png")),
    width = 800, height = 600)
with(res_df, plot(log2FoldChange, -log10(pvalue), pch = 20,
                  main = paste("Volcano:", opt$contrast),
                  xlab = "log2 Fold Change", ylab = "-log10 p-value"))
dev.off()
