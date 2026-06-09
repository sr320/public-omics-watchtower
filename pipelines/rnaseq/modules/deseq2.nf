process DESEQ2_ANALYSIS {
    publishDir "${params.outdir}", mode: 'copy'

    input:
    val sample_sheet
    val contrast
    val min_count
    val alpha
    val lfc_threshold

    output:
    path "deg/deseq2_results.csv", emit: deg
    path "plots/pca.png", emit: pca
    path "plots/volcano_${contrast}.png", emit: volcano

    script:
    """
    mkdir -p quant deg plots
    # Copy quant files into expected layout
    # sample_sheet is passed as groovy list — write samples for R
    python3 - <<'PY'
import json, os
samples = ${groovy.json.JsonOutput.toJson(sample_sheet)}
for s in samples:
    src = str(s['quant'])
    dst = f"quant/{s['sample_id']}.quant.sf"
    if os.path.exists(src):
        os.makedirs('quant', exist_ok=True)
        if not os.path.exists(dst):
            os.symlink(os.path.abspath(src), dst)
PY

    Rscript ${projectDir}/bin/deseq2_analysis.R \\
        --quant-dir quant \\
        --outdir . \\
        --contrast ${contrast} \\
        --min-count ${min_count} \\
        --alpha ${alpha} \\
        --lfc ${lfc_threshold}
    """
}
