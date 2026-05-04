'use client'

import { useEffect, useRef, useState } from 'react'

export function LiveLogs({ jobId }: { jobId: string }) {
  const [logs, setLogs] = useState<string[]>([])
  const [terminalStatus, setTerminalStatus] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const source = new EventSource(`/api/jobs/${jobId}/stream`)
    source.addEventListener('log', (event) => {
      setLogs((prev) => [...prev, JSON.parse((event as MessageEvent).data)])
    })
    source.addEventListener('status', (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      if (data.status === 'done' || data.status === 'failed') {
        setTerminalStatus(data.status)
        source.close()
      }
    })
    source.onerror = () => source.close()
    return () => source.close()
  }, [jobId])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <section>
      <h2 className="text-sm font-medium text-zinc-500 mb-2">Logs</h2>
      <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-950 p-3 max-h-96 overflow-y-auto">
        <pre className="text-xs text-zinc-300 whitespace-pre-wrap break-all leading-5">
          {logs.join('\n') || 'waiting…'}
        </pre>
        <div ref={endRef} />
      </div>
      {terminalStatus && (
        <p className="text-xs text-zinc-500 mt-2">
          Stream ended ({terminalStatus}). Refresh to see final state.
        </p>
      )}
    </section>
  )
}
