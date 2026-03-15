"""
ARMM Recommender - Generates prioritized recommendations from assessment results.
"""

from .scorer import TIER_ORDER, TIER_THRESHOLDS, SCORE_WEIGHTS

RECOMMENDATION_LIMIT = 10


def get_recommendations(assessment: dict, caps_data: dict) -> dict:
    """
    Generate recommendations based on assessment results.

    Args:
        assessment: output of score_all(), with domain scores and per-action scores.
                    Expected structure:
                    {
                        "composite_tier": str,
                        "domains": {
                            domain_id: {
                                "tier": str,
                                "weighted_score_pct": float,
                                "actions": [{"id": str, "score": str}, ...]
                            }
                        }
                    }
        caps_data: parsed capabilities.json content

    Returns:
        dict with quick_wins, next_tier, automation_upgrades, current_tier, target_tier
    """
    current_tier = assessment.get("composite_tier", "Explorer")
    target_tier = _next_tier(current_tier)

    # Build lookup: domain_id -> {action_id -> ref}
    ref_lookup = {}
    name_lookup = {}
    domain_name_lookup = {}
    for domain_id, domain_data in caps_data.get("domains", {}).items():
        domain_name_lookup[domain_id] = domain_data.get("name", domain_id)
        ref_lookup[domain_id] = {}
        name_lookup[domain_id] = {}
        for action in domain_data.get("actions", []):
            ref_lookup[domain_id][action["id"]] = action.get("ref", {"T": 1, "C": 1, "I": 1})
            name_lookup[domain_id][action["id"]] = action.get("name", action["id"])

    # Build flat list of all action scores from the assessment
    # assessment["domains"][domain_id] has "actions" list added by app.py
    all_actions = []
    for domain_id, domain_result in assessment.get("domains", {}).items():
        for action in domain_result.get("actions", []):
            action_id = action["id"]
            score = action.get("score", "0")
            ref = ref_lookup.get(domain_id, {}).get(action_id, {"T": 1, "C": 1, "I": 1})
            all_actions.append({
                "domain": domain_id,
                "domain_name": domain_name_lookup.get(domain_id, domain_id),
                "action_id": action_id,
                "action_name": name_lookup.get(domain_id, {}).get(action_id, action_id),
                "current_score": score,
                "ref": ref,
            })

    quick_wins = _quick_wins(all_actions)
    next_tier_items = _next_tier_actions(all_actions, assessment, target_tier)
    automation_upgrades = _automation_upgrades(all_actions)

    return {
        "quick_wins": quick_wins[:RECOMMENDATION_LIMIT],
        "next_tier": next_tier_items[:RECOMMENDATION_LIMIT],
        "automation_upgrades": automation_upgrades[:RECOMMENDATION_LIMIT],
        "current_tier": current_tier,
        "target_tier": target_tier,
    }


def _next_tier(current_tier: str) -> str:
    """Return the tier after the current one, or the same if already at top."""
    idx = TIER_ORDER.index(current_tier) if current_tier in TIER_ORDER else 0
    if idx < len(TIER_ORDER) - 1:
        return TIER_ORDER[idx + 1]
    return current_tier


def _level_label(value: int) -> str:
    """Map a 1-3 axis value to Low / Medium / High."""
    if value == 1:
        return "Low"
    elif value == 2:
        return "Medium"
    return "High"


def _quick_wins(all_actions: list) -> list:
    """
    Quick wins: score == "0" and ref I == 1.
    Priority: ref I=1 first (all qualify), then ref C ascending (lowest effort first).
    """
    candidates = [a for a in all_actions if a["current_score"] == "0" and a["ref"]["I"] == 1]
    candidates.sort(key=lambda a: (a["ref"]["C"], a["ref"]["T"]))

    result = []
    for a in candidates:
        result.append({
            "domain": a["domain"],
            "domain_name": a["domain_name"],
            "action_id": a["action_id"],
            "action_name": a["action_name"],
            "current_score": a["current_score"],
            "suggested_score": "1C",
            "reason": "Not yet implemented; low operational risk makes this a safe starting point.",
            "effort": _level_label(a["ref"]["C"]),
            "risk": _level_label(a["ref"]["I"]),
        })
    return result


def _next_tier_actions(all_actions: list, assessment: dict, target_tier: str) -> list:
    """
    Actions that would help qualify more domains for the target tier.
    Focus on domains that are just below the target tier threshold.
    """
    target_threshold = TIER_THRESHOLDS.get(target_tier, 0)

    # Find domains that don't yet qualify for the target tier
    lagging_domains = set()
    for domain_id, domain_result in assessment.get("domains", {}).items():
        if domain_result.get("weighted_score_pct", 0) < target_threshold:
            lagging_domains.add(domain_id)

    if not lagging_domains:
        # All domains qualify — suggest highest-impact unimplemented actions
        candidates = [a for a in all_actions if a["current_score"] in ("0", "1C", "1G")]
    else:
        candidates = [a for a in all_actions if a["domain"] in lagging_domains and a["current_score"] in ("0", "1C", "1G")]

    # Sort by: score weight ascending (prioritize unimplemented), then ref T descending (tactical value)
    candidates.sort(key=lambda a: (SCORE_WEIGHTS.get(a["current_score"], 0), -a["ref"]["T"]))

    result = []
    for a in candidates:
        current_w = SCORE_WEIGHTS.get(a["current_score"], 0)
        if current_w == 0:
            suggested = "1C"
            reason = f"Implementing this capability will increase {a['domain_name']} coverage toward the {target_tier} threshold."
        else:
            suggested = "1A"
            reason = f"Upgrading from {a['current_score']} to Approver mode will boost the weighted score for {a['domain_name']}."

        result.append({
            "domain": a["domain"],
            "domain_name": a["domain_name"],
            "action_id": a["action_id"],
            "action_name": a["action_name"],
            "current_score": a["current_score"],
            "suggested_score": suggested,
            "reason": reason,
            "effort": _level_label(a["ref"]["C"]),
            "risk": _level_label(a["ref"]["I"]),
        })
    return result


def _automation_upgrades(all_actions: list) -> list:
    """
    Automation upgrades: currently 1C or 1G that could be upgraded to 1A or 2.
    Priority: lowest risk (ref I) first, then lowest effort (ref C).
    """
    candidates = [a for a in all_actions if a["current_score"] in ("1C", "1G")]
    candidates.sort(key=lambda a: (a["ref"]["I"], a["ref"]["C"]))

    result = []
    for a in candidates:
        if a["ref"]["I"] == 1:
            suggested = "2"
            reason = "Low operational risk makes full automation safe with appropriate guardrails."
        else:
            suggested = "1A"
            reason = "Moving to Approver mode (AI-prepared, analyst-approved) reduces response time while maintaining oversight."

        result.append({
            "domain": a["domain"],
            "domain_name": a["domain_name"],
            "action_id": a["action_id"],
            "action_name": a["action_name"],
            "current_score": a["current_score"],
            "suggested_score": suggested,
            "reason": reason,
            "effort": _level_label(a["ref"]["C"]),
            "risk": _level_label(a["ref"]["I"]),
        })
    return result
