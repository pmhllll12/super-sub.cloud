import { forwardRef } from 'react'

// flutter/lib/core/widgets/figure_background.dart 를 옮긴 것. 홈과 영상 분석이 같은 걸 쓴다.
//
// 화면 위쪽 88% 에 사진을 깔고(BoxFit.cover) 그 위에 아래로 갈수록 검게
// 잦아드는 막을 덮어 사진의 아랫변이 선으로 보이지 않게 지운다. 앱과 달리
// 그 자체로는 애니메이션이 없다 — 정지 상태가 기본이다. 홈 화면만 이 위에
// 아주 미세한 마우스 시차를 얹으려고 ref 를 받는다(forwardRef): ref 가 있으면
// HomeParallax 가 이 컴포넌트의 최상위 div 에 transform 을 직접 써서 배경을
// 살짝 움직인다. ref 를 안 주는 화면(영상 분석 등)은 원래대로 가만히 있다.
const FIGURE_HEIGHT_PERCENT = 88

// 앱의 세로 사진은 인물이 진짜 왼쪽 가장자리에 있어 Alignment.centerLeft(0%)로
// 잘라도 됐다. 이 웹용 가로 사진은 인물이 화면 가운데에서 살짝 왼쪽에 있어서,
// object-position 을 0%(완전 왼쪽)로 두면 폭이 좁은 화면에서 인물이 통째로
// 잘려 나간다. 좁은 화면에서도 얼굴이 살아 있도록 실측으로 맞춘 값이다.
const FIGURE_OBJECT_POSITION = '46% center'

const FigureBackground = forwardRef<HTMLDivElement>(function FigureBackground(_props, ref) {
  return (
    <div
      ref={ref}
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: -1,
        overflow: 'hidden',
        pointerEvents: 'none',
        background: 'var(--ss-bg)',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: `${FIGURE_HEIGHT_PERCENT}%`,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- 장식용 고정 배경, next/image 의 LCP 추정 대상이 되지 않도록 평범한 img 로 둔다 */}
        <img
          src="/home_figure.jpg"
          alt=""
          fetchPriority="high"
          decoding="async"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: FIGURE_OBJECT_POSITION,
          }}
        />
        {/* 사진 자체도 아래로 갈수록 어둡지만 딱 떨어지지 않아, 이 막이 나머지를 지운다. */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(to bottom, transparent 62%, color-mix(in srgb, var(--ss-bg) 30%, transparent) 88%, var(--ss-bg) 100%)`,
          }}
        />
      </div>
    </div>
  )
})

export default FigureBackground
