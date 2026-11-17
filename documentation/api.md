# REST API

Interactive OpenAPI docs: **http://localhost:8000/docs** (Swagger) and `/redoc`.

**Conventions**
- Errors: `{"success": false, "error": {"code": "HTTP_404", "message": "...", "details": [...]}}`. Validation errors use `VALIDATION_ERROR` with field details. Unexpected errors return a generic 500 and are logged server-side.
- Lists: `{"items": [...], "total": n, "page": p, "page_size": s}`.
- Auth: when `AUTH_ENABLED=true`, send `Authorization: Bearer <token>`. Otherwise every request acts as the demo admin.
- Every response includes an `X-Response-Time-ms` header.

| Method | Path | Description | Notes |
|---|---|---|---|
| GET | `/health` | Liveness | no DB access |
| GET | `/api/system/status` | DB, sandbox, LLM mode, auth mode, pricing | |
| POST | `/api/auth/register` | Create account (first user = admin) | auth enabled only, rate-limited |
| POST | `/api/auth/login` | Get JWT | rate-limited |
| GET | `/api/auth/me` | Current user | |
| POST | `/api/projects` | Create project (optional `requirement`) | 201 |
| GET | `/api/projects` | List: `search`, `status`, `business_domain`, `sort`, `order`, `page`, `page_size` | |
| GET | `/api/projects/{id}` | Detail with execution history | |
| PUT | `/api/projects/{id}` | Partial update | owner or admin |
| DELETE | `/api/projects/{id}` | Delete (cascades) | 409 if an execution is active |
| POST | `/api/projects/{id}/requirements` | Add requirement (10–10,000 chars) | |
| GET | `/api/projects/{id}/requirements` | List requirements | |
| PUT | `/api/requirements/{id}` | Edit text or `structured_output` | output validated against agent schema |
| POST | `/api/projects/{id}/execute` | Start workflow (`requirement_id` optional) | 202, rate-limited, 409 if active |
| GET | `/api/executions` | List: `project_id`, `status`, paging | |
| GET | `/api/executions/{id}` | Status, pending approval, latest output of each agent | |
| GET | `/api/executions/{id}/agents` | Agent runs | |
| GET | `/api/executions/{id}/logs?after_id=` | Incremental logs | |
| GET | `/api/executions/{id}/tests` | Executed check results (all iterations) | |
| GET | `/api/executions/{id}/workflow` | Graph nodes/edges with live status + transitions | |
| GET | `/api/executions/{id}/package` | Delivery zip (source, docs, manifest) | |
| POST | `/api/executions/{id}/cancel` | Cancel | |
| GET | `/api/approvals` | List: `decision`, `execution_id` | |
| POST | `/api/executions/{id}/approve` | Approve pending checkpoint (`feedback` optional) | reviewer/admin |
| POST | `/api/executions/{id}/reject` | `{feedback, request_revision}`: revise or stop | reviewer/admin |
| GET | `/api/projects/{id}/artifacts` | `execution_id`, `artifact_type`, `latest_only` | |
| GET | `/api/artifacts/{id}` | Metadata + text content (≤1 MB) | |
| GET | `/api/artifacts/{id}/download` | File as attachment | path-validated |
| GET | `/api/analytics/overview` | Dashboard figures | |
| GET | `/api/analytics/agents` | Per-agent success, duration, tokens, retries | |
| GET | `/api/analytics/executions` | Completion, tests, corrections, tokens, cost, latency | |
| GET | `/api/agents` | Agent catalogue | |

## Example: drive the whole workflow with curl

```bash
P=$(curl -s -X POST localhost:8000/api/projects -H 'Content-Type: application/json' \
  -d '{"name":"Leave","requirement":"Build an employee leave app with login and leave approvals."}' | jq .id)
E=$(curl -s -X POST localhost:8000/api/projects/$P/execute | jq .id)
curl -s localhost:8000/api/executions/$E | jq '.status, .pending_approval.checkpoint'
curl -s -X POST localhost:8000/api/executions/$E/approve -H 'Content-Type: application/json' -d '{}'
```
