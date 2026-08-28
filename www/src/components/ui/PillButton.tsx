import Link from 'next/link'

type BaseProps = {
  variant?: 'primary' | 'ghost'
  className?: string
  children: React.ReactNode
}

type ButtonProps = BaseProps & {
  href?: undefined
  type?: 'button' | 'submit'
  disabled?: boolean
  onClick?: () => void
}

type LinkProps = BaseProps & {
  href: string
  type?: undefined
  disabled?: undefined
  onClick?: undefined
}

export default function PillButton({
  variant = 'primary',
  type = 'button',
  disabled,
  onClick,
  href,
  className = '',
  children,
}: ButtonProps | LinkProps) {
  const primary = variant === 'primary'
  const style = {
    height: 'var(--ss-btn-h)',
    borderRadius: 'var(--ss-btn-r)',
    fontSize: 'var(--ss-btn-label)',
    background: primary ? 'var(--ss-accent)' : 'transparent',
    color: primary ? 'var(--ss-bg)' : 'var(--ss-fg)',
    border: primary ? 'none' : '1px solid var(--ss-glass-border)',
  }
  const sharedClassName = `inline-flex items-center justify-center px-8 transition disabled:opacity-50 ${className}`

  if (href) {
    return (
      <Link href={href} className={sharedClassName} style={style}>
        {children}
      </Link>
    )
  }

  return (
    <button type={type} disabled={disabled} onClick={onClick} className={sharedClassName} style={style}>
      {children}
    </button>
  )
}
