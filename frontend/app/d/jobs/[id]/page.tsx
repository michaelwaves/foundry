import { notFound } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { StatusBadge } from '../StatusBadge'
import { LiveLogs } from './LiveLogs'

type JobRow = {
  id: string
  status: string
  error: string | null
  inputs: Record<string, unknown>
  output_url: string | null
  created_at: string
}

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const supabase = await createClient()
  const { data } = await supabase
    .from('jobs')
    .select('id, status, error, inputs, output_url, created_at')
    .eq('id', id)
    .maybeSingle()

  if (!data) notFound()
  const job = data as JobRow

  return (
    <div className="px-4 py-8 max-w-3xl mx-auto flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/d/jobs" className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
            ← All jobs
          </Link>
          <h1 className="text-lg font-semibold mt-2 font-mono">{id}</h1>
          <p className="text-xs text-zinc-500">{new Date(job.created_at).toLocaleString()}</p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {job.error && (
        <pre className="rounded-lg bg-red-50 dark:bg-red-950 p-3 text-xs text-red-700 dark:text-red-400 whitespace-pre-wrap">
          {job.error}
        </pre>
      )}

      <section>
        <h2 className="text-sm font-medium text-zinc-500 mb-2">Inputs</h2>
        <pre className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-3 text-xs overflow-x-auto">
          {JSON.stringify(job.inputs, null, 2)}
        </pre>
      </section>

      {(job.status === 'running' || job.status === 'pending') && <LiveLogs jobId={id} />}

      {job.status === 'done' && (
        <a
          href={`/api/jobs/${id}/output`}
          className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-200 dark:border-zinc-700 px-4 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800 w-fit"
        >
          Download .cif.gz
        </a>
      )}
    </div>
  )
}
