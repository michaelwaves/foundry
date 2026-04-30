'use server'

const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function submitJob(formData: FormData): Promise<{ job_id: string }> {
  const res = await fetch(`${API_URL}/jobs`, { method: 'POST', body: formData })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function downloadOutput(jobId: string): Promise<{ data: string; filename: string }> {
  const res = await fetch(`${API_URL}/jobs/${jobId}/output`)
  if (!res.ok) throw new Error(await res.text())
  const buffer = await res.arrayBuffer()
  return { data: Buffer.from(buffer).toString('base64'), filename: 'output.cif.gz' }
}
