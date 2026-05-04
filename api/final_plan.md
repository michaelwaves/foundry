# Foundry Cloud Platform — Final Plan

A web app where researchers design proteins with RFdiffusion3 plus custom SAE steering hooks (toxicity, etc). Users land on `/d/generate`, upload a motif PDB, set contig + hotspots + steps + steering, click Run, watch logs stream in, then view inputs/outputs of every job at `/d/jobs`. NVIDIA's RFD3 demo is the UI reference.

---

## Architecture

```
Browser (Next.js 16, app router)
   │
   ├─ Google / email-pass login ─────► Supabase Auth (issues JWT, sets cookie)
   │
   ├─ /d/generate  POST → Server Action submitJob()
   │     │ uploads motif to Supabase Storage `inputs/{user_id}/{job_id}.pdb`
   │     │ POSTs JSON job_config + Bearer JWT to Railway
   │     ▼
   │  Railway FastAPI ──► auth.get_user_id (verify JWT locally)
   │     │                ├─► Supabase Postgres   (insert jobs row, created_by, inputs jsonb)
   │     │                └─► modal_worker.run_job.spawn(job_id, job_config)
   │     │                                                         │
   ├─ /d/jobs/[id]  GET /api/jobs/[id]/stream  (SSE, Bearer JWT) ──┴── Modal GPU worker
   │     proxied through Next route handler  ◄──── Redis pub/sub ◄────  │
   │                                                                    │
   │                                                                    ├─► Redis (publish logs, status)
   │                                                                    ├─► Supabase Postgres (status, output_url)
   │                                                                    └─► Supabase Storage `outputs/{user_id}/{job_id}.cif.gz`
   │
   └─ /d/jobs/[id]  reads jobs row + signed URL from Storage
```

Three deployment targets:
- **Vercel** — Next.js frontend (free for hobby; Fluid compute supported).
- **Railway** — FastAPI orchestration + Redis addon (single project, both services).
- **Modal** — GPU worker (`A10G`, `timeout=1800`) + persistent volume `foundry-weights` for RFD3 + SAE checkpoints + steering vectors.

Redis lives **on Railway** as the addon, not a separate provider. Reason: API and Redis colocate (lower latency on SSE pubsub), one billing surface, one project to operate.

---

## What's in this repo today

| Area | State |
|---|---|
| `api/` | FastAPI MVP with in-memory store, subprocess `saffron steer`, two-knob form (alpha, partial_t, motif). Migration target written in `api/plan.md`. |
| `frontend/app/d/steering/page.tsx` | Working MVP design form (alpha slider, partial_t slider, motif upload, log stream, output download). Talks to local FastAPI via Server Action. |
| `frontend/lib/supabase/{client,server,middleware}.ts` | Supabase SSR clients exist. **No `proxy.ts` at root** — auth gate not wired. **`updateSession()` redirects to `/auth/login` but no login page exists yet.** |
| `frontend/app/api/jobs/[id]/stream/route.ts` | SSE proxy route to Railway. Currently does **not** forward Bearer token. |
| `frontend/app/d/{generate,jobs}/page.tsx` | Empty (1-line files). Need to be built. |

Important Next.js 16 detail: `middleware.ts` was renamed to **`proxy.ts`** at the project root. The lib helper `lib/supabase/middleware.ts` still exists but the root file must be `proxy.ts`. (See `node_modules/next/dist/docs/01-app/01-getting-started/16-proxy.md`.)

---

## Phase 0 — Job spec expansion

The MVP collected 3 inputs: `alpha`, `partial_t`, `motif`. The full design page collects what the NVIDIA demo collects, plus our steering knobs and the fields RFD3's input format actually requires.

`job_config` shape (sent from frontend → Railway, persisted in `jobs.inputs` jsonb, forwarded to Modal):

