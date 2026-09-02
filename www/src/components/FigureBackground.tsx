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
 * 배경 글자를 앉히는 **원호**.
 *
 * 🔴 가로로 일자가 아니라 **가운데가 솟은 아치**다(사용자 요청). 글자가 큰
 * 원의 바깥을 타고 앉아 양옆이 아래로 흘러내린다 — 포스터에서 흔한 짜임이고,
 * 마침 이 사진은 가운데에 사람 머리가 있어서 글자가 그 위를 타고 넘는다.
 *
 * viewBox 는 폭이 늘 1000 이다. 반지름이 클수록 완만하다:
 *
 *   반폭 = 500 − MARK_INSET
 *   솟는 높이 = R − √(R² − 반폭²)        원호 길이 = 2R·asin(반폭/R)
 *
 * 🔴 **양끝을 안쪽으로 들인다**(`MARK_INSET`). 아치가 깊어지면 끝 글자가
 * 50° 가까이 기울어 상자 밖으로 뻗는데, 원호를 화면 끝까지 그으면 그 글자가
 * **화면 밖에서 잘린다**(실제로 T 와 P 가 잘렸다). 90 만 들여도 들어온다.
 *
 * 🔴 기준선(`MARK_BASELINE`)은 **솟는 높이 + 캡 높이**보다 아래여야 한다.
 * 안 그러면 한가운데 글자의 머리가 viewBox 위로 잘려 나간다.
 *
 * 🔴 `MARK_FIT` 은 **원호 길이보다 조금 짧게**. 길면 `textLength` 가 자간을
 * 음수로 밀어 넣어 글자가 겹치고(겹쳤었다), 너무 짧으면 자간이 벌어져 글자가
 * 흩어진다(흩어졌었다). 글자 크기(globals.css)와 짝이라 같이 고칠 것 —
 * Shrikhand 로 "TRAIN & GEAR UP" 은 1px 당 대략 8.9 만큼 늘어난다.
 */
const MARK_INSET = 90
const MARK_R = 537
const MARK_BASELINE = 276
const MARK_LINE = 344
const MARK_FIT = 930

/**
 * 글자 하나가 **화면 밖 어디에서** 날아오는지.
 *
 * 🔴 진짜 난수를 쓰지 않는다. 서버에서 그린 것과 브라우저에서 그린 것이 달라지면
 * 자리가 어긋나고, 다시 그릴 때마다 방향이 바뀌어 나갈 때 들어온 자리로 못
 * 돌아간다(사용자 요청: "나갈 때도 똑같은 자리로"). 차례(index)만 넣으면 늘 같은
 * 값이 나오는 셈을 쓴다.
 *
 * 거리는 viewBox 폭(1000)보다 넉넉히 크게 잡는다 — 상자 안 어디에 있든 그만큼
 * 밀면 화면 밖이다.
 */
/**
 * 글자가 **아치를 타고 바깥으로** 빠져나가는 방향(내리기 시작했을 때).
 *
 * 🔴 그냥 좌우로 밀면 아치를 벗어나 직선으로 미끄러진다. 원호 위의 그 자리에서
 * **접선 방향**으로 밀어야 글자가 제 곡선을 따라 흘러 나간다 — 가운데 글자는
 * 거의 옆으로, 양끝 글자는 아치가 꺾이는 만큼 아래로 흐른다.
 *
 * 왼쪽 절반("TRAIN &")은 왼쪽 아래로, 오른쪽 절반("GEAR UP")은 오른쪽 아래로
 * 간다(사용자 요청). 가르는 자리가 마침 `&` 뒤의 빈칸이라 따로 셀 것이 없다.
 */
function arcExitOf(k: number, n: number): { ax: number; ay: number } {
  const phiMax = Math.asin((500 - MARK_INSET) / MARK_R)
  const t = n > 1 ? k / (n - 1) : 0.5
  const phi = -phiMax + t * 2 * phiMax
  // 안쪽으로 향하는 쪽이 아니라 **제 편 바깥쪽**으로.
  const way = t < 0.5 ? -1 : 1
  const dist = 1600
  return {
    ax: Math.round(way * Math.cos(phi) * dist),
    ay: Math.round(way * Math.sin(phi) * dist),
  }
}

