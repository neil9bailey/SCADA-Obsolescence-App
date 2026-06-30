from __future__ import annotations

from typing import Protocol


class AssessableAsset(Protocol):
    business_criticality: int
    safety_impact: int
    production_impact: int
    support_status: str
    cyber_exposure: int
    failure_likelihood: int
    spares_risk: int
    recoverability_risk: int
    dependency_complexity: int
    evidence_confidence: str
    delivery_readiness: int
    asset_code: str | None
    system_name: str | None
    site: str | None
    asset_type: str | None
    manufacturer: str | None
    model: str | None
    owner: str | None
    treatment: str | None
    support_end_date: object | None
    process_area: str | None


SUPPORT_RATING = {
    "supported": 1,
    "limited": 3,
    "end_of_support": 5,
    "unknown": 4,
}
CONFIDENCE_PENALTY = {"A": 0, "B": 2, "C": 5, "D": 8}
WEIGHTS = {
    "business_criticality": 15,
    "safety_impact": 10,
    "production_impact": 10,
    "support_status": 20,
    "cyber_exposure": 15,
    "failure_likelihood": 10,
    "spares_risk": 5,
    "recoverability_risk": 10,
    "dependency_complexity": 5,
}


def _normalise(rating: int) -> float:
    return (max(1, min(5, int(rating))) - 1) / 4


def calculate_risk_score(asset: AssessableAsset) -> float:
    score = 0.0
    for field, weight in WEIGHTS.items():
        rating = SUPPORT_RATING.get(asset.support_status, 4) if field == "support_status" else getattr(asset, field)
        score += _normalise(rating) * weight
    score += CONFIDENCE_PENALTY.get(asset.evidence_confidence, 8)
    return round(min(100, score), 1)


def risk_band(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def recommended_wave(score: float, readiness: int) -> str:
    if score >= 60 and readiness <= 2:
        return "Wave 0"
    if score >= 60:
        return "Wave 1"
    if score >= 40:
        return "Wave 2"
    return "Monitor"


def calculate_completeness(asset: AssessableAsset) -> int:
    fields = (
        "asset_code",
        "system_name",
        "site",
        "process_area",
        "asset_type",
        "manufacturer",
        "model",
        "owner",
        "treatment",
        "support_end_date",
    )
    populated = sum(1 for field in fields if getattr(asset, field, None) not in (None, ""))
    return round(populated / len(fields) * 100)


def apply_assessment(asset) -> None:
    asset.risk_score = calculate_risk_score(asset)
    asset.risk_band = risk_band(asset.risk_score)
    asset.recommended_wave = recommended_wave(asset.risk_score, asset.delivery_readiness)
    asset.data_completeness = calculate_completeness(asset)