```ts
type JobConfig = {
  // RFD3 inputs (shape mirrors tutorials/rfd3_ppi_tutorial/ppi_tutorial.yaml)
  design_name: string                 // slugified, e.g. "binder_4zxb_a"
  pdb_storage_path: string | null     // "inputs/{user_id}/{job_id}.pdb" or null for de novo
  contig: string | null               // e.g. "40-120,/0,E6-155"
  length: string | null               // e.g. "190-270" (used when no contig, or as range)
  hotspots: Record<string, string>    // {"E64": "CD2,CZ", ...}; empty obj if none
  diffusion_steps: number             // 1..50, default 15
  infer_ori_strategy: 'hotspots' | 'none'
  is_non_loopy: boolean
  partial_t: number                   // 0 = off; only valid when pdb provided

  // SAE steering knobs
  steering: {
    feature_id: number                // e.g. 639 (toxicity)
    alpha: number                     // -10..+10; 0 = off
    apply_at_steps: 'all' | number[]
  } | null
}
```

The Modal worker assembles the `inputs.json` (`{design_name: spec}`) and the steering YAML from this dict, then calls `saffron steer model=rfd3 inputs=... out_dir=... diffusion.num_steps=<N>`.

> **Correction to `api/plan.md`**: the old plan only carries `alpha`, `partial_t`, `motif_bytes`. Replace those args with the full `JobConfig` dict. Inline `motif_bytes` as a Modal spawn argument is fine (PDBs are <1MB), but we'll prefer the storage path for large files and so the user can re-fetch their input later from `/d/jobs/[id]`.

---

## Phase 1 — Supabase

### 1.1 Auth providers

In Supabase Studio → Authentication → Providers:

- **Email**: enable, confirm-on-signup off for dev / on for prod.
- **Google**: enable, paste OAuth client ID + secret. Authorized redirect URI:
  - `https://<project>.supabase.co/auth/v1/callback`
  - In Google Cloud Console → APIs & Services → Credentials → OAuth client → "Authorized redirect URIs", add the same URL.
  - "Authorized JavaScript origins": `https://<your-vercel-domain>` and `http://localhost:3002` for dev.

### 1.2 Schema

```sql
-- jobs
create table jobs (
  id            uuid primary key default gen_random_uuid(),
  status        text not null default 'pending',  -- pending | running | done | failed
  error         text,
  inputs        jsonb not null,                   -- the JobConfig dict
  output_url    text,                             -- signed URL written by worker
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  created_by    uuid not null references auth.users(id)
);
create index jobs_created_by_idx on jobs (created_by, created_at desc);

alter table jobs enable row level security;
create policy "users see own jobs"   on jobs for select using (auth.uid() = created_by);
create policy "users insert own jobs" on jobs for insert with check (auth.uid() = created_by);
```

RLS is defense-in-depth. Railway uses the **service-role key** (bypasses RLS) and filters `created_by = user_id` explicitly in every query. The frontend reads jobs directly via the **anon key** so RLS is the actual enforcement on the read path.

### 1.3 Storage

Two private buckets:
- `inputs` — motif PDBs uploaded by the frontend (path: `{user_id}/{job_id}.pdb`).
- `outputs` — `.cif.gz` written by the Modal worker (path: `{user_id}/{job_id}.cif.gz`).

Storage RLS: users can read/write their own `{user_id}/...` prefix; service-role bypasses.

### 1.4 Env vars

| Where | Var |
|---|---|
| Vercel | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `API_URL` (Railway URL) |
| Railway | `SUPABASE_URL`, `SUPABASE_KEY` (service-role), `SUPABASE_JWT_SECRET`, `REDIS_URL` |
| Modal Secret `foundry-secrets` | `SUPABASE_URL`, `SUPABASE_KEY` (service-role), `REDIS_URL` |

`SUPABASE_JWT_SECRET` is in Supabase → Project Settings → API → JWT Secret. Never sent to Modal — Railway alone verifies JWTs.

---

## Phase 2 — Frontend (Next.js 16)

### 2.1 Auth surface

**`frontend/proxy.ts`** (new, root-level — replaces what would have been `middleware.ts` in pre-16 Next):

```ts
import type { NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

export async function proxy(request: NextRequest) {
  return updateSession(request)
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
```

