from __future__ import annotations

from typing import Any

RECOMMENDATION_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "id": "booking-clarity",
        "title": "Clarify booking states and confirmation",
        "evidence_ids": ["MIS-002", "MIS-007"],
        "problem_hypothesis": "Booking steps and state changes may not be clear enough for employees to know whether a trip was booked, altered, or missed.",
        "proposed_intervention": "Simplify the booking flow, show the final booking state in a persistent confirmation banner, and add explicit messaging for any changes after selection.",
        "success_metrics": ["Booking completion rate", "Rate of post-booking confirmation reads", "Support tickets mentioning booking confusion"],
        "risks_and_guardrails": "Avoid adding a second confirmation step that creates alert fatigue; keep the final state visible on the trip card and in notifications.",
        "validation_status": "Requires validation",
        "confidence": "Medium",
    },
    {
        "id": "assigned-trip-visibility",
        "title": "Prioritise the employee's assigned trip and communicate location freshness",
        "evidence_ids": ["MIS-003", "MIS-004", "MIS-006"],
        "problem_hypothesis": "Employees may be unable to distinguish the trip assigned to them from multiple nearby vehicles, and stale or delayed location updates may reduce trust.",
        "proposed_intervention": "Highlight the assigned trip card, show a freshness timestamp for vehicle and ETA data, and indicate when map data is stale or delayed.",
        "success_metrics": ["Time to identify assigned vehicle", "Location freshness rate", "ETA discrepancy ticket volume"],
        "risks_and_guardrails": "Do not overstate map precision; show only confident data and explicitly mark stale data when it is older than the expected threshold.",
        "validation_status": "Requires validation",
        "confidence": "Medium",
    },
    {
        "id": "checkin-no-show",
        "title": "Make check-in and no-show outcomes timely, understandable, and contestable",
        "evidence_ids": ["MIS-001", "MIS-007"],
        "problem_hypothesis": "When employees miss check-in windows or are marked no-show, the reason and recourse may not be clear enough to prevent confusion and disputes.",
        "proposed_intervention": "Expose the exact check-in status, give a plain-language reason for a no-show outcome, and offer a fast escalation path for disputed events.",
        "success_metrics": ["No-show dispute rate", "Median time to resolution", "Check-in clarity survey score"],
        "risks_and_guardrails": "Keep the policy explanation factual and action-oriented; do not hard-code legal judgments into the app without operational approval.",
        "validation_status": "Requires validation",
        "confidence": "Medium",
    },
    {
        "id": "exception-notifications",
        "title": "Create actionable exception notifications",
        "evidence_ids": ["MIS-004", "MIS-006"],
        "problem_hypothesis": "When ETA or driver location is off, employees may receive weak or delayed notifications that do not describe what to do next.",
        "proposed_intervention": "Deliver event-based alerts with a short explanation, current status, and the next action (for example, wait, re-check, or contact support).",
        "success_metrics": ["Notification delivery rate", "Time-to-reaction for exceptions", "Rate of actionable notification opens"],
        "risks_and_guardrails": "Do not notify employees for every transient delay; prioritise disruptions that change the trip outcome or required action.",
        "validation_status": "Requires validation",
        "confidence": "Medium",
    },
    {
        "id": "support-evidence-loop",
        "title": "Connect review themes to support tickets and operational evidence",
        "evidence_ids": ["MIS-001", "MIS-002", "MIS-003", "MIS-004", "MIS-005", "MIS-006", "MIS-007"],
        "problem_hypothesis": "Review trends are easiest to act on when tied to the operational signals already available in support and trip telemetry.",
        "proposed_intervention": "Tag support tickets, internal alerts, and incident logs with the same taxonomy used in review analysis so product teams can validate themes quickly.",
        "success_metrics": ["Support-ticket theme coverage", "Recovery time from incident tickets", "Cross-functional review closure rate"],
        "risks_and_guardrails": "Do not treat a review as a bug report without operational validation; map the theme to evidence before a fix is prioritised.",
        "validation_status": "Requires validation",
        "confidence": "Medium",
    },
]


def get_recommendations(df) -> list[dict[str, Any]]:
    available_ids = set(df["evidence_id"].astype(str).str.strip())
    recommendations: list[dict[str, Any]] = []
    for blueprint in RECOMMENDATION_BLUEPRINTS:
        matched_ids = [evidence_id for evidence_id in blueprint["evidence_ids"] if evidence_id in available_ids]
        missing_ids = [evidence_id for evidence_id in blueprint["evidence_ids"] if evidence_id not in available_ids]
        recommendation = dict(blueprint)
        recommendation["matched_evidence_ids"] = matched_ids
        recommendation["pending_evidence_ids"] = missing_ids
        recommendation["evidence_status"] = "Pending verification" if missing_ids else "Mapped to available evidence"
        recommendations.append(recommendation)
    return recommendations
