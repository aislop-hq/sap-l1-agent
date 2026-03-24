"""AgentState, RCAResult, and IncidentReport — central state schema."""

from __future__ import annotations

from typing import Literal, Optional, TypedDict


class RCAResult(TypedDict):
    symptoms: list[str]
    root_cause: str
    evidence: list[str]
    confidence: Literal["high", "medium", "low"]
    proposed_fix: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    sap_note_ref: Optional[str]


class IncidentReport(TypedDict):
    incident_id: str
    host: str
    alert: str
    rca: RCAResult
    action_taken: Optional[str]
    action_result: Optional[str]
    resolved: bool
    escalate: bool


class AgentState(TypedDict):
    # Input
    host: str
    sid: str
    instance_nr: str
    alert: str
    thread_id: str

    # Agent outputs
    rca_result: Optional[RCAResult]
    approval_decision: Optional[str]  # "yes" | "no" | None
    action_result: Optional[str]

    # Control
    next: str  # supervisor routing target
    messages: list  # LangGraph message history
    report: Optional[IncidentReport]
