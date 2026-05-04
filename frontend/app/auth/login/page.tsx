'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

type Mode = 'signin' | 'signup'

export default function LoginPage() {
  const supabase = createClient()
  const router = useRouter()
  const searchParams = useSearchParams()
  const next = searchParams.get('next') ?? '/d/generate'

  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submitEmailPassword = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setBusy(true)
    const action = mode === 'signin'
      ? supabase.auth.signInWithPassword({ email, password })
      : supabase.auth.signUp({ email, password })
    const { error: authError } = await action
    setBusy(false)
    if (authError) {
      setError(authError.message)
      return
    }
    router.push(next)
    router.refresh()
  }

  const signInWithGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}` },
    })
  }

  return (
    <div className="flex items-start justify-center py-16 px-4">
      <div className="w-full max-w-sm flex flex-col gap-6">
        <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          {mode === 'signin' ? 'Sign in' : 'Create account'}
        </h1>

        <button
          onClick={signInWithGoogle}
          className="h-10 rounded-lg border border-zinc-200 dark:border-zinc-700 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800"
        >
          Continue with Google
        </button>

        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
          or
          <div className="flex-1 h-px bg-zinc-200 dark:bg-zinc-800" />
        </div>

        <form onSubmit={submitEmailPassword} className="flex flex-col gap-3">
          <input
            type="email" placeholder="email" value={email} required
            onChange={(e) => setEmail(e.target.value)}
            className="h-10 rounded-lg border border-zinc-200 dark:border-zinc-700 px-3 text-sm bg-transparent"
          />
          <input
            type="password" placeholder="password" value={password} required
            onChange={(e) => setPassword(e.target.value)}
            className="h-10 rounded-lg border border-zinc-200 dark:border-zinc-700 px-3 text-sm bg-transparent"
          />
          <button
            type="submit" disabled={busy}
            className="h-10 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 disabled:opacity-40"
          >
            {busy ? '…' : mode === 'signin' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <button
          onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
          className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
        >
          {mode === 'signin' ? 'No account? Create one' : 'Have an account? Sign in'}
        </button>

        {error && (
          <p className="rounded-lg bg-red-50 dark:bg-red-950 px-3 py-2 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
