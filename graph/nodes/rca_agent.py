"""RCA agent node — read-only diagnosis using SSH tools + RAG."""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from langfuse import observe

from config import settings
from graph.state import AgentState, RCAResult
from tools.ssh_tools import SSHClient, set_scenario
from tools import sapcontrol_tools, log_tools
from tools.rag_tools import rag_lookup

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)

_SYNTHESIS_PROMPT = """\
You are an SAP Basis L1 support analyst. Analyze the evidence below and produce
a root-cause analysis.

Alert: {alert}
Host: {host}  SID: {sid}  Instance: {nr}

== Process List ==
{process_list}

== Work Process Table ==
{wp_table}

== Filesystem Usage ==
{df_output}

== Dev Log ==
{dev_log}

== Runbook Matches ==
{rag_matches}

Respond with ONLY a JSON object (no markdown):
{{
  "symptoms": ["<list of observed symptoms>"],
  "root_cause": "<one-sentence root cause>",
  "evidence": ["<list of evidence strings>"],
  "confidence": "high" | "medium" | "low",
  "proposed_fix": "<specific fix action or 'None' if informational only>",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "sap_note_ref": "<SAP Note number or null>"
}}
"""


def _pick_wp_nr(wp_table: list[dict[str, str]], alert: str) -> int:
    """Determine which work process log to read based on WP table and alert."""
    # Check for STOPPED / error work processes first
    for wp in wp_table:
        status = wp.get("Status", "").strip()
        if status in ("STOPPED", "Ended"):
            try:
                return int(wp.get("No", "0").strip())
            except ValueError:
                continue
        err = wp.get("Err", "").strip()
        if err == "X":
            try:
                return int(wp.get("No", "0").strip())
            except ValueError:
                continue
    return 0  # default to dev_w0


@observe(name="rca_diagnosis")
def rca_agent_node(state: AgentState) -> dict:
    """Run root-cause analysis and return an RCAResult."""
    host = state["host"]
    sid = state["sid"]
    nr = state["instance_nr"]
    alert = state["alert"]

    logger.info("[RCA] Starting diagnosis for alert: %s", alert)

    # Set the mock scenario so all tool calls return the right data
    set_scenario(alert)

    with SSHClient(host=host) as ssh:
        # 1. Get process list
        logger.info("[RCA] Calling sapcontrol GetProcessList")
        proc_list = sapcontrol_tools.get_process_list(ssh, nr)

        # 2. Get work process table
        logger.info("[RCA] Calling sapcontrol ABAPGetWPTable")
        wp_table = sapcontrol_tools.get_wp_table(ssh, nr)

        # 3. Get filesystem usage
        logger.info("[RCA] Calling df -h")
        df_output = log_tools.get_filesystem_usage(ssh)

        # 4. Read relevant dev log
        wp_nr = _pick_wp_nr(wp_table, alert)
        logger.info("[RCA] Reading dev_w%d log", wp_nr)
        dev_log = log_tools.read_dev_log(ssh, sid, nr, wp_nr)

        # 5. RAG lookup
        error_summary = f"{alert} — process list: {json.dumps(proc_list)}"
        logger.info("[RCA] RAG lookup for: %s", alert)
        rag_matches = rag_lookup(error_summary, alert=alert)

    # Format evidence for LLM
    rag_text = "\n".join(
        f"- [{m.score:.2f}] {m.title}: {m.content} (SAP Note {m.sap_note})"
        for m in rag_matches
    )

    if settings.demo_mode:
        # Build RCAResult deterministically for demo
        rca = _build_demo_rca(alert, wp_table, dev_log, df_output, rag_matches)
    else:
        prompt = _SYNTHESIS_PROMPT.format(
            alert=alert,
            host=host,
            sid=sid,
            nr=nr,
            process_list=json.dumps(proc_list, indent=2),
            wp_table=json.dumps(wp_table, indent=2),
            df_output=df_output,
            dev_log=dev_log,
            rag_matches=rag_text,
        )
        response = _llm.invoke(prompt)
        try:
            rca = json.loads(response.content)
        except json.JSONDecodeError:
            logger.error("[RCA] Failed to parse LLM response, building fallback")
            rca = _build_demo_rca(alert, wp_table, dev_log, df_output, rag_matches)

    logger.info("[RCA] Diagnosis complete — root cause: %s", rca.get("root_cause", "?"))
    return {"rca_result": rca}


def _build_demo_rca(
    alert: str,
    wp_table: list[dict[str, str]],
    dev_log: str,
    df_output: str,
    rag_matches: list,
) -> RCAResult:
    """Build a deterministic RCAResult for demo scenarios."""
    alert_lower = alert.lower()

    sap_note = rag_matches[0].sap_note if rag_matches else None

    if "wp" in alert_lower or "work proc" in alert_lower:
        return RCAResult(
            symptoms=["WP02 status STOPPED in ABAPGetWPTable", "SIGSEGV in dev_w2"],
            root_cause="Work process 02 crashed with SIGSEGV in function module Z_CUSTOM_FM",
            evidence=[
                "ABAPGetWPTable: WP02 Status=STOPPED, Reason=SIGSEGV",
                "dev_w2: SIGSEGV caught in Z_CUSTOM_FM (program SAPLZ_CUSTOM)",
            ],
            confidence="high",
            proposed_fix="restart_workprocess",
            risk_level="LOW",
            sap_note_ref=sap_note,
        )

    if "filesystem" in alert_lower or "disk" in alert_lower:
        return RCAResult(
            symptoms=["/usr/sap/DEV/work at 94% usage", "8.2GB of old trace files"],
            root_cause="Filesystem /usr/sap/DEV/work nearly full due to unrotated old trace files",
            evidence=[
                "df -h: /usr/sap/DEV/work at 94%",
                "ls -lh: dev_w*.old files from 30+ days ago totalling 8.2GB",
            ],
            confidence="high",
            proposed_fix="cleanup_filesystem",
            risk_level="MEDIUM",
            sap_note_ref=sap_note,
        )

    if "dump" in alert_lower or "abap" in alert_lower:
        return RCAResult(
            symptoms=["TIME_OUT dump in dev_w0", "ZREPORT_HEAVY exceeded runtime"],
            root_cause="ABAP program ZREPORT_HEAVY hit TIME_OUT — long SELECT on VBAK without checkpoint",
            evidence=[
                "dev_w0: TIME_OUT in ZREPORT_HEAVY line 1042",
                "Long running SELECT on table VBAK without proper WHERE clause",
            ],
            confidence="high",
            proposed_fix="None",
            risk_level="LOW",
            sap_note_ref=sap_note,
        )

    if "instance" in alert_lower or "down" in alert_lower:
        return RCAResult(
            symptoms=["Instance DEV/00 status GRAY", "All processes stopped"],
            root_cause="SAP instance is completely down — dispatcher and all processes stopped",
            evidence=[
                "GetSystemInstanceList: DEV/00 dispstatus=GRAY",
                "GetProcessList: dispatcher, IGS, gateway all GRAY/Stopped",
            ],
            confidence="high",
            proposed_fix="escalate",
            risk_level="HIGH",
            sap_note_ref=sap_note,
        )

    # Fallback
    return RCAResult(
        symptoms=["Unknown alert pattern"],
        root_cause=f"Unable to determine root cause for: {alert}",
        evidence=[],
        confidence="low",
        proposed_fix="None",
        risk_level="LOW",
        sap_note_ref=None,
    )
