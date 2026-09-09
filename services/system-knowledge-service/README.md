# FDAI System Knowledge Service

`fdai-system-knowledge-service` is an independently packaged, read-only Teams mention bot for
questions about FDAI design, implementation status, verification evidence, and known limitations.
It uses a release-bound catalog and has no operational provider or execution authority.

## Responsibilities

- Verify a dedicated Teams bot activity before reading the question.
- Search reviewed English and Korean aliases deterministically.
- Present designed behavior, implemented evidence, limitations, and source citations.
- Preserve retry and ambiguous-send state in a service-owned message ledger.
- Expose independent liveness and readiness.

## Service Boundary

The service does not import Core or Operator Service implementations. It does not read customer
documents, Azure resources, Incidents, or conversation history. The runtime image contains a
compiled catalog but no repository source or Git credential.

## Layout

| Path | Purpose |
|------|---------|
| `src/fdai_system_knowledge_service/catalog.py` | Release catalog compilation and loading |
| `src/fdai_system_knowledge_service/search.py` | Deterministic bilingual retrieval |
| `src/fdai_system_knowledge_service/teams_{auth,ingress,publisher}.py` | Teams authentication, mention parsing, and publishing |
| `src/fdai_system_knowledge_service/ledger.py` | Durable single-replica delivery claims |
| `src/fdai_system_knowledge_service/runtime.py` | Query, rendering, delivery, and failure coordination |
| `src/fdai_system_knowledge_service/application.py` | Health and Teams HTTP routes |
| `tests/` | Service-owned contract and behavior tests |
| `docker/Dockerfile` | Non-root service image |

## Build the catalog

Run the compiler from the repository root after a cited source changes:

```bash
uv run fdai-system-knowledge-build-catalog \
  --repo-root . \
  --output services/system-knowledge-service/src/fdai_system_knowledge_service/data/catalog.json
```

## Run locally

Provide the deployment-owned Teams identifiers and start the service:

```bash
uv run fdai-system-knowledge-service
```

The default listener is `127.0.0.1:8015`.

## Testing

```bash
uv run pytest -q --no-cov services/system-knowledge-service/tests \
  packages/service-contracts/tests/test_system_knowledge.py
```

## Related documentation

| To learn about | Read |
|----------------|------|
| Design and trust boundary | [System Knowledge Service](../../docs/roadmap/interfaces/system-knowledge-service.md) |
| Delivery state | [Implementation ledger](../../docs/roadmap-implementation/interfaces/system-knowledge-service.md) |
| General operational channel runtime | [Production A3 channel runtime](../../docs/roadmap/interfaces/production-a3-channel-runtime.md) |
