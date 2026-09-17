import Link from 'next/link'

type BaseProps = {
  /**
   * `white` 는 **구글 버튼과 같은 결**이다(흰 바탕 · 검은 글자). 구글이 그리는
   * 버튼은 우리가 색을 못 바꾸므로, 그 옆에 나란히 서는 단추를 그 모양에
   * 맞출 때 쓴다 — 로그인 화면의 「심사위원용 로그인」이 그 자리다.
   */
  variant?: 'primary' | 'ghost' | 'white'
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
  const white = variant === 'white'
  /* 🔴 색을 **인라인으로** 넣는다 — 그래서 클래스로는 못 덮는다. 새 모양이
     필요하면 여기서 갈래를 늘린다(바깥에서 `className` 으로 덮으려 하면
     인라인이 이겨서 조용히 안 먹는다). */
  const style = {
    height: 'var(--ss-btn-h)',
    borderRadius: 'var(--ss-btn-r)',
    fontSize: 'var(--ss-btn-label)',
    background: primary ? 'var(--ss-accent)' : white ? '#ffffff' : 'transparent',
    color: primary || white ? 'var(--ss-bg)' : 'var(--ss-fg)',
    border: primary || white ? 'none' : '1px solid var(--ss-glass-border)',
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
