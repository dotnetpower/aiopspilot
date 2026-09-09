from __future__ import annotations

import json

import pytest
from fdai_system_knowledge_service.config import (
    CLAIM_CONTAINER_URL_ENV,
    SystemKnowledgeConfigurationError,
    SystemKnowledgeSettings,
)


def _environment(*, venue: str) -> dict[str, str]:
    values = {
        "FDAI_EXECUTION_VENUE": venue,
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_APPLICATION_ID": "application-example",
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_BOT_ID": "28:application-example",
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_TENANT_ID": "tenant-example",
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_TEAM_IDS_JSON": json.dumps(["team-example"]),
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_CHANNEL_IDS_JSON": json.dumps(["channel-example"]),
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_SERVICE_URLS_JSON": json.dumps(
            ["https://smba.trafficmanager.net/example"]
        ),
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_PRINCIPAL_MAP_JSON": json.dumps(
            {"aad-example": "principal-example"}
        ),
        "FDAI_SYSTEM_KNOWLEDGE_TEAMS_JWKS_URL": "https://login.example.com/keys",
    }
    if venue == "local":
        values["FDAI_SYSTEM_KNOWLEDGE_TEAMS_CLIENT_SECRET"] = "local-secret"
    else:
        values["FDAI_SYSTEM_KNOWLEDGE_SOURCE_REVISION"] = "a" * 40
        values["FDAI_SYSTEM_KNOWLEDGE_MI_CLIENT_ID"] = "application-example"
        values[CLAIM_CONTAINER_URL_ENV] = "https://storage.example.com/system-knowledge-claims"
    return values


def test_deployed_settings_require_managed_identity_blob_claims() -> None:
    settings = SystemKnowledgeSettings.parse(_environment(venue="deployed"))

    assert settings.claim_container_url is not None
    assert settings.managed_identity_client_id == settings.teams.application_id
    assert settings.teams.client_secret is None


def test_deployed_settings_reject_missing_claim_container() -> None:
    values = _environment(venue="deployed")
    del values[CLAIM_CONTAINER_URL_ENV]

    with pytest.raises(SystemKnowledgeConfigurationError, match=CLAIM_CONTAINER_URL_ENV):
        SystemKnowledgeSettings.parse(values)


def test_local_settings_reject_deployed_blob_binding() -> None:
    values = _environment(venue="local")
    values[CLAIM_CONTAINER_URL_ENV] = "https://storage.example.com/system-knowledge-claims"

    with pytest.raises(SystemKnowledgeConfigurationError, match="MUST be unset"):
        SystemKnowledgeSettings.parse(values)
