"""Basic schema round-trip tests — no API calls required."""

import json
import pytest
from garlicpress.schema import (
    FileFindingsReport,
    Finding,
    FindingType,
    ImplicitAssumption,
    Severity,
    Traceability,
)


def _minimal_report() -> dict:
    return {
        "file": "src/foo.py",
        "summary": "Does foo things.",
        "findings": [],
        "interfaces_exported": ["foo() -> str"],
        "interfaces_consumed": [],
        "explicit_requirements": [],
        "implicit_assumptions": [],
        "stable_since": "2026-01-01",
        "dependencies_changed_since": [],
        "cross_file_flags": [],
    }


def test_minimal_report_roundtrip():
    data = _minimal_report()
    report = FileFindingsReport.model_validate(data)
    assert report.file == "src/foo.py"
    assert report.findings == []
    dumped = json.loads(report.model_dump_json())
    assert dumped["file"] == "src/foo.py"


def test_report_with_finding():
    data = _minimal_report()
    data["findings"] = [
        {
            "finding_id": "foo-001",
            "severity": "high",
            "type": "missing_error_path",
            "location": "foo:L10",
            "description": "No error handling.",
            "evidence": "result = call()",
            "traceability": {"file": "src/foo.py", "line": 10, "git_sha": None},
        }
    ]
    report = FileFindingsReport.model_validate(data)
    assert len(report.findings) == 1
    assert report.findings[0].severity == Severity.high
    assert report.findings[0].type == FindingType.missing_error_path


def test_implicit_assumption_roundtrip():
    data = _minimal_report()
    data["implicit_assumptions"] = [
        {"assumption": "Request is pre-authenticated", "confidence": "high", "risk": "Auth bypass"}
    ]
    report = FileFindingsReport.model_validate(data)
    assert report.implicit_assumptions[0].confidence == "high"


def test_invalid_severity_raises():
    data = _minimal_report()
    data["findings"] = [{
        "finding_id": "foo-001",
        "severity": "not_a_real_severity",
        "type": "other",
        "location": "foo:L1",
        "description": "x",
        "evidence": "x",
        "traceability": {"file": "src/foo.py"},
    }]
    with pytest.raises(Exception):
        FileFindingsReport.model_validate(data)
