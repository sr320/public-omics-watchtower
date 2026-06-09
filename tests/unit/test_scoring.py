"""Scoring engine tests."""

from watchtower.config.loader import load_scoring_config, load_species_config
from watchtower.discovery.base import DiscoveredRecord
from watchtower.scoring.ranker import DatasetRanker
from watchtower.scoring.rules import compute_relevance_score


def test_high_relevance_stress_study() -> None:
    species = load_species_config("crassostrea_gigas")
    scoring = load_scoring_config()
    record = DiscoveredRecord(
        source="sra",
        accession="SRR999",
        title="Pacific oyster heat stress RNA-seq under hypoxia",
        organism="Crassostrea gigas",
        taxonomy_id=29159,
        summary="Treatment vs control gill tissue under thermal and hypoxia stress",
        sample_count=12,
        publication_date="2024",
    )
    score, breakdown = compute_relevance_score(record, species, scoring)
    assert score >= 60
    assert breakdown["taxonomy"] > 0
    assert len(breakdown["matched_keywords"]) >= 1


def test_low_relevance_skipped() -> None:
    ranker = DatasetRanker("crassostrea_gigas")
    record = DiscoveredRecord(
        source="sra",
        accession="SRR000",
        title="Unrelated study",
        organism="Homo sapiens",
        taxonomy_id=9606,
        sample_count=1,
    )
    score, _ = ranker.score(record)
    assert ranker.should_skip(score) or score < 60


def test_ranker_creates_download_job() -> None:
    ranker = DatasetRanker("crassostrea_gigas")
    import tempfile
    from pathlib import Path

    from watchtower.db.connection import connect
    from watchtower.db.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        store = Store(connect(Path(tmp) / "t.db"))
        record = DiscoveredRecord(
            source="sra",
            accession="SRR888",
            title="Crassostrea gigas salinity stress RNA-seq treatment control",
            organism="Crassostrea gigas",
            taxonomy_id=29159,
            summary="Ocean acidification and salinity challenge experiment",
            sample_count=8,
            publication_date="2025",
        )
        jobs = ranker.process_records([record], store)
        assert len(jobs) >= 1
        assert jobs[0].job_type == "download"
