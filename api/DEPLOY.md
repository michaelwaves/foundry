  ---
  Deploy Steps

  1. Supabase

  # from repo root
  npx supabase link --project-ref zaafausyullnzgbacnlw
  npx supabase db push   # applies
  supabase/migrations/{0001_jobs,0002_storage}.sql

  Then in Supabase Studio:
  - Authentication → Providers → Google: enable, paste OAuth client ID
  + secret. Redirect URL on the Supabase side is fixed at
  https://zaafausyullnzgbacnlw.supabase.co/auth/v1/callback.
  - Google Cloud Console → APIs & Services → Credentials → OAuth 2.0
  Client IDs → your web client:
    - Authorized JavaScript origins: http://localhost:3002,
  https://<your-vercel-domain>.
    - Authorized redirect URIs:
  https://zaafausyullnzgbacnlw.supabase.co/auth/v1/callback.
  - Settings → API Keys → Secret keys → "Create new secret key" (named
  foundry-backend). Copy the sb_secret_... value — you'll paste it into
   Railway + Modal env vars below.

  2. Modal

  modal token new                             # if not already authed
  modal secret create foundry-secrets \
    SUPABASE_URL=https://zaafausyullnzgbacnlw.supabase.co \
    SUPABASE_KEY=sb_secret_...               \
    REDIS_URL=redis://...                     # paste from Railway
  after step 3

  modal volume create foundry-weights         # if not already

  # one-time weight upload (uploads SAE locally, then triggers
  in-volume RFD3 download)
  source .venv/bin/activate
  modal run api/scripts/upload_weights.py

  3. Railway

  - Add Redis addon (New → Database → Redis). Copy the REDIS_URL it
  injects into your service — paste into the Modal secret above (re-run
   modal secret create if needed).
  - Service → Variables, add:
    - SUPABASE_URL=https://zaafausyullnzgbacnlw.supabase.co
    - SUPABASE_KEY=sb_secret_...
    - MODAL_TOKEN_ID=ak-...
    - MODAL_TOKEN_SECRET=as-...
  - Service → Settings → Triggers → Watch Paths: add api/**.
  - Push to GitHub — Railway auto-redeploys with the new
  nixpacks.toml/railway.toml inside api/.
  - After build, copy the public URL from Settings → Domains (something
   like foundry-api-production.up.railway.app).

  4. Vercel (frontend)

  - Connect repo, set root directory = frontend/.
  - Environment Variables:
    - NEXT_PUBLIC_SUPABASE_URL=https://zaafausyullnzgbacnlw.supabase.co
    - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_vq5dHs9JvGAI9
  Fof4683wA_IzwvHE4E
    - API_URL=https://<your-railway-url>
  - After first deploy, add the Vercel domain to Google OAuth's
  authorized origins (step 1).

  5. Smoke test

  http://localhost:3002 → /auth/login → Google → /d/generate
  upload tutorials/rfd3_ppi_tutorial/4zxb_cropped.pdb
  contig: 40-120,/0,E6-155
  hotspots: E64:CD2+CZ; E88:CG+CZ; E96:CD1+CZ
  steps: 15
  Run → watch logs stream → /d/jobs/{id} → download .cif.gz

  ---
  Files changed

  New backend (api/): auth.py, db.py, redis_client.py, modal_worker.py,
   worker_inputs.py, worker_steering.py, worker_logs.py,
  worker_output.py, scripts/upload_weights.py. Rewrote: models.py,
  runner.py, main.py. Deleted: store.py, cache/.

  New SQL (supabase/migrations/): 0001_jobs.sql, 0002_storage.sql.

  Frontend new: proxy.ts, app/auth/{login,callback,logout},
  app/d/page.tsx (redirect), app/d/generate/{page,GenerateInputs,JobSta
  tusCard,useJobStream,types},
  app/d/jobs/{page,StatusBadge,[id]/{page,LiveLogs}},
  app/api/jobs/[id]/output/route.ts. Modified: app/actions.ts,
  app/api/jobs/[id]/stream/route.ts, lib/supabase/middleware.ts.
  Deleted: app/d/steering/.

  Steering YAMLs: 8 files in sae/src/sae/configs/steering/ had
  hardcoded /mnt/nw/... paths; replaced with
  ${oc.env:FOUNDRY_ROOT,...}/.

  ---
  Known things to verify after first run

  1. The Modal image pip install rc-foundry[rfd3,sae,api] @
  git+https://github.com/RoseTTAFold3/foundry@modal assumes a public
  branch exists. If the repo is private or the branch name differs,
  change in api/modal_worker.py:14.
  2. The Modal image build takes ~5–10 min the first time (pulls torch,
   pymol, atomworks). Subsequent runs reuse the layer.
  3. SSE: Railway and Vercel both need to NOT buffer responses. Vercel
  should be fine via dynamic = 'force-dynamic'; Railway via
  X-Accel-Buffering: no (already set).
  4. The output_url is a 7-day signed URL written by the worker. If a
  user downloads >7 days later, regenerate (post-MVP — add
  /jobs/:id/refresh-url).
