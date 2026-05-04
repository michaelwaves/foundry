import type { GenerateForm } from './types'

type Props = {
  form: GenerateForm
  update: <K extends keyof GenerateForm>(key: K, value: GenerateForm[K]) => void
}

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

      <Field label="Target protein (PDB)" hint="Leave empty for de novo design">
        <input
          type="file" accept=".pdb"
          onChange={(e) => update('motif', e.target.files?.[0] ?? null)}
          className="text-sm text-muted-foreground file:mr-3 file:rounded-md file:border-0 file:bg-brand-orange/10 file:text-brand-orange file:px-3 file:py-1.5 file:text-xs file:font-medium hover:file:bg-brand-orange/20 file:cursor-pointer"
        />
      </Field>

      <Field label="Contigs" hint="e.g. 40-120,/0,E6-155">
        <input
          type="text" value={form.contig} placeholder="40-120,/0,E6-155"
          onChange={(e) => update('contig', e.target.value)}
          className={INPUT_BASE}
        />
      </Field>

      <Field label="Length range" hint="e.g. 190-270">
        <input
          type="text" value={form.length}
          onChange={(e) => update('length', e.target.value)}
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
