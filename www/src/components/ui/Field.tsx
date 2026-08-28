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
      <span className="ss-field-label text-sm">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        minLength={minLength}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        className="ss-field-input bg-transparent px-4 py-3 outline-none"
        style={{
          borderRadius: 'var(--ss-field-radius)',
          border: '1px solid var(--ss-glass-border)',
        }}
      />
      {hint && <span className="ss-field-hint text-xs">{hint}</span>}
    </label>
  )
}
