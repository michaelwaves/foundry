'use client'

import Image from 'next/image'
import { useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'

export default function LoginForm() {
  const supabase = createClient()
  const searchParams = useSearchParams()
  const next = searchParams.get('next') ?? '/d/generate'

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
          <h1 className="font-heading text-xl text-foreground mt-1">Welcome</h1>
          <p className="text-xs text-muted-foreground">Sign in to continue.</p>
        </header>

        <Button onClick={signInWithGoogle} variant="outline" size="lg" className="w-full">
          Continue with Google
        </Button>
      </div>
    </div>
  )
}
