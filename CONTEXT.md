# CONTEXT.md — Technical Context for AI Assistants

This file describes the architecture and extension points of the ARMM Assessment Tool for the benefit of AI coding assistants working on this codebase.

---

## Architecture Overview

The application is a single-server Flask application with no database. State is stored in Flask's signed client-side session cookie between the POST to `/assess` and the GET to `/results`.

```
Browser  --GET /-->              index.html        (landing page)
Browser  --GET /assess-->        assess.html       (questionnaire form)
Browser  --POST /assess-->       app.py            (scoring + session write)
                 --> redirect --> /results
Browser  --GET /results-->       results.html      (report, reads session)
Browser  --GET /export-->        app.py            (JSON download, reads session)
```

---

## Routes

| Method | Path      | Handler       | Description                                               |
|--------|-----------|---------------|-----------------------------------------------------------|
| GET    | /         | `index()`     | Landing page                                              |
| GET    | /assess   | `assess()`    | Assessment questionnaire (blank form)                     |
| POST   | /assess   | `assess_post()` | Process scores, write session, redirect to /results     |
| GET    | /results  | `results()`   | Read session, render full report                          |
| GET    | /export   | `export()`    | Read session, return JSON attachment                      |

---

## Session Storage

The session key `"assessment"` contains a JSON-serialisable dict:

```python
{
  "company": str,          # HTML-escaped at render time via Jinja2 | e filter
  "date": str,             # ISO date string
  "overall": {             # Output of scorer.score_all()
    "overall_score_pct": float,
    "coverage_pct": float,
    "automation_pct": float,
    "composite_tier": str,
    "domains": {
      domain_id: {
        "weighted_score_pct": float,
        "coverage_pct": float,
        "automation_pct": float,
        "tier": str,
        "total": int,
        "covered": int,
        "automated": int,
        "actions": [{"id": str, "score": str}, ...]   # added by app.py
      }
    }
  },
  "recommendations": {     # Output of recommender.get_recommendations()
    "quick_wins": [...],
    "next_tier": [...],
    "automation_upgrades": [...],
    "current_tier": str,
    "target_tier": str
  }
}
```

Session size: approximately 15-25 KB for a full 80-action assessment. Flask's default cookie limit is 4 KB signed; to support larger payloads you may need server-side sessions (e.g., `flask-session` with filesystem backend). At current scale the data fits within the limit because it is compact JSON.

---

## Scoring Logic (assessment/scorer.py)

### Score weights

| Score | Weight | Meaning                      |
|-------|--------|------------------------------|
| 0     | 0.0    | Not available                |
| 1     | 1.0    | Basic (generic)              |
| 1C    | 0.5    | Collaborative (AI assists)   |
| 1G    | 1.0    | Guide (AI suggests)          |
| 1A    | 1.5    | Approver (AI prepares)       |
| 2     | 2.0    | Fully automated              |

### Domain score formula

```
weighted_score_pct = (sum of weights / (total_actions * 2.0)) * 100
```

### Composite tier gating

Tier requires >= 4 out of 6 domains to meet the tier threshold:

| Tier     | Threshold |
|----------|-----------|
| Explorer | 0%        |
| Entry    | 40%       |
| Advanced | 65%       |
| Expert   | 80%       |

---

## Form Field Names

Each action's radio group is named: `domain_{domain_id}_{action_id}`

Example: `domain_identity_reset_password_std`

Valid values: `0`, `1`, `1C`, `1G`, `1A`, `2`

Invalid values are silently defaulted to `"0"` in `assess_post()`.

---

## Adding a New Domain

1. Add the domain entry to `assessment/capabilities.json` under `"domains"`.
2. The scorer, recommender, and all templates use `domains.items()` dynamically — no template changes required.
3. The composite tier gating uses `max(1, int(num_domains * (4/6)))` — it scales automatically.

---

## Adding a New Score Level

1. Add the new level to `SCORE_WEIGHTS` in `scorer.py`.
2. Add it to `VALID_SCORES`.
3. Add a radio button entry to the `scores` list in `assess.html`.
4. Add a colour-coding case in `results.html`.

---

## Security Notes

- `SECRET_KEY` is generated with `os.urandom(24)` at startup. It rotates on each server restart, invalidating all existing sessions. For production use, persist it in an environment variable.
- All user-supplied strings (company name, date) are rendered via Jinja2's `{{ value | e }}` auto-escaping. Flask templates have auto-escaping enabled by default for `.html` files.
- The export endpoint reads only from the server-side session — no user input is trusted for the export path or content.

---

## Dependencies

- **Flask >= 3.0** (only external dependency)
- **Bootstrap 5.3.3** via CDN (no local assets)
- **Pure Python stdlib** for everything else: `os`, `json`, `datetime`, `pathlib`

No JavaScript libraries beyond Bootstrap's bundle (includes Popper.js for tooltips).
