export type Status = 'idle' | 'submitting' | 'pending' | 'running' | 'done' | 'failed'

export type GenerateForm = {
  designName: string
  motif: File | null
  contig: string
  length: string
  hotspots: string
  diffusionSteps: number
  isNonLoopy: boolean
  partialT: number
  steeringEnabled: boolean
  steeringFeatureId: number
  steeringAlpha: number
}

export const DEFAULT_FORM: GenerateForm = {
  designName: 'design_001',
  motif: null,
  contig: '',
  length: '100-150',
  hotspots: '',
  diffusionSteps: 15,
  isNonLoopy: true,
  partialT: 0,
  steeringEnabled: false,
  steeringFeatureId: 639,
  steeringAlpha: 0,
}

export function parseHotspots(raw: string): Record<string, string> {
  if (!raw.trim()) return {}
  const result: Record<string, string> = {}
  for (const entry of raw.split(/[;\n,]/).map((s) => s.trim()).filter(Boolean)) {
    const [residue, atoms] = entry.split(':').map((s) => s.trim())
    if (residue) result[residue] = atoms ? atoms.split('+').map((s) => s.trim()).join(',') : ''
  }
  return result
}
