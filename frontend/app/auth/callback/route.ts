import { NextResponse, type NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  const next = url.searchParams.get('next') ?? '/d/generate'

  if (!code) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }
  const supabase = await createClient()
  const { error } = await supabase.auth.exchangeCodeForSession(code)
  if (error) {
    const errorUrl = new URL('/auth/login', request.url)
    errorUrl.searchParams.set('error', error.message)
    return NextResponse.redirect(errorUrl)
  }
  return NextResponse.redirect(new URL(next, request.url))
}
