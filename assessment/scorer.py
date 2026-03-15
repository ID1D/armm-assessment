"""
ARMM Scorer - Self-contained scoring engine for the ARMM framework.
No dependency on armm-toolkit.
"""

SCORE_WEIGHTS = {"0": 0.0, "1": 1.0, "1C": 0.5, "1G": 1.0, "1A": 1.5, "2": 2.0}
VALID_SCORES = set(SCORE_WEIGHTS.keys())

TIER_ORDER = ["Explorer", "Entry", "Advanced", "Expert"]
TIER_THRESHOLDS = {"Explorer": 0, "Entry": 40, "Advanced": 65, "Expert": 80}

MAX_WEIGHT = SCORE_WEIGHTS["2"]  # 2.0


def score_domain(actions: list) -> dict:
    """
    Score a single domain.

    Args:
        actions: list of dicts with keys "id" and "score" (e.g. "1A", "0", "2")

    Returns:
        dict with:
            weighted_score_pct  - 0-100, weighted score as % of max possible
            coverage_pct        - % of actions with score > 0
            automation_pct      - % of actions with score == "2"
            tier                - tier name string
            total               - total number of actions
            covered             - number of actions with score > 0
            automated           - number of actions with score == "2"
    """
    if not actions:
        return {
            "weighted_score_pct": 0.0,
            "coverage_pct": 0.0,
            "automation_pct": 0.0,
            "tier": "Explorer",
            "total": 0,
            "covered": 0,
            "automated": 0,
        }

    total = len(actions)
    covered = 0
    automated = 0
    weighted_sum = 0.0
    max_possible = total * MAX_WEIGHT

    for action in actions:
        raw = action.get("score", "0")
        if raw not in VALID_SCORES:
            raw = "0"
        w = SCORE_WEIGHTS[raw]
        weighted_sum += w
        if w > 0:
            covered += 1
        if raw == "2":
            automated += 1

    weighted_score_pct = round((weighted_sum / max_possible) * 100, 1) if max_possible > 0 else 0.0
    coverage_pct = round((covered / total) * 100, 1) if total > 0 else 0.0
    automation_pct = round((automated / total) * 100, 1) if total > 0 else 0.0

    tier = _calculate_tier(weighted_score_pct)

    return {
        "weighted_score_pct": weighted_score_pct,
        "coverage_pct": coverage_pct,
        "automation_pct": automation_pct,
        "tier": tier,
        "total": total,
        "covered": covered,
        "automated": automated,
    }


def _calculate_tier(score_pct: float) -> str:
    """Return the tier name for a given score percentage."""
    tier = "Explorer"
    for t in TIER_ORDER:
        if score_pct >= TIER_THRESHOLDS[t]:
            tier = t
    return tier


def score_all(domain_scores: dict) -> dict:
    """
    Aggregate scores across all domains.

    Args:
        domain_scores: dict mapping domain_id -> domain_result (output of score_domain)

    Returns:
        dict with:
            overall_score_pct   - weighted average across all domains
            coverage_pct        - overall coverage
            automation_pct      - overall automation
            composite_tier      - highest tier where >= 4/6 planes qualify
            domains             - copy of input domain_scores
    """
    if not domain_scores:
        return {
            "overall_score_pct": 0.0,
            "coverage_pct": 0.0,
            "automation_pct": 0.0,
            "composite_tier": "Explorer",
            "domains": {},
        }

    total_actions = sum(d["total"] for d in domain_scores.values())
    total_covered = sum(d["covered"] for d in domain_scores.values())
    total_automated = sum(d["automated"] for d in domain_scores.values())

    # Weighted average: weight each domain by its number of actions
    if total_actions > 0:
        overall_score_pct = round(
            sum(d["weighted_score_pct"] * d["total"] for d in domain_scores.values()) / total_actions,
            1,
        )
        coverage_pct = round((total_covered / total_actions) * 100, 1)
        automation_pct = round((total_automated / total_actions) * 100, 1)
    else:
        overall_score_pct = 0.0
        coverage_pct = 0.0
        automation_pct = 0.0

    composite_tier = _composite_tier(domain_scores)

    return {
        "overall_score_pct": overall_score_pct,
        "coverage_pct": coverage_pct,
        "automation_pct": automation_pct,
        "composite_tier": composite_tier,
        "domains": domain_scores,
    }


def _composite_tier(domain_scores: dict) -> str:
    """
    Composite tier uses sequential gating:
    Highest tier where at least 4 out of 6 domains qualify at that tier level.
    """
    num_domains = len(domain_scores)
    required = max(1, int(num_domains * (4 / 6)))  # 4 out of 6 => 66%

    composite = "Explorer"
    for tier in TIER_ORDER:
        threshold = TIER_THRESHOLDS[tier]
        qualifying = sum(
            1 for d in domain_scores.values() if d["weighted_score_pct"] >= threshold
        )
        if qualifying >= required:
            composite = tier

    return composite
