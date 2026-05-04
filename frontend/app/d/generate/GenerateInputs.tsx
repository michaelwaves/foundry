import { cn } from '@/lib/utils'
import { type GenerateForm, type GenerateMode, SYMMETRY_OPTIONS } from './types'

type Update = <K extends keyof GenerateForm>(key: K, value: GenerateForm[K]) => void
type Props = { form: GenerateForm; update: Update }

const INPUT_BASE =
  'h-9 w-full rounded-md border border-border bg-background px-3 text-sm font-mono outline-none transition-colors focus:border-brand-orange focus:ring-2 focus:ring-brand-orange/20'

export function GenerateInputs({ form, update }: Props) {
  return (
    <>
      <Field label="Design name">
        <input
          type="text" value={form.designName}
          onChange={(e) => update('designName', e.target.value)}
          className={INPUT_BASE}
        />
      </Field>

      <Field label="Target protein (PDB)" hint={form.mode === 'symmetric' ? 'must be pre-symmetrized about origin' : 'leave empty for de novo'}>
        <input
          type="file" accept=".pdb"
          onChange={(e) => update('motif', e.target.files?.[0] ?? null)}
          className="text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-brand-orange/10 file:text-brand-orange file:px-3 file:py-1.5 file:text-xs file:font-medium hover:file:bg-brand-orange/20 file:cursor-pointer"
        />
      </Field>

      <Field
        label="Length"
        hint={form.mode === 'symmetric' ? 'residues per subunit, e.g. 100 or 80-120' : 'range, e.g. 190-270'}
      >
        <input
          type="text" value={form.length}
          onChange={(e) => update('length', e.target.value)}
          className={INPUT_BASE}
        />
      </Field>

      <ModeTabs mode={form.mode} onChange={(m) => update('mode', m)} />
      {form.mode === 'standard' ? <StandardInputs form={form} update={update} /> : <SymmetricInputs form={form} update={update} />}

      <RangeField
        label="Diffusion steps" value={form.diffusionSteps}
        min={1} max={50} step={1}
        onChange={(v) => update('diffusionSteps', v)}
      />

      <RangeField
        label="Partial diffusion (partial_t)" value={form.partialT}
        min={0} max={160} step={1}
        disabled={!form.motif}
        onChange={(v) => update('partialT', v)}
        hint={!form.motif ? 'requires motif' : form.partialT === 0 ? 'off' : undefined}
      />

      <SteeringPanel form={form} update={update} />
    </>
  )
}

function ModeTabs({ mode, onChange }: { mode: GenerateMode; onChange: (m: GenerateMode) => void }) {
  return (
    <div className="grid grid-cols-2 gap-1 rounded-lg border border-border bg-muted/30 p-1">
      {(['standard', 'symmetric'] as const).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={cn(
            'h-9 rounded-md text-sm font-medium capitalize transition-colors',
            mode === m
              ? 'bg-brand-orange text-white shadow-sm'
              : 'text-muted-foreground hover:bg-brand-orange/10 hover:text-brand-orange',
          )}
        >
          {m}
        </button>
      ))}
    </div>
  )
}

function StandardInputs({ form, update }: Props) {
  return (
    <>
      <Field label="Contigs" hint="e.g. 40-120,/0,E6-155">
        <input
          type="text" value={form.contig} placeholder="40-120,/0,E6-155"
          onChange={(e) => update('contig', e.target.value)}
          className={INPUT_BASE}
        />
      </Field>

      <Field
        label="Hotspot residues"
        hint={form.motif ? 'E64:CD2+CZ; E88:CG+CZ' : 'requires motif PDB'}
      >
        <input
          type="text" value={form.hotspots} placeholder="E64:CD2+CZ; E88:CG+CZ"
          disabled={!form.motif}
          onChange={(e) => update('hotspots', e.target.value)}
          className={`${INPUT_BASE} disabled:opacity-40 disabled:cursor-not-allowed`}
        />
      </Field>

      <Field label="Orientation inference" hint="how to orient the designed chain">
        <select
          value={form.inferOriStrategy}
          onChange={(e) => update('inferOriStrategy', e.target.value as 'hotspots' | 'none')}
          className={INPUT_BASE}
        >
          <option value="hotspots">hotspots (default)</option>
          <option value="none">none</option>
        </select>
      </Field>
    </>
  )
}

function SymmetricInputs({ form, update }: Props) {
  return (
    <>
      <Field label="Symmetry group" hint="Cn = cyclic, Dn = dihedral">
        <select
          value={form.symmetryId}
          onChange={(e) => update('symmetryId', e.target.value as typeof form.symmetryId)}
          className={INPUT_BASE}
        >
          {SYMMETRY_OPTIONS.map((id) => (
            <option key={id} value={id}>{id}</option>
          ))}
        </select>
      </Field>

      <Field
        label="Unsymmetrized motif"
        hint={form.motif ? 'optional contigs/ligands to leave unsymmetrized, e.g. Y1-11,Z16-25' : 'requires motif PDB'}
      >
        <input
          type="text" value={form.isUnsymMotif} placeholder="Y1-11,Z16-25"
          disabled={!form.motif}
          onChange={(e) => update('isUnsymMotif', e.target.value)}
          className={`${INPUT_BASE} disabled:opacity-40 disabled:cursor-not-allowed`}
        />
      </Field>

      <label className="flex items-center gap-2.5 text-sm font-medium cursor-pointer">
        <input
          type="checkbox" checked={form.disableZeus}
          onChange={(e) => update('disableZeus', e.target.checked)}
          className="h-4 w-4 accent-brand-orange cursor-pointer"
        />
        Disable ZeUS attention
        <span className="font-normal text-muted-foreground text-xs">fall back to full attention</span>
      </label>
    </>
  )
}

function SteeringPanel({ form, update }: Props) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-brand-green/40 bg-brand-green/10 p-4">
      <label className="flex items-center gap-2.5 text-sm font-medium cursor-pointer">
        <input
          type="checkbox" checked={form.steeringEnabled}
          onChange={(e) => update('steeringEnabled', e.target.checked)}
          className="h-4 w-4 accent-brand-orange cursor-pointer"
        />
        SAE steering
      </label>
      {form.steeringEnabled && (
        <>
          <Field label="Feature id">
            <input
              type="number" value={form.steeringFeatureId}
              onChange={(e) => update('steeringFeatureId', Number(e.target.value))}
              className={INPUT_BASE}
            />
          </Field>
          <RangeField
            label="Alpha" value={form.steeringAlpha}
            min={-10} max={10} step={0.5}
            onChange={(v) => update('steeringAlpha', v)}
            hint={form.steeringAlpha > 0 ? '→ feature' : form.steeringAlpha < 0 ? '→ anti-feature' : 'baseline'}
          />
        </>
      )}
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-foreground">
        {label}
        {hint && <span className="ml-2 font-normal text-muted-foreground">{hint}</span>}
      </label>
      {children}
    </div>
  )
}

function RangeField({
  label, value, min, max, step, onChange, disabled, hint,
}: {
  label: string; value: number; min: number; max: number; step: number
  onChange: (v: number) => void; disabled?: boolean; hint?: string
}) {
  return (
    <Field label={label} hint={hint}>
      <div className="flex items-center gap-3">
        <input
          type="range" min={min} max={max} step={step} value={value} disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 accent-brand-orange disabled:opacity-30"
        />
        <span className="font-mono text-sm w-12 text-right tabular-nums">{value}</span>
      </div>
    </Field>
  )
}
