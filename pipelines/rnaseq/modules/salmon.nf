process SALMON_QUANT {
    tag "$sample_id"
    publishDir "${params.outdir}/quant", mode: 'copy', pattern: 'quant.sf'

    input:
    tuple val(sample_id), path(reads), val(condition)
    path salmon_index

    output:
    tuple val(sample_id), path('quant.sf'), emit: quant

    script:
    def reads_list = reads instanceof List ? reads : [reads]
    def is_paired = reads_list.size() > 1
    def reads_arg = is_paired
        ? "-1 ${reads_list[0]} -2 ${reads_list[1]}"
        : "-r ${reads_list[0]}"
    def libtype = is_paired ? 'A' : 'U'
    """
    salmon quant -i ${salmon_index} -l ${libtype} ${reads_arg} -o . --validateMappings
    mv quant.sf ${sample_id}.quant.sf 2>/dev/null || true
    cp ${sample_id}.quant.sf quant.sf 2>/dev/null || cp quant.sf quant.sf
    """
}
