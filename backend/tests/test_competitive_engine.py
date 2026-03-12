from __future__ import annotations

from app.services.competitive_engine import evaluate_phase_scope, list_roadmap_objectives


def test_list_roadmap_objectives_includes_top_priorities() -> None:
    data = list_roadmap_objectives()
    assert data["count"] == 10
    assert {"O1", "O3", "O4", "O5", "O6", "O8"}.issubset(set(data["top_priority_objective_ids"]))


def test_evaluate_phase_scope_pass_with_aligned_deliverables() -> None:
    result = evaluate_phase_scope(
        ["O1", "O3"],
        [
            "exploit path simulation engine",
            "detection rule tuning copilot with coverage validation",
        ],
    )
    assert result["scope_pass"] is True
    assert result["scope_status"] == "in_scope"


def test_evaluate_phase_scope_rejects_unknown_objectives() -> None:
    result = evaluate_phase_scope(["O1", "OX"], ["exploit path"])
    assert result["scope_pass"] is False
    assert result["scope_status"] == "out_of_scope"
    assert "OX" in result["unknown_objectives"]

