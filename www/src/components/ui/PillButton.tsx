export default function PillButton({
  variant = 'primary',
  type = 'button',
  disabled,
  onClick,
  className = '',
  children,
}: {
  variant?: 'primary' | 'ghost'
  type?: 'button' | 'submit'
  disabled?: boolean
  onClick?: () => void
  className?: string
  children: React.ReactNode
}) {
  const primary = variant === 'primary'
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center px-8 transition disabled:opacity-50 ${className}`}
      style={{
        height: 'var(--ss-btn-h)',
        borderRadius: 'var(--ss-btn-r)',
        fontSize: 'var(--ss-btn-label)',
        background: primary ? 'var(--ss-accent)' : 'transparent',
        color: primary ? 'var(--ss-bg)' : 'var(--ss-fg)',
        border: primary ? 'none' : '1px solid var(--ss-glass-border)',
      }}
    >
      {children}
    </button>
  )
}
