"""Download staging tests."""

from pathlib import Path

from watchtower.download.staging import infer_condition, write_sample_sheet


def test_infer_condition() -> None:
    assert infer_condition("sample_control_1") == "control"
    assert infer_condition("stress_rep2") == "treatment"
    assert infer_condition("unknown_sample") == "unknown"


def test_write_sample_sheet(tmp_path: Path) -> None:
    samples = [
        {"sample_id": "s1", "fastq_1": "/a/R1.fq", "fastq_2": "/a/R2.fq", "condition": "control"},
        {"sample_id": "s2", "fastq_1": "/b/R1.fq", "fastq_2": "/b/R2.fq", "condition": "treatment"},
    ]
    path = write_sample_sheet(tmp_path / "samplesheet.csv", samples)
    content = path.read_text()
    assert "sample_id" in content
    assert "s1" in content
    assert "control" in content
