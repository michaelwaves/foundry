export type Status = 'idle' | 'submitting' | 'pending' | 'running' | 'done' | 'failed'

export type InferOriStrategy = 'hotspots' | 'none'

export type GenerateMode = 'standard' | 'symmetric'

export const SYMMETRY_OPTIONS = [
  'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C12',
  'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8',
] as const

export type SymmetryId = (typeof SYMMETRY_OPTIONS)[number]

export type GenerateForm = {
  mode: GenerateMode
  designName: string
  motif: File | null
  diffusionSteps: number
  partialT: number
  length: string
  isNonLoopy: boolean
  steeringEnabled: boolean
  steeringFeatureId: number
  steeringAlpha: number
  contig: string
  hotspots: string
  inferOriStrategy: InferOriStrategy
  symmetryId: SymmetryId
  isUnsymMotif: string
}

export const DEFAULT_FORM: GenerateForm = {
  mode: 'standard',
  designName: 'design_001',
  motif: null,
  diffusionSteps: 15,
  partialT: 0,
  length: '190-270',
  isNonLoopy: true,
  steeringEnabled: false,
  steeringFeatureId: 639,
  steeringAlpha: 0,
  contig: '',
  hotspots: '',
  inferOriStrategy: 'hotspots',
  symmetryId: 'C5',
  isUnsymMotif: '',
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
