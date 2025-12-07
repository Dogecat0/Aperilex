from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    AnalysisData,
    CompanyData,
    FilingData,
)
from src.infrastructure.database.models.identity import User
from src.infrastructure.database.repositories.analysis_repository import (
    AnalysisRepository,
)
from src.infrastructure.database.repositories.company_repository import (
    CompanyRepository,
)
from src.infrastructure.database.repositories.filing_repository import FilingRepository
from src.shared.enums import (
    AnalysisStatus,
    AnalysisType,
    FilingType,
    TaskStatus,
    UserStatus,
    UserTier,
)
from src.shared.types import (
    CIK,
    AccessionNumber,
    AnalysisId,
    CompanyId,
    FilingId,
    Ticker,
    UserId,
)


async def _create_user(session: AsyncSession, email: str) -> UserId:
    user = User(
        id=uuid.uuid4(),
        email=email,
        status=UserStatus.ACTIVE.value,
        tier=UserTier.ESSENTIAL.value,
    )
    session.add(user)
    await session.commit()
    return UserId(user.id)


@pytest.mark.asyncio
async def test_company_repository_crud_and_lookup(db_session: AsyncSession) -> None:
    repo = CompanyRepository(db_session)
    company_id = CompanyId(uuid.uuid4())

    created = await repo.create(
        CompanyData(
            id=company_id,
            cik=CIK(value="0000320193"),
            name="Apple Inc",
            ticker=Ticker(value="AAPL"),
            metadata={"sector": "Tech"},
        )
    )
    await db_session.commit()

    cached = await repo.get_by_id(company_id)
    assert cached is not None
    assert cached.id == created.id
    assert cached.ticker and cached.ticker.value == "AAPL"

    normalized_lookup = await repo.get_by_cik(CIK(value="320193"))
    assert normalized_lookup is not None
    assert normalized_lookup.id == company_id

    _ = await repo.update(
        CompanyData(
            id=company_id,
            cik=CIK(value="320193"),
            name="Apple Platforms",
            ticker=Ticker(value="APRX"),
            metadata={"sector": "Platform"},
        )
    )
    await db_session.commit()

    refreshed = await repo.get_by_id(company_id)
    assert refreshed is not None
    assert refreshed.name == "Apple Platforms"
    assert refreshed.ticker and refreshed.ticker.value == "APRX"

    name_matches = await repo.find_by_name("Apple", limit=5)
    assert any(item.id == company_id for item in name_matches)

    deleted = await repo.delete(company_id)
    await db_session.commit()
    assert deleted is True
    assert await repo.get_by_id(company_id) is None


@pytest.mark.asyncio
async def test_filing_repository_latest_and_status(db_session: AsyncSession) -> None:
    company_repo = CompanyRepository(db_session)
    filing_repo = FilingRepository(db_session)

    company = await company_repo.create(
        CompanyData(
            id=CompanyId(uuid.uuid4()),
            cik=CIK(value="1067983"),
            name="Aperilex Labs",
            ticker=Ticker(value="APRX"),
            metadata={"sector": "AI"},
        )
    )
    await db_session.commit()

    first_filing = await filing_repo.create(
        FilingData(
            id=FilingId(uuid.uuid4()),
            company_id=company.id,
            filing_type=FilingType.FORM_10K,
            accession_number=AccessionNumber(value="0001067983-23-000001"),
            filing_date=datetime(2023, 1, 1, tzinfo=UTC),
            processing_status=TaskStatus.PENDING,
            metadata={"source": "edgar"},
        )
    )
    latest_filing = await filing_repo.create(
        FilingData(
            id=FilingId(uuid.uuid4()),
            company_id=company.id,
            filing_type=FilingType.FORM_10K,
            accession_number=AccessionNumber(value="0001067983-24-000001"),
            filing_date=datetime(2024, 1, 1, tzinfo=UTC),
            processing_status=TaskStatus.PENDING,
            metadata={"source": "edgar"},
        )
    )
    await db_session.commit()

    fetched_by_accession = await filing_repo.get_by_accession_number(
        AccessionNumber(value="0001067983-24-000001")
    )
    assert fetched_by_accession is not None
    assert fetched_by_accession.id == latest_filing.id

    latest_by_type = await filing_repo.get_latest_by_type(
        company.id, FilingType.FORM_10K
    )
    assert latest_by_type is not None
    assert latest_by_type.id == latest_filing.id

    status_updated = await filing_repo.update_status(
        latest_filing.id, TaskStatus.COMPLETED, error="ok"
    )
    await db_session.commit()
    assert status_updated is not None
    assert status_updated.processing_status == TaskStatus.COMPLETED
    assert status_updated.processing_error == "ok"

    ticker_filtered = await filing_repo.get_by_ticker_with_filters_and_company(
        ticker=Ticker(value="APRX"),
        filing_type=FilingType.FORM_10K,
        sort_field="filing_date",
        sort_direction="desc",
        page_size=10,
    )
    returned_ids = [filing.id for filing, _company in ticker_filtered]
    assert returned_ids == [latest_filing.id, first_filing.id]


