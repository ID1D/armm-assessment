# ARMM Assessment Tool

A self-assessment web application for evaluating your organisation's AI Security Operations Centre (SOC) maturity using the ARMM (AI Response Maturity Model) framework.

---

## What it is and who it is for

The ARMM Assessment Tool is designed for:

- **Security teams and SOC managers** who want to understand how mature their AI-assisted security operations are.
- **CISOs and security architects** looking to benchmark their AI SOC capabilities against a structured framework.
- **Vendors and consultants** who want to evaluate a client's AI SOC readiness objectively.

No technical knowledge is required to complete the assessment. The questionnaire uses plain English labels and tooltips at every step.

---

## Credits

**Tool built by:**

| Author | GitHub |
|--------|--------|
| Diego Andrade | [@ID1D](https://github.com/ID1D) |

**ARMM framework developed by:**

- **Andrei Cotaie**
- **Cristian Miron**
- **Filip Stojkovski**

---

## Quick Start

1. **Install Flask** (the only external dependency):

   ```
   pip install flask
   ```

2. **Run the application**:

   ```
   python app.py
   ```

3. **Open your browser** and navigate to:

   ```
   http://127.0.0.1:5000
   ```

4. Click **Start Assessment**, complete the questionnaire, and click **Generate Report**.

---

## What the report contains

The generated report includes:

- **Composite Maturity Tier** (Explorer / Entry / Advanced / Expert) based on the ARMM scoring rules.
- **Three summary metrics**: Overall weighted score, capability coverage percentage, and full automation percentage.
- **Domain Breakdown table**: Per-domain scores, coverage, automation, tier, and visual bar chart for Identity, Network, Endpoint, Cloud, SaaS, and General response planes.
- **Recommendations in three categories**:
  - *Quick Wins* — not yet implemented capabilities with low operational risk.
  - *Next Tier Actions* — what is needed to reach the next maturity tier.
  - *Automation Upgrades* — capabilities currently in Collaborative or Guide mode that could be promoted to Approver or fully Automated.
- **Full Capability Detail** — all 80+ actions with their assigned scores, colour-coded by maturity level.
- **Print and Export** — print the report directly from the browser, or export the raw assessment data as a JSON file.

---

## Integration with armm-toolkit and mock-ai-soc

This tool is a standalone self-assessment companion to the broader ARMM ecosystem:

- **armm-toolkit** (`C:\I-DID-LAB\armm-toolkit`): Contains the reference implementation of the ARMM scoring engine, playbooks, and capability definitions. The assessment tool's `scorer.py` and `recommender.py` replicate the core logic independently so that no toolkit dependency is required.
- **mock-ai-soc** (`C:\I-DID-LAB\mock-ai-soc`): A simulated AI SOC environment. Assessment results exported as JSON can be loaded into mock-ai-soc to configure its capability level, or used to validate that mock scenarios match your real-world maturity rating.

To export results for use in mock-ai-soc, click **Export JSON** on the results page. The exported file contains the full scoring breakdown and per-action scores in a structured format.

---

## Directory structure

```
armm-assessment/
├── app.py                  # Flask application, routes
├── assessment/
│   ├── __init__.py
│   ├── capabilities.json   # All 80+ ARMM actions with reference scores
│   ├── scorer.py           # ARMM scoring engine (self-contained)
│   └── recommender.py      # Recommendation generator
├── templates/
│   ├── base.html           # Shared layout, Bootstrap 5 CDN
│   ├── index.html          # Landing page
│   ├── assess.html         # Assessment questionnaire
│   └── results.html        # Report page (printable)
├── requirements.txt        # flask>=3.0
├── README.md
├── CONTEXT.md
└── .gitignore
```