function offsetOf(k: number): { dx: number; dy: number } {
  const r = (n: number) => {
    const x = Math.sin(n * 12.9898) * 43758.5453
    return x - Math.floor(x)
  }
  const angle = r(k * 2 + 1) * Math.PI * 2
  // 🔴 화면 밖으로 나갈 만큼만. 더 멀리 두면 같은 시간에 그만큼 빨리 날아와
  //    부드럽게 흐르는 게 아니라 휙 꽂히는 것으로 보인다(사용자 지적).
  const dist = 720 + r(k * 2 + 2) * 380
  return { dx: Math.round(Math.cos(angle) * dist), dy: Math.round(Math.sin(angle) * dist) }
}

/**
 * `className` 은 이 층을 **바깥에서 움직이려는** 곳을 위한 것이다 — 영상 분석
 * 화면이 왼쪽 판을 밀어 넣으면서 사진을 그만큼 오른쪽으로 옮긴다. 홈은 안 준다.
 */
export default function FigureBackground({
  className = '',
  /**
   * 화면마다 다른 사진을 깔 수 있다(레슨 · 상점은 공을 든 선수). 안 주면
   * 홈 · 영상 분석이 쓰는 기본 사진이다.
   *
   * 🔴 **영상 분석은 기본값을 그대로 써야 한다.** 그 화면의 큰 글자가 이
   * 사진의 밝기를 마스크로 쓰고(`.ss-shot-cut` 이 같은 파일을 다시 그린다),
   * 여기만 바꾸면 마스크가 따로 논다.
   */
  src = '/home_figure.jpg',
  /** 사진마다 인물이 있는 자리가 다르다 — 좁은 화면에서 인물이 안 잘리게. */
  position,
  /**
   * 사진에서 **사람만 오려 낸** 그림. 주면 큰 글자 **위**에 다시 덮는다 —
   * 그래야 글자가 사람 뒤로 지나간다(레퍼런스: Elite Court Supplies).
   *
   * 🔴 사진과 **같은 상자 · 같은 자르기**를 쓴다. 한 픽셀이라도 다르면 오려
   * 낸 사람이 원본에서 살짝 어긋나 유령처럼 겹쳐 보인다. 그래서 두 그림이
   * 같은 부모 안에서 같은 값을 받는다.
   *
   * `scripts/cutout.swift` 로 만든다(macOS Vision).
   */
  cutout,
  /** 배경에 크게 깔리는 글자. 줄 단위로 준다. */
  mark,
  /**
   * 화면 **끝까지** 채운다.
   *
   * 기본은 위 88% 만 쓰고 아래를 검게 잦아들게 하는 것이다(홈 · 영상 분석).
   * 그 막이 화면 아래에 **검은 띠**로 보이는 사진이 있어서(사용자 지적),
   * 그럴 때는 이걸 켠다 — 상자를 100% 로 키우고 막을 빼면 사진이 끝까지 간다.
   */
  bleed = false,
}: {
  className?: string
  src?: string
  position?: string
  cutout?: string
  mark?: string[]
  bleed?: boolean
}) {
  /**
   * 원호에 줄 id. 🔴 화면이 바뀌는 동안 **두 장이 겹쳐 있을 수 있어서**
   * 고정된 id 를 쓰면 뒤엣것이 앞엣것의 길을 따라 앉는다. 사진 주소에서
   * 만들면 장마다 다르다.
   */
  const arcId = `ss-arc-${src.replace(/[^a-z0-9]/gi, '')}`

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
          height: bleed ? '100%' : `var(--ss-figure-h, ${FIGURE_HEIGHT_PERCENT}%)`,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- 장식용 고정 배경, next/image 의 LCP 추정 대상이 되지 않도록 평범한 img 로 둔다 */}
        <img
          src={src}
          alt=""
          fetchPriority="high"
          decoding="async"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: position ?? `var(--ss-figure-pos, ${FIGURE_OBJECT_POSITION})`,
          }}
        />
        {/* 사진 자체도 아래로 갈수록 어둡지만 딱 떨어지지 않아, 이 막이 나머지를 지운다.
            화면 끝까지 채우는 사진에는 지울 아랫변이 없으므로 두지 않는다. */}
        {!bleed && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: `linear-gradient(to bottom, transparent 62%, color-mix(in srgb, var(--ss-bg) 30%, transparent) 88%, var(--ss-bg) 100%)`,
            }}
          />
        )}

        {/* 🔴 글자는 **사진 위 · 누끼 아래**다. 이 차례가 이 연출의 전부다.
            🔴 **SVG 로 담는다.** 글자 크기를 vw 로 잡아 봤더니 문구 길이에 따라
            양끝이 잘려 안 읽혔다(사용자 지적) — 몇 vw 가 맞는지는 글꼴과 글자
            수에 달려 있어서 손으로는 못 맞춘다. viewBox 는 폭이 늘 1000 이고
            `textLength` 가 그 폭에 글자를 맞추므로, **문구를 바꿔도 늘 화면 폭에
            딱 들어찬다.** `lengthAdjust="spacing"` 이라 글자 모양은 안 늘어나고
            자간만 조절된다 — 초압축 글꼴을 옆으로 늘리면 금세 촌스러워진다. */}
        {mark && mark.length > 0 && (
          <svg
            className="ss-figure-mark"
            viewBox={`0 0 1000 ${mark.length * MARK_LINE}`}
            preserveAspectRatio="xMidYMin meet"
            aria-hidden="true"
            focusable="false"
          >
            <defs>
              {mark.map((line, i) => (
                /* 왼쪽 아래에서 시작해 오른쪽 아래로 가는 원호. `sweep-flag=1`
                   이라 가운데가 위로 솟는다(0 이면 아래로 꺼진다). */
                <path
                  key={line}
                  id={`${arcId}-${i}`}
                  fill="none"
                  d={`M ${MARK_INSET} ${i * MARK_LINE + MARK_BASELINE} A ${MARK_R} ${MARK_R} 0 0 1 ${
                    1000 - MARK_INSET
                  } ${i * MARK_LINE + MARK_BASELINE}`}
                />
              ))}
            </defs>
            {/* 🔴 글자 **하나마다 한 장**을 그린다. 한 장에는 문구 전체가 들어
                있고 그중 한 글자만 보이게 둔다 — 그래서 열넷 다 **똑같은 자리에
                똑같이 앉는다.** 글자마다 위치를 따로 재서 놓는 방법도 있지만,
                그러면 `textLength` 가 자간을 어떻게 벌렸는지까지 다시 계산해야
                하고 글꼴이 바뀔 때마다 어긋난다. 이렇게 하면 **브라우저가 이미
                계산해 둔 자리를 그대로 쓴다.**
                안 보이는 글자도 자리는 그대로 차지한다(투명도는 배치를 안 바꾼다). */}
            {mark.map((line, i) =>
              Array.from(line).map((ch, k) =>
                ch === ' ' ? null : (
                  <text
                    key={`${i}-${k}`}
                    className="ss-figure-mark-ch"
                    xmlSpace="preserve"
                    style={
                      {
                        '--ss-ch-dx': offsetOf(i * 100 + k).dx,
                        '--ss-ch-dy': offsetOf(i * 100 + k).dy,
                        '--ss-ch-ax': arcExitOf(k, line.length).ax,
                        '--ss-ch-ay': arcExitOf(k, line.length).ay,
                        '--ss-ch-i': k,
                      } as React.CSSProperties
                    }
                  >
                    <textPath
                      href={`#${arcId}-${i}`}
                      startOffset="50%"
                      textAnchor="middle"
                      textLength={MARK_FIT}
                      lengthAdjust="spacing"
                    >
                      {Array.from(line).map((c, j) =>
                        c === ' ' ? (
                          ' '
                        ) : (
                          <tspan key={j} fillOpacity={j === k ? 1 : 0}>
                            {c}
                          </tspan>
                        ),
                      )}
                    </textPath>
                  </text>
                ),
              ),
            )}
          </svg>
        )}

        {/* 오려 낸 사람을 글자 위에 다시 덮는다. 같은 상자 · 같은 자르기라
            자리가 저절로 맞는다 — 덮었다는 티도 안 난다. */}
        {cutout && (
          // eslint-disable-next-line @next/next/no-img-element -- 위 배경 사진과 같은 이유
          <img
            src={cutout}
            alt=""
            decoding="async"
            className={`ss-figure-cut${bleed ? ' ss-figure-cut-bleed' : ''}`}
            style={{
              objectPosition: position ?? `var(--ss-figure-pos, ${FIGURE_OBJECT_POSITION})`,
            }}
          />
        )}
      </div>
    </div>
  )
}
