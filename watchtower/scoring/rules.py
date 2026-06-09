"""Relevance scoring rules."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from watchtower.discovery.base import DiscoveredRecord


def score_taxonomy_match(record: DiscoveredRecord, expected_taxonomy_id: int, weight: int) -> int:
    if record.taxonomy_id == expected_taxonomy_id:
        return weight
    organism_lower = record.organism.lower()
    if "crassostrea" in organism_lower or "magallana" in organism_lower:
        return weight
    return 0


def score_keywords(
    text: str,
    keywords: list[str],
    max_points: int,
    points_per_match: int,
    max_matches: int,
) -> tuple[int, list[str]]:
    text_lower = text.lower()
    matched: list[str] = []
    for kw in keywords:
        if kw.lower() in text_lower:
            matched.append(kw)
    points = min(len(matched), max_matches) * points_per_match
    return min(points, max_points), matched


def score_sample_count(
    sample_count: int,
    min_samples: int,
    optimal_samples: int,
    max_points: int,
) -> int:
    if sample_count < min_samples:
        return 0
    if sample_count >= optimal_samples:
        return max_points
    ratio = (sample_count - min_samples) / max(optimal_samples - min_samples, 1)
    return int(ratio * max_points)


def score_study_design(text: str, design_keywords: list[str], max_points: int) -> int:
    text_lower = text.lower()
    matches = sum(1 for kw in design_keywords if kw.lower() in text_lower)
    if matches >= 2:
        return max_points
    if matches == 1:
        return max_points // 2
    return 0


def score_recency(publication_date: str | None, recent_years: int, max_points: int) -> int:
    if not publication_date:
        return max_points // 2
    year_match = re.search(r"(20\d{2})", publication_date)
    if not year_match:
        return max_points // 2
    year = int(year_match.group(1))
    current_year = datetime.now().year
    age = current_year - year
    if age <= recent_years:
        return max_points
    if age <= recent_years * 2:
        return max_points // 2
    return max_points // 4


def compute_relevance_score(
    record: DiscoveredRecord,
    species_config: dict[str, Any],
    scoring_config: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    weights = scoring_config.get("weights", {})
    text = f"{record.title} {record.summary}"

    taxonomy_pts = score_taxonomy_match(
        record,
        int(species_config.get("taxonomy_id", 0)),
        int(weights.get("taxonomy_match", 30)),
    )

    kw_cfg = scoring_config.get("keyword_scoring", {})
    keyword_pts, matched_kw = score_keywords(
        text,
        species_config.get("stress_keywords", []),
        int(kw_cfg.get("max_points", 25)),
        int(kw_cfg.get("points_per_match", 5)),
        int(kw_cfg.get("max_matches", 5)),
    )

    sc_cfg = scoring_config.get("sample_count_scoring", {})
    sample_pts = score_sample_count(
        record.sample_count,
        int(sc_cfg.get("min_samples", 3)),
        int(sc_cfg.get("optimal_samples", 12)),
        int(weights.get("sample_count", 15)),
    )

    sd_cfg = scoring_config.get("study_design_keywords", {})
    design_pts = score_study_design(
        text,
        sd_cfg.get("controlled", []),
        int(weights.get("study_design", 15)),
    )

    rec_cfg = scoring_config.get("recency_years", {})
    recency_pts = score_recency(
        record.publication_date,
        int(rec_cfg.get("recent", 3)),
        int(weights.get("recency", 15)),
    )

    total = taxonomy_pts + keyword_pts + sample_pts + design_pts + recency_pts
    breakdown = {
        "taxonomy": taxonomy_pts,
        "keywords": keyword_pts,
        "matched_keywords": matched_kw,
        "sample_count": sample_pts,
        "study_design": design_pts,
        "recency": recency_pts,
        "total": min(total, 100),
    }
    return min(total, 100), breakdown
