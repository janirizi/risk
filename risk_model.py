"""Risk scoring and failure-analysis engine for IT projects.

This module intentionally avoids heavy ML dependencies so the app can run with
only Streamlit, pandas and matplotlib.  It uses a transparent weighted model,
which is better for academic/project demonstrations because every score is
explainable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class RiskInput:
    probability: float          # 1-5
    impact: float               # 1-5
    exposure: float             # 1-5, how exposed the project is
    detectability: float        # 1-5, lower is easier to detect
    control_strength: float     # 1-5, higher means stronger controls
    weight: float = 1.0         # business priority multiplier


@dataclass(frozen=True)
class FailureSignals:
    schedule_slippage: float        # percentage, e.g. 18
    budget_variance: float          # percentage, e.g. 12
    scope_creep: float              # 1-5
    requirement_volatility: float   # 1-5
    technical_complexity: float     # 1-5
    team_turnover: float            # 1-5
    stakeholder_engagement: float   # 1-5, higher is better
    vendor_dependency: float        # 1-5


RISK_LEVELS: List[Tuple[int, str]] = [
    (75, "Critical"),
    (55, "High"),
    (35, "Medium"),
    (0, "Low"),
]


CATEGORY_RECOMMENDATIONS: Dict[str, List[str]] = {
    "Schedule": [
        "Re-baseline the schedule and split delayed milestones into weekly checkpoints.",
        "Add dependency tracking for critical-path tasks.",
        "Introduce daily blockers review for the delivery team.",
    ],
    "Budget": [
        "Freeze non-essential scope until the budget variance is under control.",
        "Create a variance log and require approval for new cost items.",
        "Move high-cost features into a separate release phase.",
    ],
    "Scope": [
        "Create a formal change-control board for new requirements.",
        "Score every change request by value, cost and risk before approval.",
        "Define a non-negotiable MVP boundary with stakeholders.",
    ],
    "Requirements": [
        "Run requirement validation workshops with end users.",
        "Convert vague requirements into acceptance criteria.",
        "Maintain a traceability matrix from requirement to test case.",
    ],
    "Technical": [
        "Run a proof of concept for the riskiest technical component.",
        "Add architecture review gates before implementation.",
        "Reduce technical uncertainty by documenting integration assumptions.",
    ],
    "People": [
        "Create backup ownership for critical modules.",
        "Document key processes and handover notes.",
        "Reduce single-person dependency through pair reviews.",
    ],
    "Stakeholder": [
        "Schedule weekly stakeholder demos and decision checkpoints.",
        "Create a communication matrix with escalation paths.",
        "Track unresolved stakeholder decisions as project risks.",
    ],
    "Vendor": [
        "Define vendor SLAs and escalation contacts.",
        "Create a fallback plan for delayed vendor deliverables.",
        "Track vendor dependency as a separate risk item.",
    ],
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def calculate_risk(input_data: RiskInput) -> Dict[str, object]:
    """Calculate a normalized risk score with an explainable formula.

    Formula idea:
    - Probability and impact create core severity.
    - Exposure and detectability increase risk.
    - Strong controls reduce the final score.
    - Weight allows business-critical risks to receive higher priority.
    """
    p = clamp(input_data.probability, 1, 5)
    i = clamp(input_data.impact, 1, 5)
    e = clamp(input_data.exposure, 1, 5)
    d = clamp(input_data.detectability, 1, 5)
    c = clamp(input_data.control_strength, 1, 5)
    w = clamp(input_data.weight, 0.5, 2.0)

    raw_score = (p * i * e * d * w) / c
    normalized_score = round(clamp((raw_score / 125) * 100, 0, 100), 2)
    level = risk_level(normalized_score)

    return {
        "score": normalized_score,
        "level": level,
        "priority": priority_label(normalized_score),
        "formula": "((probability × impact × exposure × detectability × weight) / control_strength) normalized to 100",
    }


def risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return "Low"


def priority_label(score: float) -> str:
    if score >= 75:
        return "Immediate escalation"
    if score >= 55:
        return "Management attention"
    if score >= 35:
        return "Monitor and mitigate"
    return "Acceptable with routine review"


def failure_probability(signals: FailureSignals) -> Dict[str, object]:
    """Predict project failure likelihood using weighted delivery signals."""
    schedule = clamp(signals.schedule_slippage / 40 * 100, 0, 100)
    budget = clamp(signals.budget_variance / 35 * 100, 0, 100)
    scope = clamp((signals.scope_creep - 1) / 4 * 100, 0, 100)
    req = clamp((signals.requirement_volatility - 1) / 4 * 100, 0, 100)
    tech = clamp((signals.technical_complexity - 1) / 4 * 100, 0, 100)
    people = clamp((signals.team_turnover - 1) / 4 * 100, 0, 100)
    stakeholder = clamp((5 - signals.stakeholder_engagement) / 4 * 100, 0, 100)
    vendor = clamp((signals.vendor_dependency - 1) / 4 * 100, 0, 100)

    weighted_components = {
        "Schedule": schedule * 0.18,
        "Budget": budget * 0.16,
        "Scope": scope * 0.16,
        "Requirements": req * 0.14,
        "Technical": tech * 0.13,
        "People": people * 0.09,
        "Stakeholder": stakeholder * 0.09,
        "Vendor": vendor * 0.05,
    }

    probability = round(sum(weighted_components.values()), 2)
    top_drivers = sorted(weighted_components.items(), key=lambda item: item[1], reverse=True)[:3]

    return {
        "failure_probability": probability,
        "status": project_status(probability),
        "drivers": [{"category": k, "contribution": round(v, 2)} for k, v in top_drivers],
        "recommendations": build_recommendations([k for k, _ in top_drivers]),
    }


def project_status(probability: float) -> str:
    if probability >= 70:
        return "Failing / urgent intervention needed"
    if probability >= 50:
        return "At serious risk"
    if probability >= 30:
        return "Warning zone"
    return "Stable"


def build_recommendations(categories: List[str]) -> List[str]:
    recommendations: List[str] = []
    for category in categories:
        recommendations.extend(CATEGORY_RECOMMENDATIONS.get(category, [])[:2])
    return recommendations[:6]
