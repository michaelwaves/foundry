import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const supabase = await createClient()
  const { data } = await supabase.auth.getSession()
  if (!data.session) return new Response('unauthorized', { status: 401 })

  const upstream = await fetch(`${API_URL}/jobs/${id}/output`, {
    redirect: 'manual',
    headers: { Authorization: `Bearer ${data.session.access_token}` },
  })
  const location = upstream.headers.get('location')
  if (upstream.status >= 300 && upstream.status < 400 && location) {
    return NextResponse.redirect(location, 302)
  }
  return new Response(await upstream.text(), { status: upstream.status })
}
