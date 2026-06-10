"""GEO download helper tests."""

from unittest.mock import MagicMock

from watchtower.download.geo_download import (
    extract_sra_accessions,
    fetch_sra_accessions_for_geo,
    parse_sra_run_accessions_from_summary,
)


def test_extract_sra_accessions_from_text() -> None:
    text = "Linked runs SRR123456 and SRX999 for GSM768505"
    assert extract_sra_accessions("GSE31012", text) == ["SRR123456", "SRX999"]


def test_parse_sra_run_accessions_from_summary() -> None:
    runs = '<Run acc="SRR334321" total_spots="14992508"/>'
    assert parse_sra_run_accessions_from_summary(runs) == ["SRR334321"]


def test_fetch_sra_accessions_for_geo() -> None:
    entrez = MagicMock()
    entrez.esearch.return_value = ["200031012"]
    entrez.elink.return_value = ["107138", "107139"]
    entrez.esummary.return_value = [
        {"runs": '<Run acc="SRR334321" total_spots="1"/>'},
        {"runs": '<Run acc="SRR334322" total_spots="1"/>'},
    ]

    accessions = fetch_sra_accessions_for_geo("GSE31012", entrez=entrez)

    assert accessions == ["SRR334321", "SRR334322"]
    entrez.esearch.assert_called_once_with("gds", "GSE31012 AND gse[entry_type]", retmax=1)
    entrez.elink.assert_called_once_with("gds", "sra", ["200031012"])
