'use client'

import { useCallback, useState } from 'react'
import { submitJob } from '@/app/actions'
import { DEFAULT_FORM, type GenerateForm, parseHotspots } from './types'
import { GenerateInputs } from './GenerateInputs'
import { JobStatusCard } from './JobStatusCard'
import { useJobStream } from './useJobStream'

export default function GeneratePage() {
  const [form, setForm] = useState<GenerateForm>(DEFAULT_FORM)
  const [jobId, setJobId] = useState<string | null>(null)
  const stream = useJobStream()

  const updateForm = useCallback(
    <K extends keyof GenerateForm>(key: K, value: GenerateForm[K]) =>
      setForm((prev) => ({ ...prev, [key]: value })),
    [],
  )

  const run = useCallback(async () => {
    stream.reset()
    setJobId(null)
    stream.setStatus('submitting')
    try {
      const motifPayload = form.motif
        ? { name: form.motif.name, bytes: await form.motif.arrayBuffer() }
        : null
      const { job_id } = await submitJob(
        {
          design_name: form.designName,
          diffusion_steps: form.diffusionSteps,
          contig: form.contig.trim() || null,
          length: form.length.trim() || null,
          hotspots: parseHotspots(form.hotspots),
          infer_ori_strategy: form.inferOriStrategy,
          is_non_loopy: form.isNonLoopy,
          partial_t: form.partialT,
          steering: form.steeringEnabled
            ? { feature_id: form.steeringFeatureId, alpha: form.steeringAlpha, apply_at_steps: 'all' }
            : null,
        },
        motifPayload,
      )
      setJobId(job_id)
      stream.setStatus('pending')
      stream.open(job_id)
    } catch (exc) {
      stream.setStatus('failed')
      stream.setError(String(exc))
    }
  }, [form, stream])

  const busy = ['submitting', 'pending', 'running'].includes(stream.status)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 px-4 py-8 max-w-6xl mx-auto">
      <div className="flex flex-col gap-6">
        <h1 className="text-lg font-semibold">Design</h1>
        <GenerateInputs form={form} update={updateForm} />
        <button
          onClick={run} disabled={busy}
          className="h-10 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 disabled:opacity-40"
        >
          {busy ? 'Running…' : 'Run'}
        </button>
      </div>
      <div className="flex flex-col gap-6">
        <h2 className="text-sm font-medium text-zinc-500">Output</h2>
        <JobStatusCard jobId={jobId} status={stream.status} error={stream.error} logs={stream.logs} />
        {stream.status === 'done' && jobId && (
          <a
            href={`/api/jobs/${jobId}/output`}
            className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-200 dark:border-zinc-700 px-4 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800"
          >
            Download .cif.gz
          </a>
        )}
      </div>
    </div>
  )
}