`lib/supabase/middleware.ts` already redirects unauthenticated users to `/auth/login` for any path that isn't `/login` or `/auth`. Update its allowlist to also let `/`, `/docs/*`, and `/_next/*` through unauthenticated (the nextra docs site is public).

**`frontend/app/auth/login/page.tsx`** (new — client component): Google button + email/password form.

```tsx
'use client'
import { createClient } from '@/lib/supabase/client'

export default function Login() {
  const supabase = createClient()

  const google = () =>
    supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${location.origin}/auth/callback?next=/d/generate` },
    })

  // form submits handler calls supabase.auth.signInWithPassword(...) / signUp(...)
  // ...
}
```

**`frontend/app/auth/callback/route.ts`** (new — route handler that exchanges the OAuth code for a session, then redirects to `next`). Standard Supabase pattern; copy from `@supabase/ssr` examples.

**`frontend/app/auth/logout/route.ts`** (new — POST signs out, redirects to `/`).

### 2.2 `/d/generate` (main design page)

Mirrors NVIDIA's layout: input form on the left, job status / 3D viewer on the right.

State managed locally; submission via Server Action.

Form fields (in this order, top → bottom):

1. **Target Protein (PDB upload)** — required for motif designs; `<input type="file" accept=".pdb">`.
2. **Contigs** — text input, e.g. `A114-353/0 50-100`. Help tooltip explains syntax.
3. **Hotspot Residues** — text input parsed into `{"E64": "CD2,CZ", ...}`. Permit two formats:
   - shorthand `A119,A123,A233` → atom set defaults to all sidechain heavy atoms
   - explicit `E64:CD2+CZ; E88:CG+CZ` → exact atom-level
4. **Length range** — two number inputs `min`–`max` (default 100–150 if no PDB).
5. **Diffusion Steps** — slider 1–50, default 15 (matches NVIDIA).
6. **Steering** — collapsible section:
   - Feature dropdown (toxicity=639, more later from a `/api/sae/features` listing).
   - α slider −10…+10, step 0.5.
   - "apply at steps": "all" radio + "list" textarea.
7. **partial_t** — slider 0…160 (disabled when no motif). Same as MVP.
8. **Run** button → calls Server Action `submitJob(formData)`.

Right pane: status card, log stream, **3D viewer** when `done` (load `output_url` into a small `mol*` or `3dmol.js` viewer; defer to post-MVP — initial release just shows download button like the steering page does today).

Wire up logs by opening `EventSource('/api/jobs/{id}/stream')` exactly as `app/d/steering/page.tsx` does today. **Reuse that page's hook structure** — it is correct.

### 2.3 `/d/jobs` (list) and `/d/jobs/[id]` (detail)

Server Components — read directly from Supabase using the SSR client (RLS enforces ownership):

```tsx
// app/d/jobs/page.tsx
import { createClient } from '@/lib/supabase/server'

export default async function JobsList() {
  const supabase = await createClient()
  const { data: jobs } = await supabase
    .from('jobs')
    .select('id, status, created_at, inputs')
    .order('created_at', { ascending: false })
    .limit(100)
  // render table: id (truncated) · status badge · created_at · design_name · row → /d/jobs/{id}
}
```

`/d/jobs/[id]` shows:
- Status pill (live-updating via SSE if `running`/`pending`).
- **Inputs panel** — pretty-printed `inputs` jsonb, plus a "Download motif PDB" link (signed URL from `inputs` bucket).
- **Outputs panel** — when `status='done'`: download `.cif.gz`, embed 3D viewer, show generation parameters used.
- **Logs panel** — full log stream (poll Redis via SSE while running; fetch one-shot log archive after done — *future enhancement*: write final logs to Supabase Storage when worker finishes so they persist past the Redis pubsub).

### 2.4 SSE route — forward auth header

Current `app/api/jobs/[id]/stream/route.ts` does **not** forward the Supabase JWT. Fix:

```ts
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) return new Response('unauthorized', { status: 401 })

  const upstream = await fetch(`${API_URL}/jobs/${id}/stream`, {
    cache: 'no-store',
    headers: { Authorization: `Bearer ${session.access_token}` },
  })
  // ... same stream proxy as today
}
```

Same fix in `app/actions.ts` — `submitJob` and `downloadOutput` need to attach `Authorization: Bearer <access_token>` from the SSR client.

### 2.5 Server Actions

```ts
// app/actions.ts
'use server'
import { createClient } from '@/lib/supabase/server'

