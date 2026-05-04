'use client'

import Image from 'next/image'
import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'

type Mode = 'signin' | 'signup'

const INPUT_BASE =
  'h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none transition-colors focus:border-brand-orange focus:ring-2 focus:ring-brand-orange/20'

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
    <div className="min-h-dvh flex items-center justify-center px-4 bg-gradient-to-br from-brand-orange/5 via-background to-brand-green/10">
      <div className="w-full max-w-sm flex flex-col gap-7 rounded-2xl border border-border bg-card p-8 shadow-sm">
        <header className="flex flex-col items-center gap-2 text-center">
          <Image src="/logo.svg" alt="Raft Bioworks" width={68} height={64} priority />
          <span className="font-heading text-3xl text-brand-orange tracking-tight">Raft Bioworks</span>
          <h1 className="font-heading text-xl text-foreground mt-1">
            {mode === 'signin' ? 'Welcome back' : 'Create your account'}
          </h1>
          <p className="text-xs text-muted-foreground">
            {mode === 'signin' ? 'Sign in to continue.' : 'Start designing proteins in minutes.'}
          </p>
        </header>

        <Button onClick={signInWithGoogle} variant="outline" size="lg" className="w-full">
          Continue with Google
        </Button>

        <div className="flex items-center gap-3 text-xs uppercase tracking-wide text-muted-foreground">
          <div className="flex-1 h-px bg-border" />
          or
          <div className="flex-1 h-px bg-border" />
        </div>

        <form onSubmit={submitEmailPassword} className="flex flex-col gap-3">
          <input
            type="email" placeholder="email" value={email} required
            onChange={(e) => setEmail(e.target.value)}
            className={INPUT_BASE}
          />
          <input
            type="password" placeholder="password" value={password} required
            onChange={(e) => setPassword(e.target.value)}
            className={INPUT_BASE}
          />
          <Button type="submit" disabled={busy} size="lg" className="mt-1">
            {busy ? '…' : mode === 'signin' ? 'Sign in' : 'Create account'}
          </Button>
        </form>

        <button
          type="button"
          onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
          className="text-xs text-muted-foreground hover:text-brand-orange transition-colors text-center cursor-pointer"
        >
          {mode === 'signin' ? 'No account? Create one' : 'Have an account? Sign in'}
        </button>

        {error && (
          <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
