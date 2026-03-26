"""Langfuse prompt management with hardcoded fallbacks.

Prompts are fetched from Langfuse at runtime (versioned, editable in UI).
If Langfuse is unavailable or the prompt doesn't exist yet, the fallback
string is used — so the system works with or without Langfuse.

Langfuse uses {{variable}} for placeholders (double curly braces).
"""

from __future__ import annotations

import logging

from langfuse import get_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback prompts (used when Langfuse is unavailable)
# ---------------------------------------------------------------------------

SUPERVISOR_ROUTING_FALLBACK = """\
You are the Supervisor of an SAP Basis L1 support agent system.

Current state:
- Alert: {{alert}}
- RCA completed: {{rca_done}}
- RCA result: {{rca_summary}}

Decide the next step. Respond with ONLY a JSON object (no markdown):
{"next": "<target>", "reason": "<short reason>"}

Possible targets:
- "rca_agent"        → run root-cause analysis (use when RCA has not been done yet)
- "human_approval"   → ask operator to approve a fix (use when RCA found a fixable issue with proposed_fix)
- "report"           → go straight to report (use when RCA is informational-only OR the issue requires escalation, i.e. risk_level is HIGH)
"""

RCA_SYNTHESIS_FALLBACK = """\
You are an SAP Basis L1 support analyst. Analyze the evidence below and produce
a root-cause analysis.

Alert: {{alert}}
Host: {{host}}  SID: {{sid}}  Instance: {{nr}}

== Process List ==
{{process_list}}

== Work Process Table ==
{{wp_table}}

== Filesystem Usage ==
{{df_output}}

== Dev Log ==
{{dev_log}}

== Runbook Matches ==
{{rag_matches}}

Respond with ONLY a JSON object (no markdown).

IMPORTANT: Use the runbook match with the highest score to determine the proposed_fix.
- Copy the "action" value from the best-matching runbook into "proposed_fix"
- Copy the "fix_command" value from the best-matching runbook into "fix_command"
- Copy the "verify_command" value from the best-matching runbook into "verify_command"
- If the best runbook has action "none" or "escalate", use that — do NOT invent a fix.
- If no runbook matches well, use proposed_fix="none", fix_command="", verify_command=""

{
  "symptoms": ["<list of observed symptoms>"],
  "root_cause": "<one-sentence root cause>",
  "evidence": ["<list of evidence strings>"],
  "confidence": "high" | "medium" | "low",
  "proposed_fix": "<action from best-matching runbook>",
  "fix_command": "<fix_command from best-matching runbook>",
  "verify_command": "<verify_command from best-matching runbook>",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "sap_note_ref": "<SAP Note number or null>"
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_prompt_text(name: str, variables: dict[str, str]) -> str:
    """Fetch a prompt from Langfuse and compile it with variables.

    Falls back to the hardcoded prompt if Langfuse is unavailable.
    """
    fallbacks = {
        "supervisor_routing": SUPERVISOR_ROUTING_FALLBACK,
        "rca_synthesis": RCA_SYNTHESIS_FALLBACK,
    }

    fallback = fallbacks.get(name, "")

    try:
        client = get_client()
        prompt = client.get_prompt(name, label="production", fallback=fallback)
        compiled = prompt.compile(**variables)
        logger.info("[PROMPTS] Using Langfuse prompt '%s'", name)
        return compiled
    except Exception as exc:
        logger.info("[PROMPTS] Langfuse unavailable for '%s', using fallback: %s", name, exc)
        # Manual compile: replace {{var}} with values
        text = fallback
        for key, val in variables.items():
            text = text.replace("{{" + key + "}}", val)
        return text