export async function submitJob(jobConfig: JobConfig, motifFile: File | null) {
  const supabase = await createClient()
  const { data: { session }, data: { user } } = await supabase.auth.getSession()
  if (!session || !user) throw new Error('unauthorized')

  // 1. upload motif to Supabase Storage if present (path: inputs/{user_id}/{tmp_uuid}.pdb)
  //    server-side upload uses the user's session, bound by storage RLS to their own prefix.
  let pdbStoragePath: string | null = null
  if (motifFile) {
    const tmpId = crypto.randomUUID()
    pdbStoragePath = `${user.id}/${tmpId}.pdb`
    const { error } = await supabase.storage.from('inputs').upload(pdbStoragePath, motifFile)
    if (error) throw error
  }

  // 2. POST to Railway with Bearer token
  const res = await fetch(`${process.env.API_URL}/jobs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ ...jobConfig, pdb_storage_path: pdbStoragePath }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<{ job_id: string }>
}
```

Note: The motif is uploaded under a temporary path; the Modal worker copies it (or re-uploads) to the canonical `inputs/{user_id}/{job_id}.pdb` on first read. Or — simpler — Railway renames it on insert. Pick one; I'd just have Railway pass the storage path through and let the worker download it as-is.

---

## Phase 3 — Backend changes (delta vs `api/plan.md`)

The original plan covers Modal + Redis + Supabase + JWT verification. Keep all of that. The deltas:

### 3.1 `models.py`

```python
@dataclass
class JobConfig:
    design_name: str
    pdb_storage_path: str | None
    contig: str | None
    length: str | None
    hotspots: dict[str, str]
    diffusion_steps: int
    infer_ori_strategy: str
    is_non_loopy: bool
    partial_t: float
    steering: SteeringConfig | None

@dataclass
class SteeringConfig:
    feature_id: int
    alpha: float
    apply_at_steps: str | list[int]
```

`Job` keeps `id`, `status`, `error`, `output_url`. Drop `logs: list[str]` (lives in Redis).

### 3.2 `main.py` — `POST /jobs`

```python
@app.post("/jobs")
async def submit_job(
    job_config: JobConfig,
    user_id: str = Depends(get_user_id),
):
    job_id = str(uuid.uuid4())
    insert_job(db_client, job_id, user_id, job_config)
    run_job.spawn(job_id, asdict(job_config))
    return {"job_id": job_id}
```

JSON body, not multipart. The motif PDB lives in Supabase Storage already; Railway never sees the bytes.

### 3.3 `modal_worker.py` — full RFD3 invocation

The worker now:

1. Downloads `pdb_storage_path` from Supabase Storage to `/tmp/{job_id}/motif.pdb` (if not null).
2. Builds `inputs.json` from `JobConfig`:
   ```python
   spec = {
       "input": str(motif_path) if motif_path else None,
       "contig": cfg["contig"],
       "length": cfg["length"],
       "select_hotspots": cfg["hotspots"] or None,
       "infer_ori_strategy": cfg["infer_ori_strategy"],
       "is_non_loopy": cfg["is_non_loopy"],
       "select_fixed_atoms": True if motif_path else False,
   }
   if cfg["partial_t"] > 0 and motif_path:
       spec["partial_t"] = cfg["partial_t"]
   inputs = {cfg["design_name"]: {k: v for k, v in spec.items() if v is not None}}
   ```
3. Generates the steering YAML iff `cfg["steering"]` is set, else skips `hooks=` and `steering=`.
4. Builds the saffron command:
   ```python
   cmd = ["saffron", "steer", "model=rfd3",
          f"inputs={inputs_path}", f"out_dir={out_dir}",
          f"diffusion.num_steps={cfg['diffusion_steps']}"]
   if steering_yaml:
       cmd += ["hooks=rfd3_steer_only", f"steering={steering_yaml}"]
   ```
5. Streams stdout/stderr line-by-line to Redis channel `logs:{job_id}` (1 publish per line).
6. Also publishes status transitions on a separate channel `status:{job_id}` (or as a typed event on the same channel — pick one; I'd use a single channel with `event:` prefixes matching what the steering MVP already parses: `log` and `status`).
7. Uploads the resulting `.cif.gz` to `outputs/{user_id}/{job_id}.cif.gz`, generates a 1-hour signed URL, writes it to `jobs.output_url`.

**Bump `timeout` from 600 → 1800.** RFD3 with 50 diffusion steps + hotspots + steering routinely takes >10 min. Make it configurable per job (`timeout=cfg.get('timeout', 1800)`) so we can shrink it later.

### 3.4 `auth.py`, `db.py`, `redis_client.py`, `runner.py`

Per the original plan. The runner becomes ~10 lines (`build job_config dict → insert job row → spawn`).

### 3.5 Steering YAML hardcoded paths

The original plan calls out 8 files in `sae/configs/steering/` with hardcoded `/mnt/nw/home/m.yu/repos/foundry/` paths. Fix is unchanged — replace each with `${oc.env:FOUNDRY_ROOT,/mnt/nw/home/m.yu/repos/foundry}/`. Verify before deploying:

```bash
grep -l '/mnt/nw' sae/configs/steering/*.yaml
```

---

## Phase 4 — Modal volume contents

Same three trees as before:

| Artifact | Volume path |
|---|---|
| RFD3 model weights | `/weights/checkpoints/rfd3` |
| SAE checkpoint | `/weights/outputs/sae/2026-04-26_15-38-55/` |
| Steering vectors | `/weights/outputs/steering/vectors/` |

`FOUNDRY_ROOT=/weights` env var is set on the worker so OmegaConf interpolations resolve. One-time upload via `api/scripts/upload_weights.py` — keep the original plan's design.

---

## Phase 5 — Auth flow on the wire

```
1. User clicks "Sign in with Google" on /auth/login
2. Browser → Supabase /auth/v1/authorize?provider=google → Google consent
3. Google → Supabase /auth/v1/callback (exchange code → JWT)
4. Supabase → /auth/callback?code=...  (Next.js route handler)
5. Route handler calls supabase.auth.exchangeCodeForSession(code)
6. Cookie set: sb-<project>-auth-token  (httpOnly, sameSite=lax)
7. Redirect to /d/generate
8. proxy.ts reads cookie → updateSession() → user found → through.
9. Server Action submitJob:
     a. createClient() reads cookie, getSession() → {user, access_token}
     b. POST Railway with Authorization: Bearer <access_token>
10. Railway auth.get_user_id verifies JWT with SUPABASE_JWT_SECRET (HS256, aud=authenticated)
    → returns user_id (sub claim)
11. Railway inserts row, spawns Modal, returns {job_id}
```

Email/password flow is identical from step 5 onward; steps 1–4 are replaced by `signInWithPassword` server action.

---

## Phase 6 — File diff summary

### Frontend (new)
| File | Purpose |
|---|---|
| `frontend/proxy.ts` | Root auth gate (Next.js 16 replaces `middleware.ts`). |
| `frontend/app/auth/login/page.tsx` | Google + email/password login. |
| `frontend/app/auth/callback/route.ts` | OAuth code exchange. |
| `frontend/app/auth/logout/route.ts` | Sign out. |
| `frontend/app/d/generate/page.tsx` | Full RFD3 design form. |
| `frontend/app/d/jobs/page.tsx` | Server-rendered job list. |
| `frontend/app/d/jobs/[id]/page.tsx` | Job detail (inputs, outputs, logs). |

### Frontend (modify)
| File | Change |
|---|---|
| `frontend/app/actions.ts` | Replace 2-arg form submission with full `JobConfig` + storage upload + Bearer token. |
| `frontend/app/api/jobs/[id]/stream/route.ts` | Forward Bearer token; reject if no session. |
| `frontend/lib/supabase/middleware.ts` | Allow `/`, `/docs/*` unauthenticated. |
| `frontend/app/d/steering/page.tsx` | Keep as-is for now; eventually fold into `/d/generate`'s steering panel. |

### Backend (new)
| File | Purpose |
|---|---|
| `api/auth.py` | FastAPI dep `get_user_id` (HS256 JWT verify against `SUPABASE_JWT_SECRET`). |
| `api/db.py` | Supabase Postgres CRUD; all queries filter by `created_by`. |
| `api/redis_client.py` | Redis pub/sub helpers. |
| `api/modal_worker.py` | GPU `run_job(job_id, job_config)`; assembles `inputs.json` + steering YAML; streams logs; uploads output. |
| `api/scripts/upload_weights.py` | One-time Modal volume population. |

### Backend (modify)
| File | Change |
|---|---|
| `api/main.py` | Add CORS origin allowlist (Vercel domain), JWT dep on every route, JSON body for `POST /jobs`, Redis-backed SSE, signed URL redirect for `/output`. |
| `api/runner.py` | ~10 lines: `build_job_config → insert_job → run_job.spawn`. |
| `api/models.py` | Add `JobConfig`, `SteeringConfig`; drop `logs` from `Job`; add `output_url`. |
| `api/store.py` | **Delete.** |
| `sae/configs/steering/ablate_block12_f639*.yaml` (×4) | Replace hardcoded path. |
| `sae/configs/steering/rawdiff_neg_block12_c*.yaml` (×4) | Replace hardcoded path. |

---

## Implementation order

1. **Supabase**: tables, buckets, Google OAuth provider, env vars.
2. **Steering YAMLs**: replace 8 hardcoded paths.
3. **Modal volume**: upload RFD3 + SAE + steering vectors.
4. **`modal_worker.py`**: hand-test with `modal run` using a fixed `JobConfig`.
5. **Backend**: `auth.py`, `db.py`, `redis_client.py`, then rewrite `main.py` + `runner.py`, delete `store.py`. Smoke test against Modal end-to-end.
6. **Railway**: deploy with new env vars + Redis addon.
7. **Frontend auth**: `proxy.ts`, `/auth/login`, `/auth/callback`, `/auth/logout`. Verify redirects + cookie set.
8. **Frontend `/d/generate`**: rebuild form using existing `/d/steering` event-stream hook structure as the template; widen the form fields to the full `JobConfig`.
9. **Frontend `/d/jobs` + `/d/jobs/[id]`**: server-rendered list; live SSE on detail when running.
10. **Wire auth header**: update `actions.ts` and `app/api/jobs/[id]/stream/route.ts` to forward Bearer token.
11. **Vercel deploy**: set env vars, add `<domain>` to Supabase auth redirect allowlist + Google OAuth origins.
12. **End-to-end smoke test**: login with Google → upload `4zxb_cropped.pdb` → set contigs `40-120,/0,E6-155` + hotspots `E64:CD2+CZ` + steps 15 + alpha 0 → Run → watch logs → 3D output downloads → row visible in `/d/jobs`.

---

## Open questions

- **3D viewer in `/d/jobs/[id]`**: `mol*` is the gold standard but heavy; `3dmol.js` is lighter. Defer past MVP — start with download link.
- **Log persistence**: Redis pubsub doesn't store history. If user reopens `/d/jobs/[id]` mid-run after a refresh, they'll only see logs from now on. Fix later by buffering to a Redis list (`LPUSH logs:{job_id}` + `LTRIM 0 999`) and replaying on subscribe, or by writing logs to Supabase Storage on completion.
- **Concurrent job limits**: nothing today caps the number of jobs a user can spawn. Add a simple `count(*) where status in ('pending','running') and created_by = ?` check before spawn.
- **Cost ceiling**: A10G on Modal is ~$1.10/hr. A 30-min job is ~$0.55. Add per-user monthly cap before opening to external researchers.
