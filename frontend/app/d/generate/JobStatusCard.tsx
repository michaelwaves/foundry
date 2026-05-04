import type { Status } from './types'

export function JobStatusCard({
  jobId,
  status,
  error,
  logs,
}: {
  jobId: string | null
  status: Status
  error: string | null
  logs: string[]
}) {
  if (!jobId) return null
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-muted/30 p-4">
        <span className="font-mono text-xs text-muted-foreground">{jobId}</span>
        <span className="text-sm text-foreground">
          Status: <span className={statusClass(status)}>{status}</span>
        </span>
      </div>
      {logs.length > 0 && (
        <div className="rounded-lg border border-border bg-zinc-950 p-3 max-h-72 overflow-y-auto">
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap break-all leading-5 font-mono">
            {logs.join('\n')}
          </pre>
        </div>
      )}
      {error && (
        <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

function statusClass(status: Status): string {
  if (status === 'done') return 'font-semibold text-[#5a7a2a]'
  if (status === 'failed') return 'font-semibold text-destructive'
  if (status === 'running') return 'font-semibold text-brand-blue'
  return 'font-semibold text-brand-orange'
}
