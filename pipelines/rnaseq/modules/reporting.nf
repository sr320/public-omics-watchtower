process RENDER_REPORT {
    publishDir "${params.outdir}/report", mode: 'copy'

    input:
    path deg_file
    path pca_plot
    path volcano_plot
    path go_file
    val outdir

    output:
    path "study_report.md", emit: report

    script:
    """
    python3 ${projectDir}/bin/render_report.py \\
        --deg ${deg_file} \\
        --pca ${pca_plot} \\
        --volcano ${volcano_plot} \\
        --go ${go_file} \\
        --out study_report.md \\
        --contrast ${params.contrast}
    """
}
