"""Celery task to (re)calculate motivation scores for all properties."""
import asyncio
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _recalculate():
    from app.database import AsyncSessionLocal
    from app.models.property import Property
    from app.models.indicator import PropertyIndicator
    from app.models.score import PropertyScore
    from app.services.scoring_engine import calculate_score, IndicatorInput
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Property).options(selectinload(Property.indicators))
        )
        properties = result.scalars().all()

        for prop in properties:
            inputs = [
                IndicatorInput(
                    indicator_type=ind.indicator_type,
                    confidence=ind.confidence,
                )
                for ind in prop.indicators
            ]
            breakdown = calculate_score(inputs)

            score_result = await db.execute(
                select(PropertyScore).where(PropertyScore.property_id == prop.id)
            )
            score = score_result.scalar_one_or_none()

            if not score:
                score = PropertyScore(property_id=prop.id)
                db.add(score)

            score.total_score = breakdown.total_score
            score.financial_score = breakdown.financial_score
            score.legal_score = breakdown.legal_score
            score.landlord_score = breakdown.landlord_score
            score.market_score = breakdown.market_score
            score.condition_score = breakdown.condition_score
            score.indicator_count = breakdown.indicator_count

        await db.commit()
        logger.info(f"Recalculated scores for {len(properties)} properties.")


@celery_app.task(name="app.tasks.recalculate_scores.recalculate_all_scores")
def recalculate_all_scores():
    _run_async(_recalculate())
