from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class FindingType(str, Enum):
    missing_error_path = "missing_error_path"
    missing_auth = "missing_auth"
    interface_mismatch = "interface_mismatch"
    implicit_assumption_violated = "implicit_assumption_violated"
    security = "security"
    logic_error = "logic_error"
    missing_validation = "missing_validation"
    race_condition = "race_condition"
    resource_leak = "resource_leak"
    other = "other"


class Traceability(BaseModel):
    file: str
    line: int | None = None
    git_sha: str | None = None


class Finding(BaseModel):
    finding_id: str = ""
    severity: Severity = Severity.info
    type: FindingType = FindingType.other
    location: str = ""
    description: str = ""
    evidence: str = ""
    traceability: Traceability | None = None


class ImplicitAssumption(BaseModel):
    assumption: str
    confidence: str = "medium"  # "high" | "medium" | "low"
    risk: str = ""              # what breaks if the assumption is violated


class DependencyChange(BaseModel):
    file: str
    changed: str  # ISO date


class FileFindingsReport(BaseModel):
    """Output of a single map agent turn. One per source file."""
    file: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    interfaces_exported: list[str] = Field(default_factory=list)
    interfaces_consumed: list[str] = Field(default_factory=list)
    explicit_requirements: list[str] = Field(default_factory=list)
    implicit_assumptions: list[ImplicitAssumption] = Field(default_factory=list)
    stable_since: str | None = None                              # ISO date from git
    dependencies_changed_since: list[DependencyChange] = Field(default_factory=list)
    cross_file_flags: list[str] = Field(default_factory=list)   # notes for the reduce phase


class Contradiction(BaseModel):
    """A cross-file assumption conflict detected during reduce."""
    severity: Severity = Severity.medium
    file_a: str = ""
    assumption: str = ""       # what file_a assumed
    file_b: str = ""
    actual_behavior: str = ""  # what file_b actually does
    description: str = ""
    finding_ids: list[str] = Field(default_factory=list)


class DirectorySummary(BaseModel):
    """Output of a reduce agent turn. One per directory level."""
    directory: str
    files_reviewed: int
    findings_count: dict[str, int] = Field(default_factory=dict)  # severity -> count
    contradictions: list[Contradiction] = Field(default_factory=list)
    escalated_flags: list[str] = Field(default_factory=list)
    summary: str


class SwapFinding(BaseModel):
    """Agent B finding — spec says X, code does Y."""
    finding_id: str
    severity: Severity
    spec_expectation: str
    observed_behavior: str  # grounded in map phase finding_ids
    map_finding_ids: list[str] = Field(default_factory=list)
    description: str


class SwapReport(BaseModel):
    """Output of the bidirectional swap (Agent B)."""
    spec_files_used: list[str]
    confirmed: list[str]    # behaviors that match spec — free text
    contradictions: list[SwapFinding]
    ambiguous: list[SwapFinding]  # routed to human
    summary: str


class FinalReport(BaseModel):
    """Root output of a full garlicpress run."""
    repo: str
    files_reviewed: int
    map_duration_s: float
    reduce_duration_s: float
    swap_duration_s: float
    findings_by_severity: dict[str, int]
    contradictions: list[Contradiction]
    swap: SwapReport | None = None
    top_findings: list[Finding] = Field(default_factory=list)  # critical + high, sorted
    directory_summaries: list[DirectorySummary] = Field(default_factory=list)
    summary: str


# JSON schema string injected into prompts so agents know exactly what to emit
def findings_json_schema() -> str:
    return FileFindingsReport.model_json_schema().__str__()


def reduce_json_schema() -> str:
    return DirectorySummary.model_json_schema().__str__()


def swap_json_schema() -> str:
    return SwapReport.model_json_schema().__str__()
