'use client'

import { useCallback, useState } from 'react'
import { Download } from 'lucide-react'
import { submitJob } from '@/app/actions'
import { Button } from '@/components/ui/button'
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
    <div className="px-8 py-10 max-w-6xl mx-auto">
      <header className="mb-8">
        <h1 className="font-heading text-4xl text-foreground tracking-tight">Design</h1>
        <p className="text-sm text-muted-foreground mt-1">Configure inputs and run a new diffusion job.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div className="flex flex-col gap-5">
          <GenerateInputs form={form} update={updateForm} />
          <Button onClick={run} disabled={busy} size="lg" className="mt-2">
            {busy ? 'Running…' : 'Run'}
          </Button>
        </div>

        <div className="flex flex-col gap-5">
          <h2 className="font-heading text-xl text-foreground">Output</h2>
          <JobStatusCard jobId={jobId} status={stream.status} error={stream.error} logs={stream.logs} />
          {stream.status === 'done' && jobId && (
            <Button asChild variant="outline" size="lg" className="w-fit">
              <a href={`/api/jobs/${jobId}/output`}>
                <Download />
                Download .cif.gz
              </a>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
