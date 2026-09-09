---
title: Onboard the System Knowledge Teams Bot
---
# Onboard the System Knowledge Teams Bot

Use this runbook to prepare and deploy the independent FDAI System Knowledge Service in one
approved standard Teams channel. The workflow keeps tenant values in GitHub configuration, uses a
deployment-only OpenID Connect (OIDC) identity for Microsoft Graph, and gives the runtime identity
no app-catalog or execution permission.

> **Scope:** This runbook covers the development environment. It does not change the operational
> A3 bot, request resource-specific consent (RSC) for all channel messages, or grant managed-resource
> execution authority.
>
> **Private tenant:** Run Key Vault, Blob, Terraform state, and Container Apps work through the
> VNet-connected self-hosted runner. Do not copy a secret or private state file to a laptop.

## Prerequisites

You need:

- an approved standard Team and channel;
- one or more Entra users mapped to stable FDAI knowledge principal names;
- a clean, pushed protected-main revision with required CI and an attested
  `fdai-system-knowledge-service` image;
- tenant administration permission to bootstrap the deployment-only installer identity;
- the existing private FDAI platform with document Blob storage enabled.

Private and shared channels are not supported by the initial release.

## Configure the Teams profile

Create these repository secrets without writing their values to source control:

| Secret | Content |
|--------|---------|
| `SYSTEM_KNOWLEDGE_TEAMS_PROFILE_JSON` | Service name, Bot name, tenant, approved team and channel lists, Bot service URL allowlist, and JWKS URL |
| `SYSTEM_KNOWLEDGE_PRINCIPAL_MAP_JSON` | Teams sender `aadObjectId` to deployment-local knowledge principal mapping |

Use this shape for the profile:

```json
{
  "service_name": "<container-app-name>",
  "bot_name": "<azure-bot-name>",
  "tenant_id": "<tenant-guid>",
  "team_ids": ["<team-guid>"],
  "channel_ids": ["<channel-id>"],
  "allowed_service_urls": ["https://<bot-service-origin>"],
  "jwks_url": "https://<bot-service-jwks-url>"
}
```

Use this shape for the principal map:

```json
{
  "<entra-user-object-id>": "<knowledge-principal>"
}
```

The protected workflow writes only the principal map to one fixed Key Vault secret. The other
values remain protected deployment inputs and appear in the restricted Terraform state.

## Bootstrap the deployment-only installer

The installer uses exactly two Microsoft Graph application permissions:

- `AppCatalog.ReadWrite.All`;
- `TeamsAppInstallation.ReadWriteForTeam.All`.

The runtime UAMI does not receive either permission. Bootstrap the installer once while signed in
as a tenant administrator:

```bash
result="$(
  uv run --frozen --package fdai-system-knowledge-service python \
    scripts/deployment/system_knowledge/bootstrap_installer_identity.py \
    --repository dotnetpower/fdai \
    --environment dev
)"
client_id="$(jq -er '.client_id' <<<"$result")"
gh variable set SYSTEM_KNOWLEDGE_INSTALLER_CLIENT_ID --body "$client_id"
result=""
client_id=""
```

The helper creates or verifies one Entra application, service principal, GitHub
`repo:dotnetpower/fdai:environment:dev` federated credential, and the exact two Graph roles. The
apply job exchanges GitHub OIDC for a short-lived Graph token. No client secret is created.

## Plan the deployment

Resolve the attested image digest for the exact required-CI revision, then dispatch plan-only:

```bash
gh workflow run system-knowledge-deploy.yml \
  -f commit_sha=<exact-sha> \
  -f image_ref=ghcr.io/dotnetpower/fdai/fdai-system-knowledge-service@sha256:<digest> \
  -f previous_image_ref=ghcr.io/dotnetpower/fdai/fdai-system-knowledge-service@sha256:<digest> \
  -f transition=enable
```

The plan is accepted only when it contains the dedicated UAMI, private claim container, three
minimum role assignments, one-replica Container App, F0 Azure Bot, Teams channel, and
`execution_authority=false` contract.

Record the plan run id, attempt, plan digest, and context digest from the workflow summary.

## Apply and install

Dispatch apply with the exact plan evidence:

```bash
gh workflow run system-knowledge-deploy.yml \
  -f commit_sha=<exact-sha> \
  -f image_ref=ghcr.io/dotnetpower/fdai/fdai-system-knowledge-service@sha256:<digest> \
  -f previous_image_ref=ghcr.io/dotnetpower/fdai/fdai-system-knowledge-service@sha256:<digest> \
  -f transition=enable \
  -f apply=true \
  -f plan_run_id=<plan-run-id> \
  -f plan_run_attempt=<attempt> \
  -f plan_digest=<plan-sha256> \
  -f context_digest=sha256:<context-sha256>
```

The workflow:

1. replays and guards the exact binary plan;
2. materializes and reads back the principal map inside the private VNet;
3. applies the plan;
4. verifies the active healthy revision and private Blob claim container;
5. builds the deterministic Teams package;
6. uses the deployment-only OIDC identity to upload and install the package.

## Validate the channel

In the approved standard channel:

1. Mention `FDAI Knowledge` and ask how FDAI keeps actions safe.
2. Verify that one same-conversation reply contains designed behavior, implementation evidence,
   limitations, source paths, and `execution_authority=false`.
3. Restart the exact Container App revision.
4. Confirm that no prior message is replied to again.
5. Send another mention and confirm one new reply.
6. Retain only content-free claim, revision, delivery, and timing evidence.

Do not copy conversation text, user identifiers, Team ids, or channel ids into the repository.

## Rehearse disable and rollback

Create a new plan with `transition=disable`, then apply its exact evidence using the same workflow.
The apply must finish within 15 minutes and leave the dedicated service Terraform state empty. Core,
Operator Service, document services, the Isolated Executor, and the operational A3 edge must remain
unchanged.

After recording rollback evidence, create and apply a fresh `enable` plan if the approved target
state is to keep the bot running.

## Related docs

| To learn about | Read |
|----------------|------|
| Service design and failure behavior | [System Knowledge Service](../roadmap/interfaces/system-knowledge-service.md) |
| Private deployment runner | [Deploy and onboard](../roadmap/deployment/deploy-and-onboard.md) |
| Service graduation gates | [Service graduation and data ownership](../roadmap/architecture/service-graduation-and-ownership.md) |
| Operational Teams conversations | [Production A3 channel runtime](../roadmap/interfaces/production-a3-channel-runtime.md) |
