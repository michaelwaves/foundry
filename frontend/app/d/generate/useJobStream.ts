'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { Status } from './types'

export function useJobStream() {
  const [status, setStatus] = useState<Status>('idle')
  const [logs, setLogs] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const terminatedRef = useRef(false)

  const close = useCallback(() => {
    eventSourceRef.current?.close()
    eventSourceRef.current = null
  }, [])

  const open = useCallback((jobId: string) => {
    close()
    terminatedRef.current = false
    setLogs([])
    setError(null)
    const source = new EventSource(`/api/jobs/${jobId}/stream`)
    eventSourceRef.current = source
    source.addEventListener('status', (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      setStatus(data.status as Status)
      if (data.status === 'done' || data.status === 'failed') {
        terminatedRef.current = true
        source.close()
        if (data.status === 'failed') setError(data.error ?? 'job failed')
      }
    })
    source.addEventListener('log', (event) => {
      setLogs((prev) => [...prev, JSON.parse((event as MessageEvent).data)])
    })
    source.onerror = () => {
      source.close()
      if (!terminatedRef.current) {
        setStatus('failed')
        setError('stream connection lost')
      }
    }
  }, [close])

  useEffect(() => () => close(), [close])

  const reset = useCallback(() => {
    close()
    setStatus('idle')
    setLogs([])
    setError(null)
  }, [close])

  return { status, setStatus, logs, error, setError, open, close, reset }
}
