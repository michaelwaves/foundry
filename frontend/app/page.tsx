'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { submitJob, downloadOutput } from './actions'

type Status = 'idle' | 'submitting' | 'pending' | 'running' | 'done' | 'failed'

export default function Home() {
  const [alpha, setAlpha] = useState(0)
  const [motif, setMotif] = useState<File | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const esRef = useRef<EventSource | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef(false)

  const closeStream = useCallback(() => {
    esRef.current?.close()
    esRef.current = null
  }, [])

  const openStream = useCallback((id: string) => {
    closeStream()
    terminalRef.current = false
    const es = new EventSource(`/api/jobs/${id}/stream`)
    esRef.current = es
    es.addEventListener('status', (e) => {
      const data = JSON.parse(e.data)
      setStatus(data.status as Status)
      if (data.status === 'done' || data.status === 'failed') {
        terminalRef.current = true
        es.close()
        if (data.status === 'failed') setError(data.error ?? 'job failed')
      }
    })
    es.addEventListener('log', (e) => {
      setLogs((prev) => [...prev, JSON.parse(e.data)])
    })
    es.onerror = () => {
      es.close()
      if (!terminalRef.current) {
        setStatus('failed')
        setError('stream connection lost')
      }
    }
  }, [closeStream])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const submit = useCallback(async () => {
    closeStream()
    setStatus('submitting')
    setJobId(null)
    setError(null)
    setLogs([])
    const form = new FormData()
    form.append('alpha', String(alpha))
    if (motif) form.append('motif', motif)
    try {
      const { job_id } = await submitJob(form)
      setJobId(job_id)
      setStatus('pending')
      openStream(job_id)
    } catch (e) {
      setStatus('failed')
      setError(String(e))
    }
  }, [alpha, motif, closeStream, openStream])

  const download = useCallback(async () => {
    if (!jobId) return
    const { data, filename } = await downloadOutput(jobId)
    const bytes = Uint8Array.from(atob(data), (c) => c.charCodeAt(0))
    const url = URL.createObjectURL(new Blob([bytes], { type: 'application/gzip' }))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }, [jobId])

  const busy = status === 'submitting' || status === 'pending' || status === 'running'
  const alphaLabel =
    alpha > 0 ? `+${alpha} → hazard` : alpha < 0 ? `${alpha} → benign` : '0 (baseline)'

  return (
    <div className="flex items-start justify-center py-16 px-4">
      <div className="w-full max-w-md flex flex-col gap-6">
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Hazard Steering Demo
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">RFD3 + SAE feature 639 · AUROC 0.815</p>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Alpha:{' '}
            <span className="font-mono text-zinc-900 dark:text-zinc-100">{alphaLabel}</span>
          </label>
          <input
            type="range" min={-10} max={10} step={0.5} value={alpha}
            onChange={(e) => setAlpha(Number(e.target.value))}
            className="w-full accent-zinc-900 dark:accent-white"
          />
          <div className="flex justify-between text-xs text-zinc-400">
            <span>−10 benign</span><span>0</span><span>+10 hazard</span>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Motif PDB{' '}
            <span className="font-normal text-zinc-400">(optional — de novo if omitted)</span>
          </label>
          <input
            type="file" accept=".pdb"
            onChange={(e) => setMotif(e.target.files?.[0] ?? null)}
            className="text-sm text-zinc-600 dark:text-zinc-400 file:mr-3 file:rounded file:border-0 file:bg-zinc-100 file:px-3 file:py-1 file:text-xs file:font-medium dark:file:bg-zinc-800 dark:file:text-zinc-300"
          />
        </div>

        <button
          onClick={submit} disabled={busy}
          className="h-10 w-full rounded-lg bg-zinc-900 dark:bg-zinc-50 text-sm font-medium text-white dark:text-zinc-900 transition-colors hover:bg-zinc-700 dark:hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? 'Running…' : 'Run'}
        </button>

        {jobId && (
          <div className="flex flex-col gap-1 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-3 text-sm">
            <span className="font-mono text-xs text-zinc-400">{jobId}</span>
            <span className="text-zinc-700 dark:text-zinc-300">
              Status:{' '}
              <span className={
                status === 'done' ? 'font-medium text-green-600 dark:text-green-400'
                : status === 'failed' ? 'font-medium text-red-500'
                : 'font-medium text-zinc-900 dark:text-zinc-100'
              }>{status}</span>
            </span>
          </div>
        )}

        {logs.length > 0 && (
          <div className="rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-950 p-3 max-h-56 overflow-y-auto">
            <pre className="text-xs text-zinc-300 whitespace-pre-wrap break-all leading-5">
              {logs.join('\n')}
            </pre>
            <div ref={logEndRef} />
          </div>
        )}

        {status === 'done' && (
          <button
            onClick={download}
            className="flex h-10 w-full items-center justify-center rounded-lg border border-zinc-200 dark:border-zinc-700 text-sm font-medium text-zinc-700 dark:text-zinc-300 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800"
          >
            Download output.cif.gz
          </button>
        )}

        {error && (
          <p className="rounded-lg bg-red-50 dark:bg-red-950 px-3 py-2 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
