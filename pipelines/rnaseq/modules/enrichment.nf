process GO_ENRICHMENT {
    publishDir "${params.outdir}/enrichment", mode: 'copy'

    input:
    path deg_file

    output:
    path "go_enrichment.csv", emit: enrichment

    script:
    """
    Rscript ${projectDir}/bin/go_enrichment.R \\
        --deg ${deg_file} \\
        --out go_enrichment.csv || echo "gene_id,go_term,pvalue" > go_enrichment.csv
    """
}
