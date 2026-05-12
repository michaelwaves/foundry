import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Download } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { Button } from '@/components/ui/button'
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
    <div className="px-8 py-10 max-w-3xl mx-auto flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <Link href="/d/jobs" className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-brand-orange transition-colors w-fit">
          <ArrowLeft className="h-3 w-3" />
          All jobs
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-heading text-3xl tracking-tight font-mono break-all">{id}</h1>
            <p className="text-xs text-muted-foreground mt-1">{new Date(job.created_at).toLocaleString()}</p>
          </div>
          <StatusBadge status={job.status} />
        </div>
      </header>

      {job.error && (
        <pre className="rounded-lg bg-destructive/10 p-4 text-xs text-destructive whitespace-pre-wrap font-mono">
          {job.error}
        </pre>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="font-heading text-lg text-foreground">Inputs</h2>
        <pre className="rounded-lg border border-border bg-muted/30 p-4 text-xs overflow-x-auto font-mono">
          {JSON.stringify(job.inputs, null, 2)}
        </pre>
      </section>

      {(job.status === 'running' || job.status === 'pending') && <LiveLogs jobId={id} />}

      {job.status === 'done' && (
        <>
          <iframe
            src={`/molstar?url=${encodeURIComponent(`/api/jobs/${id}/cif`)}`}
            className="w-full h-[500px] border-0 rounded-lg"
            title="Protein structure viewer"
          />
          <Button asChild variant="outline" size="lg" className="w-fit">
            <a href={`/api/jobs/${id}/output`}>
              <Download />
              Download .cif.gz
            </a>
          </Button>
        </>
      )}
    </div>
  )
}
