process FASTQC {
    tag "$sample_id"
    publishDir "${params.outdir}/qc", mode: 'copy'

    input:
    tuple val(sample_id), path(reads)

    output:
    path "*_fastqc.zip", optional: true
    path "*_fastqc.html", optional: true

    script:
    def reads_arg = reads instanceof List ? reads.join(' ') : reads
    """
    fastqc -o . ${reads_arg} || echo "fastqc skipped"
    """
}
