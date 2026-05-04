'use server'

import { createClient } from '@/lib/supabase/server'

const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export type SteeringInput = {
  feature_id: number
  alpha: number
  apply_at_steps: string
}

export type SymmetryInput = {
  id: string
  is_unsym_motif: string | null
}

export type JobInput = {
  design_name: string
  diffusion_steps: number
  contig: string | null
  length: string | null
  hotspots: Record<string, string>
  infer_ori_strategy: string
  is_non_loopy: boolean
  partial_t: number
  steering: SteeringInput | null
  symmetry: SymmetryInput | null
  disable_zeus: boolean
}

export async function submitJob(
  input: JobInput,
  motif: { name: string; bytes: ArrayBuffer } | null,
): Promise<{ job_id: string }> {
  const { accessToken, userId } = await requireSession()
  const pdbStoragePath = motif ? await uploadMotif(userId, motif) : null

  const response = await fetch(`${API_URL}/jobs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ ...input, pdb_storage_path: pdbStoragePath }),
  })
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}


async function requireSession(): Promise<{ accessToken: string; userId: string }> {
  const supabase = await createClient()
  const { data: userData, error: userError } = await supabase.auth.getUser()
  if (userError || !userData.user) throw new Error('not authenticated')
  const { data: sessionData } = await supabase.auth.getSession()
  if (!sessionData.session) throw new Error('not authenticated')
  return { accessToken: sessionData.session.access_token, userId: userData.user.id }
}

async function uploadMotif(
  userId: string,
  motif: { name: string; bytes: ArrayBuffer },
): Promise<string> {
  const supabase = await createClient()
  const path = `${userId}/${crypto.randomUUID()}.pdb`
  const { error } = await supabase.storage
    .from('inputs')
    .upload(path, motif.bytes, { contentType: 'chemical/x-pdb', upsert: false })
  if (error) throw error
  return path
}
