export default function GlassPanel({
  className = '',
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return (
    <div
      className={`relative overflow-hidden ${className}`}
      style={{
        borderRadius: 'var(--ss-radius-sheet)',
        background: 'var(--ss-glass-bg)',
        border: '1px solid var(--ss-glass-border)',
        backdropFilter: 'blur(var(--ss-glass-blur))',
        WebkitBackdropFilter: 'blur(var(--ss-glass-blur))',
      }}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, transparent 20%, rgba(255,255,255,0.9) 50%, transparent 80%, transparent 100%)',
        }}
      />
      {children}
    </div>
  )
}
