"""
Weighted scoring engine for motivated seller detection.

Each indicator has a weight (1–10). A property's score is:
  score = sum(weight * confidence for each indicator) / max_possible * 100

Scores are 0–100. Color bands:
  🔴 80–100  High motivation
  🟠 60–79   Moderate-high
  🟡 40–59   Moderate
  🟢 0–39    Low signals
"""
from dataclasses import dataclass
from app.models.indicator import IndicatorType, IndicatorCategory, INDICATOR_CATEGORIES


INDICATOR_WEIGHTS: dict[IndicatorType, int] = {
    # Financial Distress
    IndicatorType.PRE_FORECLOSURE: 10,
    IndicatorType.TAX_DELINQUENT: 9,
    IndicatorType.ACTIVE_LIEN: 8,
    IndicatorType.BANKRUPTCY_FILING: 8,
    IndicatorType.UTILITY_SHUTOFF: 6,
    IndicatorType.LOW_EQUITY: 5,

    # Legal / Life Events
    IndicatorType.PROBATE_FILING: 9,
    IndicatorType.DIVORCE_FILING: 7,
    IndicatorType.EVICTION_FILING: 7,
    IndicatorType.JOB_RELOCATION: 5,

    # Landlord Pain
    IndicatorType.CODE_VIOLATION: 7,
    IndicatorType.FAILED_INSPECTION: 6,
    IndicatorType.PERMIT_INCOMPLETE: 5,
    IndicatorType.LOW_RENT_VS_MARKET: 4,
    IndicatorType.LANDLORD_MULTI_EVICTION: 6,

    # Market Signals
    IndicatorType.EXPIRED_LISTING: 6,
    IndicatorType.LONG_DOM: 4,
    IndicatorType.PRICE_DROPS: 5,
    IndicatorType.USPS_VACANCY: 6,
    IndicatorType.NO_MAIL_ACTIVITY: 3,

    # Property Condition
    IndicatorType.STREET_VIEW_NEGLECT: 4,
    IndicatorType.LONG_OWNERSHIP_NO_IMPROVEMENTS: 4,
    IndicatorType.ABSENTEE_OWNER: 5,
}

# Category max scores for normalization
CATEGORY_WEIGHTS: dict[IndicatorCategory, list[int]] = {
    cat: [w for t, w in INDICATOR_WEIGHTS.items() if INDICATOR_CATEGORIES.get(t) == cat]
    for cat in IndicatorCategory
}

MAX_POSSIBLE = sum(INDICATOR_WEIGHTS.values())


@dataclass
class ScoreBreakdown:
    total_score: float
    financial_score: float
    legal_score: float
    landlord_score: float
    market_score: float
    condition_score: float
    indicator_count: int


@dataclass
class IndicatorInput:
    indicator_type: IndicatorType
    confidence: float = 1.0


def calculate_score(indicators: list[IndicatorInput]) -> ScoreBreakdown:
    """Calculate weighted motivation score from a list of indicators."""
    if not indicators:
        return ScoreBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    category_totals: dict[IndicatorCategory, float] = {cat: 0.0 for cat in IndicatorCategory}
    category_maxes: dict[IndicatorCategory, float] = {
        cat: sum(CATEGORY_WEIGHTS[cat]) for cat in IndicatorCategory
    }

    total = 0.0
    for ind in indicators:
        weight = INDICATOR_WEIGHTS.get(ind.indicator_type, 0)
        contribution = weight * min(max(ind.confidence, 0.0), 1.0)
        total += contribution
        cat = INDICATOR_CATEGORIES.get(ind.indicator_type)
        if cat:
            category_totals[cat] += contribution

    def _normalize(value: float, max_val: float) -> float:
        if max_val == 0:
            return 0.0
        return round(min(value / max_val * 100, 100), 1)

    return ScoreBreakdown(
        total_score=_normalize(total, MAX_POSSIBLE),
        financial_score=_normalize(
            category_totals[IndicatorCategory.FINANCIAL],
            category_maxes[IndicatorCategory.FINANCIAL],
        ),
        legal_score=_normalize(
            category_totals[IndicatorCategory.LEGAL_LIFE_EVENT],
            category_maxes[IndicatorCategory.LEGAL_LIFE_EVENT],
        ),
        landlord_score=_normalize(
            category_totals[IndicatorCategory.LANDLORD_PAIN],
            category_maxes[IndicatorCategory.LANDLORD_PAIN],
        ),
        market_score=_normalize(
            category_totals[IndicatorCategory.MARKET_SIGNAL],
            category_maxes[IndicatorCategory.MARKET_SIGNAL],
        ),
        condition_score=_normalize(
            category_totals[IndicatorCategory.PROPERTY_CONDITION],
            category_maxes[IndicatorCategory.PROPERTY_CONDITION],
        ),
        indicator_count=len(indicators),
    )


def score_band(total_score: float) -> str:
    """Return a human-readable score band label."""
    if total_score >= 80:
        return "HIGH"
    elif total_score >= 60:
        return "MODERATE_HIGH"
    elif total_score >= 40:
        return "MODERATE"
    else:
        return "LOW"
