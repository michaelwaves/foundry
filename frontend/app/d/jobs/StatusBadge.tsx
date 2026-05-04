const STYLES: Record<string, string> = {
  pending: 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300',
  running: 'bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300',
  done: 'bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300',
  failed: 'bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300',
}

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? STYLES.pending
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${style}`}>
      {status}
    </span>
  )
}
