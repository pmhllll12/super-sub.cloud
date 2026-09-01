// flutter/lib/core/widgets/figure_background.dart 를 옮긴 것. 홈과 영상 분석이 같은 걸 쓴다.
//
// 화면 위쪽 88% 에 사진을 깔고(BoxFit.cover) 그 위에 아래로 갈수록 검게
// 잦아드는 막을 덮어 사진의 아랫변이 선으로 보이지 않게 지운다. 정지
// 상태 — 마우스를 움직여도 배경 사진은 그대로다(사용자 요청: "배경
// 사진은 안 움직이게 하자" — 예전엔 홈 화면에서 아주 미세한 마우스
// 시차를 얹으려고 forwardRef 로 ref 를 받았지만, 배경을 고정하기로 하며
// 그 ref 를 쓰는 곳이 없어져 걷어냈다. 워드마크·카드 층은 계속
// 움직인다 — 배경만 고정되면 오히려 그 층들이 떠 있는 느낌이 산다).
//
// 🔴 **이 두 값은 CSS 변수로 나가 있다**(--ss-figure-h · --ss-figure-pos,
// globals.css). 영상 분석 화면의 큰 글자가 이 사진의 밝기를 **마스크로** 써서
// 인물 그림자 뒤로 들어가는데, 상자 크기와 자르는 기준이 사진과 **한 픽셀도
// 어긋나면 안 되기 때문**이다. 여기서만 고치면 마스크가 따로 논다.
const FIGURE_HEIGHT_PERCENT = 88

// 앱의 세로 사진은 인물이 진짜 왼쪽 가장자리에 있어 Alignment.centerLeft(0%)로
// 잘라도 됐다. 이 웹용 가로 사진은 인물이 화면 가운데에서 살짝 왼쪽에 있어서,
// object-position 을 0%(완전 왼쪽)로 두면 폭이 좁은 화면에서 인물이 통째로
// 잘려 나간다. 좁은 화면에서도 얼굴이 살아 있도록 실측으로 맞춘 값이다.
const FIGURE_OBJECT_POSITION = '46% center'

/**
 * `className` 은 이 층을 **바깥에서 움직이려는** 곳을 위한 것이다 — 영상 분석
 * 화면이 왼쪽 판을 밀어 넣으면서 사진을 그만큼 오른쪽으로 옮긴다. 홈은 안 준다.
 */
export default function FigureBackground({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={className}
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
          height: `var(--ss-figure-h, ${FIGURE_HEIGHT_PERCENT}%)`,
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
            objectPosition: `var(--ss-figure-pos, ${FIGURE_OBJECT_POSITION})`,
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
}
