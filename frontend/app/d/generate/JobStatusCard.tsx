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
      <div className="flex flex-col gap-1 rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 p-3 text-sm">
        <span className="font-mono text-xs text-zinc-400">{jobId}</span>
        <span className="text-zinc-700 dark:text-zinc-300">
          Status: <span className={statusClass(status)}>{status}</span>
        </span>
      </div>
      {logs.length > 0 && (
        <div className="rounded-lg border border-zinc-100 dark:border-zinc-800 bg-zinc-950 p-3 max-h-72 overflow-y-auto">
          <pre className="text-xs text-zinc-300 whitespace-pre-wrap break-all leading-5">
            {logs.join('\n')}
          </pre>
        </div>
      )}
      {error && (
        <p className="rounded-lg bg-red-50 dark:bg-red-950 px-3 py-2 text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}

function statusClass(status: Status): string {
  if (status === 'done') return 'font-medium text-green-600 dark:text-green-400'
  if (status === 'failed') return 'font-medium text-red-500'
  return 'font-medium text-zinc-900 dark:text-zinc-100'
}
