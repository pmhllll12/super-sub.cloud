export default function Field({
  label,
  type = 'text',
  value,
  onChange,
  required,
  minLength,
  maxLength,
  hint,
}: {
  label: string
  type?: string
  value: string
  onChange: (v: string) => void
  required?: boolean
  minLength?: number
  maxLength?: number
  hint?: string
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm text-white/60">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        minLength={minLength}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        className="bg-transparent px-4 py-3 outline-none focus:border-white/40"
        style={{
          borderRadius: '14px',
          border: '1px solid var(--ss-glass-border)',
        }}
      />
      {hint && <span className="text-xs text-white/40">{hint}</span>}
    </label>
  )
}
