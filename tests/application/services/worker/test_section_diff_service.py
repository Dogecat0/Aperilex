"""Unit tests for `SectionDiffService` diff computation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from src.application.interfaces.query_services import AnalysisQueryResult
from src.application.services.worker.section_diff_service import SectionDiffService
from src.shared.enums import (
    AnalysisStatus,
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
)
from src.shared.models import TaskData
from src.shared.types import AnalysisId, FilingId, UserId


class _StubAnalysisQueryService:
    def __init__(self, result: AnalysisQueryResult | None) -> None:
        self._result = result
        self.calls: list[tuple[str, FilingType, datetime]] = []

    async def get_latest_completed(
        self,
        cik: str,
        filing_type: FilingType,
        before_date: datetime,
    ) -> AnalysisQueryResult | None:
        self.calls.append((cik, filing_type, before_date))
        return self._result


class _StubStorageProvider:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.requests: list[str] = []

    async def get_analysis(self, analysis_id: AnalysisId) -> Any:
        self.requests.append(str(analysis_id))
        data = json.dumps(self._payload).encode("utf-8")
        return SimpleNamespace(data=data)


def _make_task_data(**overrides: Any) -> TaskData:
    defaults: dict[str, Any] = {
        "task_id": uuid.uuid4(),
        "filing_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "email": {"value": "analyst@example.com"},
        "user_tier": UserTier.BASIC,
        "ticker": {"value": "APRX"},
        "filing_type": FilingType.FORM_10K,
        "priority": TaskPriority.NORMAL,
        "status": TaskStatus.PENDING,
        "retry_count": 0,
        "max_retries": 3,
        "deduplication_id": "dedupe",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "metadata": {
            "company_cik": "0000000001",
            "filing_date": "2025-04-01",
        },
    }
    defaults.update(overrides)
    return TaskData.model_validate(defaults)


def _make_analysis_query_result() -> AnalysisQueryResult:
    return AnalysisQueryResult(
        analysis_id=AnalysisId(uuid.uuid4()),
        filing_id=FilingId(uuid.uuid4()),
        user_id=UserId(uuid.uuid4()),
        status=AnalysisStatus.COMPLETED,
        analysis_type="COMPREHENSIVE",
        created_at=datetime(2024, 12, 1, tzinfo=UTC),
        updated_at=datetime(2024, 12, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_compute_diffs_detects_new_highlight_and_sentiment_drop() -> None:
    previous_payload = {
        "full_results": {
            "structured_data": {
                "section_analyses": [
                    {
                        "section_name": "Item 1A - Risk Factors",
                        "overall_sentiment": 0.15,
                    }
                ],
                "section_walkthroughs": {
                    "Item 1A - Risk Factors": {
                        "highlights": [
                            {
                                "id": "highlight-regulator-focus",
                                "title": "Regulators intensify enforcement",
                                "summary": "Summary text",
                                "severity": "High",
                                "source_reference": "Item 1A - Risk Factors ¶4",
                                "lesson_reference": {
                                    "lesson_id": "lesson-risk-regulator",
                                    "learning_module_key": "risk_mastery",
                                    "module_stage": "walkthrough",
                                },
                            }
                        ],
                    }
                },
            }
        }
    }

    structured_payload = {
        "section_analyses": [
            {
                "section_name": "Item 1A - Risk Factors",
                "overall_sentiment": -0.2,
            }
        ],
        "section_walkthroughs": {
            "Item 1A - Risk Factors": {
                "highlights": [
                    {
                        "id": "highlight-regulator-focus",
                        "title": "Regulators intensify enforcement",
                        "summary": "Summary text",
                        "severity": "High",
                        "source_reference": "Item 1A - Risk Factors ¶4",
                        "lesson_reference": {
                            "lesson_id": "lesson-risk-regulator",
                            "learning_module_key": "risk_mastery",
                            "module_stage": "walkthrough",
                        },
                    },
                    {
                        "id": "highlight-new-litigation",
                        "title": "New litigation risk emerges",
                        "summary": "Fresh antitrust suits are referenced in the latest filing.",
                        "severity": "Critical",
                        "source_reference": "Item 1A - Risk Factors ¶7",
                        "lesson_reference": {
                            "lesson_id": "lesson-risk-litigation",
                            "learning_module_key": "risk_mastery",
                            "module_stage": "walkthrough",
                        },
                    },
                ]
            }
        },
    }

    query_service = _StubAnalysisQueryService(_make_analysis_query_result())
    storage_provider = _StubStorageProvider(previous_payload)
    diff_service = SectionDiffService(
        analysis_query_service=query_service,
        storage=storage_provider,
    )
    task_data = _make_task_data()

    diffs = await diff_service.compute_diffs(
        task_data=task_data,
        structured_payload=structured_payload,
    )

    assert "Item 1A - Risk Factors" in diffs
    risk_diff = diffs["Item 1A - Risk Factors"]
    assert pytest.approx(risk_diff["sentiment_delta"], rel=1e-6) == -0.35
    assert risk_diff["new_highlights"][0]["id"] == "highlight-new-litigation"
    assert "sentiment fell" in risk_diff["pro_tip"]


@pytest.mark.asyncio
async def test_compute_diffs_returns_empty_when_no_previous_analysis() -> None:
    query_service = _StubAnalysisQueryService(result=None)
    storage_provider = _StubStorageProvider(payload={})
    diff_service = SectionDiffService(
        analysis_query_service=query_service,
        storage=storage_provider,
    )
    task_data = _make_task_data()

    structured_payload = {
        "section_analyses": [],
        "section_walkthroughs": {
            "Item 1A - Risk Factors": {"highlights": []},
        },
    }

    diffs = await diff_service.compute_diffs(
        task_data=task_data,
        structured_payload=structured_payload,
    )

    assert diffs == {}
