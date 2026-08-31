/** 앱의 BrandMark.letterSpacingFor 와 같은 공식. 크기가 바뀌어도 같은 글자로 읽혀야 한다. */
export function letterSpacingFor(size: number): number {
  return (size * 1.2) / 44
}

export default function BrandMark({
  size = 34,
  className = '',
  color = 'var(--ss-accent)',
}: {
  size?: number
  className?: string
  /** 밝은 바탕 위(선수 카드)에서는 강조색 대신 검게 찍어야 읽힌다. */
  color?: string
}) {
  return (
    <span
      // 인트로가 끝날 때 워드마크가 날아와 앉는 자리다 — GlitchIntro 가 이
      // 표식으로 목적지를 찾는다. 화면에 둘 이상 있으면(반응형으로 크기가
      // 다른 사본) 실제로 보이는 것 하나를 고른다.
      data-brand-mark=""
      className={`select-none ${className}`}
      style={{
        fontFamily: 'var(--font-rubik-glitch)',
        fontSize: `${size}px`,
        letterSpacing: `${letterSpacingFor(size)}px`,
        color,
        lineHeight: 1,
      }}
    >
      SUPERSUB
    </span>
  )
}
