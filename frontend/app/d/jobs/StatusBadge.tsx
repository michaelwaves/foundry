const STYLES: Record<string, string> = {
  pending: 'bg-brand-orange/10 text-brand-orange',
  running: 'bg-brand-blue/15 text-brand-blue',
  done: 'bg-brand-green/30 text-[#5a7a2a]',
  failed: 'bg-destructive/10 text-destructive',
}

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? STYLES.pending
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${style}`}>
      {status}
    </span>
  )
}
