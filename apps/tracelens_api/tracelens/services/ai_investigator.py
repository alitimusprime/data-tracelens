import json

import httpx

from tracelens.config import Settings
from tracelens.infrastructure.models import IncidentRecord


def deterministic_explanation(incident: IncidentRecord) -> dict:
    root = incident.probable_root_cause
    active_count = len([anomaly for anomaly in incident.anomalies if anomaly.status == "active"])
    facts = (
        f"{active_count} active anomalies are correlated. "
        f"Affected services: {', '.join(incident.affected_services or []) or 'unknown'}. "
        f"Calculated confidence: {incident.confidence:.0%}."
    )
    inference = (
        f"{root.title()} is the leading hypothesis because it has the strongest combined "
        "signal, timing, dependency, and propagation score."
        if root
        else "No root-cause hypothesis currently has enough evidence."
    )
    return {
        "mode": "deterministic",
        "explanation": f"{facts} {inference}",
        "limitations": (
            "This is a probable cause, not proof. Confirm it with the referenced traces and logs."
        ),
        "verified_facts": facts,
    }


async def explain_with_optional_ai(incident: IncidentRecord, settings: Settings) -> dict:
    fallback = deterministic_explanation(incident)
    if (
        settings.ai_provider == "disabled"
        or not settings.ai_base_url
        or not settings.ai_api_key
        or not settings.ai_model
    ):
        return fallback
    evidence = {
        "incident_id": incident.id,
        "summary": incident.summary,
        "root_cause": incident.probable_root_cause,
        "confidence": incident.confidence,
        "score_breakdown": incident.score_breakdown,
        "anomalies": [
            {
                "evidence_id": anomaly.id,
                "service": anomaly.service_name,
                "kind": anomaly.kind,
                "current": anomaly.current_value,
                "baseline": anomaly.baseline_value,
            }
            for anomaly in incident.anomalies
        ],
    }
    prompt = (
        "Explain this incident using only the supplied JSON. Return strict JSON with keys "
        "explanation, evidence_ids, and limitations. evidence_ids must contain only supplied "
        "evidence IDs. Preserve uncertainty and do not add facts.\n" + json.dumps(evidence)
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                json={
                    "model": settings.ai_model,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        valid_evidence = {anomaly.id for anomaly in incident.anomalies}
        cited_evidence = set(result["evidence_ids"])
        if not cited_evidence or not cited_evidence.issubset(valid_evidence):
            raise ValueError("AI response referenced invalid evidence")
        return {
            **fallback,
            "mode": "ai",
            "explanation": str(result["explanation"]),
            "limitations": str(result["limitations"]),
            "cited_evidence_ids": sorted(cited_evidence),
        }
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return {
            **fallback,
            "provider_error": "AI provider unavailable; deterministic fallback used.",
        }
