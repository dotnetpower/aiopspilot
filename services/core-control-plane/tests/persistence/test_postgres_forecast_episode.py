from __future__ import annotations

import os
from datetime import timedelta
from uuid import uuid4

import pytest
from fdai.core.detection.forecast_episode import ForecastClosureReason, ForecastEpisodeClosure
from fdai.core.detection.forecast_outcome import (
    ForecastExpectation,
    ForecastObservation,
    close_forecast,
)
from fdai.delivery.persistence.postgres_forecast_episode import (
    PostgresForecastEpisodeStore,
    PostgresForecastEpisodeStoreConfig,
)
from fdai.shared.contracts.models import TelemetryCompleteness

from tests.core.detection.test_forecast_episode import T0, _episode


def test_config_rejects_empty_dsn_and_invalid_timeouts() -> None:
    with pytest.raises(ValueError, match="DSN"):
        PostgresForecastEpisodeStoreConfig(dsn="")
    with pytest.raises(ValueError, match="timeouts"):
        PostgresForecastEpisodeStoreConfig(dsn="postgresql://example", statement_timeout_ms=0)


@pytest.mark.skipif(not os.environ.get("FDAI_DATABASE_URL"), reason="FDAI_DATABASE_URL is unset")
async def test_schema_is_available_after_migration() -> None:
    store = PostgresForecastEpisodeStore(
        config=PostgresForecastEpisodeStoreConfig(dsn=os.environ["FDAI_DATABASE_URL"])
    )
    await store.verify_schema()


@pytest.mark.skipif(not os.environ.get("FDAI_DATABASE_URL"), reason="FDAI_DATABASE_URL is unset")
async def test_publication_claims_do_not_increment_failure_count() -> None:
    dsn = os.environ["FDAI_DATABASE_URL"]
    store = PostgresForecastEpisodeStore(config=PostgresForecastEpisodeStoreConfig(dsn=dsn))
    episode = _episode(
        episode_id=uuid4(),
        correlation_id=f"live-{os.getpid()}",
    )
    payload = {
        "correlation_id": episode.correlation_id,
        "idempotency_key": f"forecast:{episode.episode_id}",
    }
    try:
        await store.record(episode, forecast_payload=payload)
        first = await store.claim_publications(
            now=T0,
            limit=1,
            lease_until=T0 + timedelta(seconds=1),
        )
        second = await store.claim_publications(
            now=T0 + timedelta(seconds=2),
            limit=1,
            lease_until=T0 + timedelta(seconds=3),
        )
        assert first[0].attempts == second[0].attempts == 0
        await store.release_publication(
            second[0].publication_id,
            available_at=T0 + timedelta(seconds=4),
            error="transient",
        )
        third = await store.claim_publications(
            now=T0 + timedelta(seconds=5),
            limit=1,
            lease_until=T0 + timedelta(seconds=6),
        )
        assert third[0].attempts == 1
        await store.dead_letter_publication(
            third[0].publication_id,
            failed_at=T0 + timedelta(seconds=5),
            error="permanent",
        )
        assert (
            await store.claim_publications(
                now=T0 + timedelta(seconds=7),
                limit=1,
                lease_until=T0 + timedelta(seconds=8),
            )
            == ()
        )
    finally:
        import psycopg

        plain = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
        async with await psycopg.AsyncConnection.connect(plain) as connection:
            await connection.execute(
                "DELETE FROM forecast_publication_outbox WHERE episode_id = %s",
                (episode.episode_id,),
            )
            await connection.execute(
                "DELETE FROM forecast_episode WHERE episode_id = %s",
                (episode.episode_id,),
            )


@pytest.mark.skipif(not os.environ.get("FDAI_DATABASE_URL"), reason="FDAI_DATABASE_URL is unset")
async def test_health_snapshot_executes_operational_accuracy_query() -> None:
    dsn = os.environ["FDAI_DATABASE_URL"]
    store = PostgresForecastEpisodeStore(config=PostgresForecastEpisodeStoreConfig(dsn=dsn))
    episode = _episode(
        episode_id=uuid4(),
        correlation_id=f"metrics-{os.getpid()}",
    )
    outcome = close_forecast(
        ForecastExpectation(
            prediction_id=episode.episode_id,
            correlation_id=episode.correlation_id,
            detector_id=episode.detector_id,
            detector_version=episode.detector_version,
            access_scope_digest=episode.access_scope_digest,
            target_ref=episode.target_ref,
            metric=episode.metric,
            feature_cutoff=episode.feature_cutoff,
            horizon_started_at=episode.horizon_started_at,
            horizon_ended_at=episode.horizon_ended_at,
            direction="rising",
            threshold=episode.threshold,
            predicted_value=episode.predicted_value or 0.0,
            interval_lower=episode.interval_lower or 0.0,
            interval_upper=episode.interval_upper or 0.0,
            evidence_refs=episode.evidence_refs,
        ),
        ForecastObservation(
            observed_value=95.0,
            actual_breach_at=T0 + timedelta(minutes=30),
            telemetry_completeness=TelemetryCompleteness.COMPLETE,
            evidence_refs=("metric-window:outcome",),
        ),
        closed_at=T0 + timedelta(hours=1, minutes=5),
    )
    try:
        await store.record(episode)
        assert await store.close(
            ForecastEpisodeClosure(
                episode_id=episode.episode_id,
                expected_revision=episode.revision,
                closed_at=outcome.closed_at,
                reason=ForecastClosureReason.SCORED,
                outcome_payload=outcome.model_dump(mode="json"),
            )
        )

        snapshot = await store.health_snapshot(now=outcome.closed_at)
        metrics = snapshot["operational_metrics"]

        assert isinstance(metrics, dict)
        assert metrics["episode_count"] >= 1
        assert metrics["lead_time_sample_count"] >= 1
        assert metrics["execution_authority"] is False
    finally:
        import psycopg

        plain = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
        async with await psycopg.AsyncConnection.connect(plain) as connection:
            await connection.execute(
                "DELETE FROM forecast_publication_outbox WHERE episode_id = %s",
                (episode.episode_id,),
            )
            await connection.execute(
                "DELETE FROM forecast_episode WHERE episode_id = %s",
                (episode.episode_id,),
            )
