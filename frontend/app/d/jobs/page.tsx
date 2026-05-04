import Link from 'next/link'
import { Plus } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { Button } from '@/components/ui/button'
import { StatusBadge } from './StatusBadge'

type JobRow = {
  id: string
  status: string
  created_at: string
  inputs: { design_name?: string }
}

export default async function JobsPage() {
  const supabase = await createClient()
  const { data: jobs } = await supabase
    .from('jobs')
    .select('id, status, created_at, inputs')
    .order('created_at', { ascending: false })
    .limit(100)

  const rows = (jobs ?? []) as JobRow[]

  return (
    <div className="px-8 py-10 max-w-5xl mx-auto">
      <header className="flex items-end justify-between mb-8">
        <div>
          <h1 className="font-heading text-4xl text-foreground tracking-tight">Jobs</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {rows.length === 0 ? 'No jobs yet.' : `${rows.length} job${rows.length === 1 ? '' : 's'}`}
          </p>
        </div>
        <Button asChild size="lg">
          <Link href="/d/generate">
            <Plus />
            New
          </Link>
        </Button>
      </header>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-brand-green/40 bg-brand-green/10 p-10 text-center">
          <p className="text-sm text-muted-foreground">
            Run a new design from <Link href="/d/generate" className="text-brand-orange hover:underline">Generate</Link>.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="text-left font-medium px-4 py-3">Design</th>
                <th className="text-left font-medium px-4 py-3">Status</th>
                <th className="text-left font-medium px-4 py-3">Submitted</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {rows.map((job) => (
                <tr key={job.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{job.inputs?.design_name ?? '—'}</td>
                  <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                  <td className="px-4 py-3 text-muted-foreground">{new Date(job.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/d/jobs/${job.id}`} className="text-xs font-medium text-brand-orange hover:underline">
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
