/** 앱의 BrandMark.letterSpacingFor 와 같은 공식. 크기가 바뀌어도 같은 글자로 읽혀야 한다. */
export function letterSpacingFor(size: number): number {
  return (size * 1.2) / 44
}

export default function BrandMark({
  size = 34,
  className = '',
}: {
  size?: number
  className?: string
}) {
  return (
    <span
      className={`select-none ${className}`}
      style={{
        fontFamily: 'var(--font-rubik-glitch)',
        fontSize: `${size}px`,
        letterSpacing: `${letterSpacingFor(size)}px`,
        color: 'var(--ss-accent)',
        lineHeight: 1,
      }}
    >
      SUPERSUB
    </span>
  )
}
