import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const supabase = await createClient()
  const { data: userData } = await supabase.auth.getUser()
  if (!userData.user) return new Response('unauthorized', { status: 401 })
  const { data: sessionData } = await supabase.auth.getSession()
  if (!sessionData.session) return new Response('unauthorized', { status: 401 })

  const upstream = await fetch(`${API_URL}/jobs/${id}/stream`, {
    cache: 'no-store',
    headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
  })
  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), { status: upstream.status })
  }
  const reader = upstream.body.getReader()
  const stream = new ReadableStream({
    async pull(controller) {
      const { done, value } = await reader.read()
      if (done) controller.close()
      else controller.enqueue(value)
    },
    cancel() { reader.cancel() },
  })
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
}
