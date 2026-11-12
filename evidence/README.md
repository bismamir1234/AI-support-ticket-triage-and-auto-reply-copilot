# Verification Evidence & Test Reports

This folder contains verified, non-fabricated outputs, logs, exports, automated test results, security test reports, and live headless Chrome screenshots generated directly from the **AI Support Ticket Triage & Auto-Reply Copilot** application.

---

## Core Project Update Evidence Files (Tasks 1–6)

| File | Purpose |
|---|---|
| [`test_matrix_10_tickets.csv`](test_matrix_10_tickets.csv) | Complete 10-ticket synthetic evaluation matrix comparing expected vs. actual category, urgency (`P1`/`P2`/`P3` + raw priority), sentiment, entities, missing info, clarification requirement, and Pass/Fail status. |
| [`test_results.json`](test_results.json) | Full JSON records for all 10 live Groq synthetic tickets, 3 adversarial prompt-injection security probes, and the compromised-LLM backend override defense-in-depth test. |
| [`classification_comparison.md`](classification_comparison.md) | Structured expected-vs-actual Markdown table and edge-case classification analysis (sarcasm, mixed refund+technical, prompt injection, incomplete clarification). |
| [`security_test_report.md`](security_test_report.md) | Security and refund policy verification report demonstrating untrusted data framing, prompt injection neutralization, preserved customer classification, and backend deterministic validation. |

---

## Screenshots (`screenshots/`)

### Project Update Verification Screenshots
- `screenshots/15_updated_dashboard.png` — Updated SaaS dashboard with real-time KPIs (`P1 Urgent`), sidebar AI status, and P1/P2/P3 urgency colors.
- `screenshots/16_ticket_inbox_p1_p2_p3.png` — Ticket inbox displaying `P1` (Red), `P2` (Yellow), `P3` (Gray) badges and `Injection Blocked` guardrail badge.
- `screenshots/17_ticket_details_and_ai_analysis.png` — Mixed-category ticket (`T10-007`) details showing original priority (`P1 (high)`), secondary category badges, extracted entities (`ORD-77821`, `500`), and AI analysis.
- `screenshots/18_empty_state.png` — Helpful search/filter empty state with `Clear Search & Filters` recovery action.
- `screenshots/19_input_validation_error.png` — New Ticket modal rejecting empty/whitespace input with character counter (`0 / 10,000 chars`) and inline validation error banner.
- `screenshots/20_api_key_error_state.png` — User-friendly API key authentication failure alert banner & sidebar status indicator (zero secret leakage).
- `screenshots/21_prompt_injection_test_result.png` — Ticket `T10-009` showing `Injection Blocked` badge, neutralized prompt-injection alert, missing `order_id` warning, and policy-compliant response.
- `screenshots/22_generated_customer_response.png` — Policy-grounded customer auto-reply draft with agent edit/regenerate/approve controls.

### Earlier Phase 7 Baseline Screenshots
- `screenshots/01_main_dashboard.png` through `screenshots/14_dark_mode_detail.png` — Baseline dashboard, edit/save, mock approval, resolution, CSV/JSON export, and dark mode captures.

---

## Supporting Artifacts & Exports

- `exports/actual_tickets_export.csv` & `exports/actual_tickets_export.json` — Live SQLite export downloads.
- `classification_logs/actual_classification.log` — Live Groq API classification execution logs.
- `test_results/expected_vs_actual_table.md`, `test_results/five_tickets_comparison.json`, `test_results/pytest_results.txt` — Historical 5-ticket and pytest baselines.

