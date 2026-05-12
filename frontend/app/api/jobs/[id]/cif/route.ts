import { gunzip } from 'zlib'
import { promisify } from 'util'
import { createClient } from '@/lib/supabase/server'

const gunzipAsync = promisify(gunzip)
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

  const response = await fetch(`${API_URL}/jobs/${id}/output`, {
    redirect: 'follow',
    headers: { Authorization: `Bearer ${sessionData.session.access_token}` },
  })
  if (!response.ok) return new Response('not found', { status: 404 })

  const compressed = Buffer.from(await response.arrayBuffer())
  const decompressed = await gunzipAsync(compressed)

  return new Response(decompressed, {
    headers: { 'Content-Type': 'chemical/x-mmcif' },
  })
}