@pytest.mark.asyncio
async def test_analysis_repository_lifecycle_and_filters(
    db_session: AsyncSession,
) -> None:
    company_repo = CompanyRepository(db_session)
    filing_repo = FilingRepository(db_session)
    analysis_repo = AnalysisRepository(db_session)

    user_id = await _create_user(db_session, "analyst@example.com")
    company = await company_repo.create(
        CompanyData(
            id=CompanyId(uuid.uuid4()),
            cik=CIK(value="835070"),
            name="Flagged Co",
            ticker=Ticker(value="FLAG"),
            metadata={},
        )
    )
    await db_session.commit()

    filing = await filing_repo.create(
        FilingData(
            id=FilingId(uuid.uuid4()),
            company_id=company.id,
            filing_type=FilingType.FORM_10Q,
            accession_number=AccessionNumber(value="0000835070-24-000001"),
            filing_date=datetime(2024, 4, 1, tzinfo=UTC),
            processing_status=TaskStatus.PENDING,
            metadata={"source": "edgar"},
        )
    )
    await db_session.commit()

    completed_at = datetime.now(UTC).isoformat()
    flagged_analysis = await analysis_repo.create(
        AnalysisData(
            id=AnalysisId(uuid.uuid4()),
            filing_id=filing.id,
            user_id=user_id,
            created_by=str(user_id),
            status=AnalysisStatus.COMPLETED,
            analysis_type=AnalysisType.COMPREHENSIVE.value,
            summary={
                "insight_counts": {"critical_findings": 2},
                "confidence": {"score": 0.72},
            },
            metadata={"analysis_completed_at": completed_at},
        )
    )

    await analysis_repo.create(
        AnalysisData(
            id=AnalysisId(uuid.uuid4()),
            filing_id=filing.id,
            user_id=user_id,
            created_by=str(user_id),
            status=AnalysisStatus.COMPLETED,
            analysis_type=AnalysisType.FINANCIAL.value,
            summary={
                "insight_counts": {"critical_findings": 5},
                "confidence": {"score": 0.82},
            },
            metadata={"analysis_completed_at": completed_at},
        )
    )

    await analysis_repo.create(
        AnalysisData(
            id=AnalysisId(uuid.uuid4()),
            filing_id=filing.id,
            user_id=user_id,
            created_by=str(user_id),
            status=AnalysisStatus.ANALYZING,
            analysis_type=AnalysisType.RISK.value,
            summary={"insight_counts": {"critical_findings": 0}},
            metadata={},
        )
    )

    cached = await analysis_repo.get_by_id(flagged_analysis.id)
    assert cached is not None
    assert cached.completed_at is not None
    assert cached.summary and cached.summary["insight_counts"]["critical_findings"] == 2

    updated_status = await analysis_repo.update_status(
        flagged_analysis.id, AnalysisStatus.ERROR, error_message="failed"
    )
    assert updated_status is True

    after_status = await analysis_repo.get_by_id(flagged_analysis.id)
    assert after_status is not None
    assert after_status.status == AnalysisStatus.ERROR
    assert after_status.metadata.get("error_message") == "failed"

    saved = await analysis_repo.save_summary(
        flagged_analysis.id,
        {"insight_counts": {"critical_findings": 3}},
        metadata_updates={"analysis_completed_at": completed_at},
    )
    assert saved is True

    refreshed = await analysis_repo.get_by_id(flagged_analysis.id)
    assert refreshed is not None
    assert (
        refreshed.summary
        and refreshed.summary["insight_counts"]["critical_findings"] == 3
    )

    flagged_results = await analysis_repo.find_with_filters(
        segment="flagged",
        sort_by="insight_counts.critical_findings",
        sort_direction="desc",
        page_size=10,
    )
    assert [
        result.summary["insight_counts"]["critical_findings"]
        for result in flagged_results
    ] == [5, 3]
    assert await analysis_repo.count_with_filters(segment="attention") == 1
