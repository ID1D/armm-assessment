"""
ARMM Assessment Tool - Flask web application.
SOC self-assessment tool for evaluating AI SOC capabilities using the ARMM framework.
"""

import os
import json
import datetime
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    Response,
    abort,
)

from assessment.scorer import score_domain, score_all, VALID_SCORES
from assessment.recommender import get_recommendations

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

SECRET_KEY = os.urandom(24)
HOST = "127.0.0.1"
PORT = 5000
EXPORT_FILENAME = "armm_assessment.json"

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Load capabilities once at startup
CAPS_PATH = Path(__file__).parent / "assessment" / "capabilities.json"
with open(CAPS_PATH, encoding="utf-8") as f:
    CAPS_DATA = json.load(f)

DOMAINS = CAPS_DATA["domains"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/assess", methods=["GET"])
def assess():
    today = datetime.date.today().isoformat()
    total_actions = sum(len(d["actions"]) for d in DOMAINS.values())
    return render_template("assess.html", domains=DOMAINS, today=today, total_actions=total_actions)


def _sanitize_company(value: str) -> str:
    """Limit company name to 200 printable characters."""
    cleaned = value.strip()[:200]
    return cleaned or "Unknown Organisation"


def _sanitize_date(value: str) -> str:
    """Accept only valid ISO-8601 dates (YYYY-MM-DD). Fall back to today."""
    cleaned = value.strip()
    try:
        datetime.date.fromisoformat(cleaned)
        return cleaned
    except ValueError:
        return datetime.date.today().isoformat()


@app.after_request
def set_security_headers(response):
    """Add basic security headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'none';"
    )
    return response


@app.route("/assess", methods=["POST"])
def assess_post():
    form = request.form

    company = _sanitize_company(form.get("company", ""))
    date = _sanitize_date(form.get("date", ""))

    # Build per-domain action lists and score them
    domain_results = {}
    for domain_id, domain_data in DOMAINS.items():
        actions_scored = []
        for action in domain_data["actions"]:
            field_name = f"domain_{domain_id}_{action['id']}"
            raw_score = form.get(field_name, "0")
            # Validate — silently default to "0" if invalid
            if raw_score not in VALID_SCORES:
                raw_score = "0"
            actions_scored.append({"id": action["id"], "score": raw_score})

        domain_result = score_domain(actions_scored)
        # Attach the per-action scores so recommender can use them
        domain_result["actions"] = actions_scored
        domain_results[domain_id] = domain_result

    overall = score_all(domain_results)
    recommendations = get_recommendations(overall, CAPS_DATA)

    # Store in session (JSON-serialisable)
    session["assessment"] = {
        "company": company,
        "date": date,
        "overall": overall,
        "recommendations": recommendations,
    }

    return redirect(url_for("results"))


@app.route("/results")
def results():
    data = session.get("assessment")
    if not data:
        return redirect(url_for("assess"))

    overall = data["overall"]

    # Build a score lookup: {domain_id: {action_id: score_str}}
    # Used in results.html to avoid fragile Jinja2 dict-mutation patterns.
    score_maps = {}
    for domain_id, domain_result in overall.get("domains", {}).items():
        score_maps[domain_id] = {a["id"]: a["score"] for a in domain_result.get("actions", [])}

    return render_template(
        "results.html",
        company=data["company"],
        date=data["date"],
        overall=overall,
        recommendations=data["recommendations"],
        domains=DOMAINS,
        score_maps=score_maps,
    )


@app.route("/export")
def export():
    data = session.get("assessment")
    if not data:
        abort(404)

    payload = json.dumps(data, indent=2, ensure_ascii=True)
    return Response(
        payload,
        mimetype="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{EXPORT_FILENAME}"',
            "Content-Type": "application/json",
        },
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("ARMM Assessment Tool starting...")
    print(f"Open your browser at: http://{HOST}:{PORT}")
    app.run(debug=False, host=HOST, port=PORT)
