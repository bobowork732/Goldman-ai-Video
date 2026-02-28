# Goldman-ai-Video

Minimal monorepo scaffold for an AI video generation platform.

## Monorepo layout

- `apps/web` — frontend UI placeholder.
- `apps/api` — REST API, queue orchestration, and pre-generation safety gate.
- `services/generation-worker` — worker consumer, model adapter registry, post-generation safety review, and output storage.
- `packages/shared` — shared DTOs, worker contracts, model capability schemas, and policy response schema.

## Architecture diagram

```text
+---------------------+      POST /jobs/* + prompt/image safety      +-------------------------+
|      apps/web       | ------------------------------------------------>       apps/api         |
|   Frontend client   |                                                         | pre-gen policy gate |
+---------------------+                                                         +----------+----------+
                                                                                           |
                                                                                           | enqueue WorkerJobContract
                                                                                           v
                                                                               +-------------------------+
                                                                               |      Redis Queue        |
                                                                               +------------+------------+
                                                                                            |
                                                                                            | consume + generate + moderate
                                                                                            v
                                                                               +-------------------------+
                                                                               | generation-worker       |
                                                                               | adapter + safety review |
                                                                               +------------+------------+
                                                                                            |
                                                                                            | publish only when allowed
                                                                                            v
                                                                               +-------------------------+
                                                                               | local/S3-compatible     |
                                                                               | output storage          |
                                                                               +-------------------------+
```

## API endpoints

- `POST /jobs/text-to-video`
- `POST /jobs/image-to-video`
- `GET /jobs/:id`
- `GET /assets/:id`
- `GET /assets/:id/provenance`

## Safety pipeline

### Pre-generation checks (`apps/api/src/safety`)

- Prompt policy classification across categories:
  - violence
  - sexual
  - hate
  - illegal
- Image screening hook for image-to-video requests.
- Policy result decisions:
  - `allow` (job can proceed)
  - `flag` (job can proceed with stricter controls / review marker)
  - `block` (job rejected with actionable reason)

### Generation-time controls

- Negative prompt presets:
  - `standard`
  - `strict`
- Model parameter clamps applied before queueing and re-applied in worker:
  - `duration_seconds`
  - `guidance_scale`
  - `motion_intensity`

### Post-generation review (`services/generation-worker/src/safety`)

- Frame sampling strategy for moderation scan.
- Moderation findings are categorized and scored.
- Block/flag pipeline holds publication of asset URLs until safety review is passed.

## Policy response schema

Shared response contract in `packages/shared/src/policy.ts`:

- `decision`: `allow | flag | block`
- `reasons[]`: actionable category/code/message details
- `user_safe_message`: safe user-facing explanation
- `review_required`: signals manual/escalated review path

## Policy levels

- **Level 0 (Allow):** no policy indicators; job proceeds.
- **Level 1 (Flag):** non-blocking concerns; stricter prompts/controls and additional review.
- **Level 2 (Block):** disallowed content; request rejected with actionable remediation guidance.

## Admin override design (role-based + auditable)

Recommended design for future implementation:

1. Role-based access control
   - `policy_reviewer`: can resolve flagged jobs.
   - `policy_admin`: can issue temporary, scoped overrides.
2. Override constraints
   - Per job or per tenant scope.
   - Time-bounded expiration.
   - Reason code + free-text justification required.
3. Audit log requirements
   - Who approved override (`actor_id`, role).
   - What changed (original decision, overridden decision).
   - Why (reason, ticket/case link).
   - When (timestamp, expiry).
4. Operational controls
   - Notify compliance/security channel on overrides.
   - Weekly review report of overrides and outcomes.


## Enterprise watermark mode

- API accepts `enterprise_mode` and `tenant_watermark` options on job creation requests.
- Tenant style settings can tune text, opacity, and placement, but minimum watermark policy is always enforced (`ENTERPRISE_WATERMARK_MIN_OPACITY`, `ENTERPRISE_WATERMARK_MIN_MARGIN`).
- Worker applies ffmpeg watermark overlay (`drawtext`) before moderation/publication.

## Generation provenance

- Worker emits provenance metadata sidecar (`<job_id>.provenance.json`) with:
  - model ID/version
  - generation timestamp
  - job ID and deterministic metadata hash
  - lineage fields for text-to-video and image-to-video flows
- API verification endpoint `GET /assets/:id/provenance` returns metadata hash and lineage for stored assets.

## Model registry and validation gate

- Model capability declarations live in `services/generation-worker/config/models.yaml`.
- API reads this registry and rejects unsupported `model` + `job_type` combinations before queueing jobs.
- Capability flags include `supports_t2v`, `supports_i2v`, and `max_duration_s`.

## Worker adapters and storage

- Common adapter interface is in `services/generation-worker/src/models/base_adapter.ts`:
  - `load()`
  - `generate_from_text(prompt, params)`
  - `generate_from_image(image, prompt, params)`
- Baseline adapter: `ZeroScopeV2XLAdapter`.
- Extension point: add another adapter class and register it in `src/models/registry.ts`, then map it in `config/models.yaml`.
- Storage abstraction in `services/generation-worker/src/storage/output-storage.ts` supports local and S3-compatible modes.

## Local run instructions

### Prerequisites

- Node.js 20+
- npm 10+
- Optional: Redis (required for cross-process queueing)

### Install

```bash
npm install
```

### Run API

```bash
npm run dev:api
```

The API listens on `http://localhost:3001` by default.

### Run worker

If Redis is running locally:

```bash
REDIS_URL=redis://localhost:6379 npm run dev:worker
```

### Notes

- If `REDIS_URL` is not set in `apps/api`, it falls back to an in-memory queue abstraction.
- Local output storage defaults to `./storage` and is served by the API at `/storage/*`.
