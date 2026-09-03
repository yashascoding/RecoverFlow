from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.schemas.investigation import QueryResult, CorrelationResult
from app.services.investigation.investigation_query_service import InvestigationQueryService

logger = get_logger(__name__)


class CorrelationAnalysisService:
    """Service for analyzing correlations and identifying contributors."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.query_service = InvestigationQueryService(db)

    async def analyze_correlations(
        self,
        time_window_hours: int = 24,
    ) -> list[CorrelationResult]:
        """Analyze correlations across all dimensions and rank contributors."""
        all_queries = await self.query_service.query_all_dimensions(time_window_hours)

        contributors = []

        for dimension, query_results in all_queries.items():
            for result in query_results:
                contribution_score = self._calculate_contribution_score(
                    result, all_queries
                )
                confidence = self._calculate_confidence(result, all_queries)

                contributors.append(
                    CorrelationResult(
                        dimension=dimension,
                        value=result.value,
                        contribution_score=contribution_score,
                        confidence=confidence,
                        rank=0,
                    )
                )

        contributors.sort(key=lambda x: x.contribution_score, reverse=True)

        for i, contributor in enumerate(contributors):
            contributor.rank = i + 1

        return contributors

    async def get_top_contributors(
        self,
        time_window_hours: int = 24,
        limit: int = 5,
    ) -> list[CorrelationResult]:
        """Get the top contributors to payment failures."""
        all_contributors = await self.analyze_correlations(time_window_hours)
        return all_contributors[:limit]

    async def get_dimension_contributors(
        self,
        dimension: str,
        time_window_hours: int = 24,
        limit: int = 10,
    ) -> list[CorrelationResult]:
        """Get contributors for a specific dimension."""
        all_contributors = await self.analyze_correlations(time_window_hours)
        dimension_contributors = [
            c for c in all_contributors if c.dimension == dimension
        ]
        return dimension_contributors[:limit]

    def _calculate_contribution_score(
        self,
        result: QueryResult,
        all_queries: dict[str, list[QueryResult]],
    ) -> float:
        """Calculate a contribution score for a query result."""
        revenue_weight = 0.4
        count_weight = 0.3
        percentage_weight = 0.2
        cross_dimension_weight = 0.1

        max_revenue = max(
            (r.revenue_impact for results in all_queries.values() for r in results),
            default=1,
        )
        max_count = max(
            (r.count for results in all_queries.values() for r in results),
            default=1,
        )

        revenue_score = result.revenue_impact / max_revenue if max_revenue > 0 else 0
        count_score = result.count / max_count if max_count > 0 else 0
        percentage_score = result.percentage / 100

        cross_dimension_score = self._calculate_cross_dimension_score(
            result, all_queries
        )

        total_score = (
            revenue_weight * revenue_score
            + count_weight * count_score
            + percentage_weight * percentage_score
            + cross_dimension_weight * cross_dimension_score
        )

        return round(total_score, 4)

    def _calculate_cross_dimension_score(
        self,
        result: QueryResult,
        all_queries: dict[str, list[QueryResult]],
    ) -> float:
        """Calculate cross-dimension correlation score."""
        cross_scores = []

        for dimension, query_results in all_queries.items():
            if dimension == result.dimension:
                continue

            for other_result in query_results:
                if self._are_correlated(result, other_result):
                    cross_scores.append(other_result.percentage / 100)

        return sum(cross_scores) / len(cross_scores) if cross_scores else 0

    def _are_correlated(self, result1: QueryResult, result2: QueryResult) -> bool:
        """Check if two query results are correlated."""
        if result1.dimension == result2.dimension:
            return result1.value == result2.value

        return result1.percentage > 20 and result2.percentage > 20

    def _calculate_confidence(
        self,
        result: QueryResult,
        all_queries: dict[str, list[QueryResult]],
    ) -> float:
        """Calculate confidence score for a correlation."""
        base_confidence = 0.5

        if result.percentage > 50:
            base_confidence += 0.3
        elif result.percentage > 30:
            base_confidence += 0.2
        elif result.percentage > 10:
            base_confidence += 0.1

        if result.revenue_impact > 100000:
            base_confidence += 0.1

        dimension_count = len(all_queries)
        if dimension_count > 3:
            base_confidence += 0.05

        return min(round(base_confidence, 2), 0.99)
