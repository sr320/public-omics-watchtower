#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { FASTQC } from './modules/qc'
include { SALMON_QUANT } from './modules/salmon'
include { DESEQ2_ANALYSIS } from './modules/deseq2'
include { GO_ENRICHMENT } from './modules/enrichment'
include { RENDER_REPORT } from './modules/reporting'

workflow {
    ch_samples = Channel
        .fromPath(params.samplesheet)
        .splitCsv(header: true)
        .map { row ->
            def sample = [
                id: row.sample_id,
                condition: row.condition ?: 'unknown',
                fastq_1: file(row.fastq_1),
                fastq_2: row.fastq_2 ? file(row.fastq_2) : null
            ]
            return tuple(sample.id, sample)
        }

    ch_fastq = ch_samples.map { id, sample ->
        def reads = sample.fastq_2 ? [sample.fastq_1, sample.fastq_2] : [sample.fastq_1]
        return tuple(id, reads)
    }

    FASTQC(ch_fastq)

    ch_salmon = ch_samples.map { id, sample ->
        def reads = sample.fastq_2 ? [sample.fastq_1, sample.fastq_2] : [sample.fastq_1]
        return tuple(id, reads, sample.condition)
    }

    SALMON_QUANT(ch_salmon, file(params.salmon_index))

    ch_quant = SALMON_QUANT.out.quant
        .collect()
        .map { quant_files ->
            def sample_sheet = quant_files.collect { f ->
                def sample_id = f.baseName.replace('.quant', '')
                return [sample_id: sample_id, quant: f]
            }
            return sample_sheet
        }

    DESEQ2_ANALYSIS(
        ch_quant,
        params.contrast,
        params.min_count,
        params.alpha,
        params.lfc_threshold
    )

    GO_ENRICHMENT(DESEQ2_ANALYSIS.out.deg)

    RENDER_REPORT(
        DESEQ2_ANALYSIS.out.deg,
        DESEQ2_ANALYSIS.out.pca,
        DESEQ2_ANALYSIS.out.volcano,
        GO_ENRICHMENT.out.enrichment,
        params.outdir
    )
}
