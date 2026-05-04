import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
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
    <div className="px-4 py-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold">Jobs</h1>
        <Link href="/d/generate" className="text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
          New →
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-zinc-500">No jobs yet. Run one from /d/generate.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="text-xs text-zinc-500 border-b border-zinc-200 dark:border-zinc-800">
            <tr>
              <th className="text-left font-medium py-2">Design</th>
              <th className="text-left font-medium py-2">Status</th>
              <th className="text-left font-medium py-2">Submitted</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((job) => (
              <tr key={job.id} className="border-b border-zinc-100 dark:border-zinc-900">
                <td className="py-2 font-mono text-xs">{job.inputs?.design_name ?? '—'}</td>
                <td className="py-2"><StatusBadge status={job.status} /></td>
                <td className="py-2 text-zinc-500">{new Date(job.created_at).toLocaleString()}</td>
                <td className="py-2 text-right">
                  <Link href={`/d/jobs/${job.id}`} className="text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
