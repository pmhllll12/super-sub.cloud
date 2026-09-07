import PlayerCardBrush from './PlayerCardBrush'

/**
 * 카드 뒤에 깔리는 **자국** 열 가지.
 *
 * 기존 `PlayerCardBrush` 는 붓으로 그은 대각선 하나뿐이고, 씨앗으로 모양이
 * 정해져 사람이 고를 수가 없었다. 여기 것들은 **고르는 것**이라 서로 확실히
 * 달라야 한다 — 색만 다른 열 장이면 고를 이유가 없다.
 *
 * 🔴 전부 하나의 `viewBox="0 0 100 140"` 안에서 그린다(카드 비율 3:4.1 에
 * 가깝다). 크기 · 위치는 바깥에서 `transform` 으로 주므로, 여기서는 **좌표만**
 * 신경 쓰면 된다.
 *
 * 🔴 색은 `currentColor` 하나로 받는다. 자국마다 색을 박아 두면 사용자가 고른
 * 색이 일부에만 먹는다.
 */

/**
 * 고를 수 있는 자국들.
 *
 * 🔴 첫 자리가 **기본**이다 — 사람 뒤에 원래 깔려 있던 붓칠
 * (`PlayerCardBrush`, 슬러그로 모양이 정해지는 그것)이다.
 * ⚠️ 한때 이 자리를 '없음' 으로 두었다가 되돌렸다: 편집을 여는 순간 붓칠이
 * 사라져, 고치기도 전에 카드가 달라져 버렸다.
 */
export const MARKS = [
  '기본',
  '없음',
  '사선',
  '빗살',
  '호',
  '파편',
  '물결',
  '점',
  '겹원',
  '지그재그',
  '격자',
  '번짐',
] as const

/**
 * 인덱스가 곧 위 배열의 자리다 — `0` 기본(원래 붓칠) · `1` 없음 · 그 뒤가 열 가지.
 *
 * 🔴 기본도 색 · 크기 · 자리를 따른다. 원래 붓칠만 못 만지면 "기본을 고르면
 * 설정이 반쯤 죽는" 자리가 된다.
 */
export default function CardMark({ index, seed }: { index: number; seed: string }) {
  if (index === 1) return null

  if (index === 0) {
    return (
      <span className="ss-card-mark ss-card-mark-default">
        <PlayerCardBrush seed={seed} />
      </span>
    )
  }

  return (
    <svg
      className="ss-card-mark"
      viewBox="0 0 100 140"
      preserveAspectRatio="none"
      aria-hidden="true"
      focusable="false"
    >
      {shape(index - 1)}
    </svg>
  )
}

function shape(index: number) {
  switch (index) {
    // 1. 사선 — 굵은 한 획이 카드를 가로지른다. 가장 단순하고 세다.
    case 1:
      return <path d="M-10 96 L110 34 L110 52 L-10 114 Z" fill="currentColor" />

    // 2. 빗살 — 가는 획 여럿이 같은 각도로 스친다.
    case 2:
      return (
        <g fill="currentColor">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <path
              key={i}
              d={`M-10 ${58 + i * 13} L110 ${24 + i * 13} L110 ${28 + i * 13} L-10 ${62 + i * 13} Z`}
              opacity={0.9 - i * 0.1}
            />
          ))}
        </g>
      )

    // 3. 호 — 카드를 감싸 도는 굵은 곡선. 인물 뒤에서 후광처럼 읽힌다.
    case 3:
      return (
        <path
          d="M-6 120 Q50 40 106 120"
          fill="none"
          stroke="currentColor"
          strokeWidth="10"
          strokeLinecap="round"
        />
      )

    // 4. 파편 — 날카로운 삼각 조각들이 흩어진다.
    case 4:
      return (
        <g fill="currentColor">
          <path d="M8 74 L44 52 L16 92 Z" />
          <path d="M54 40 L92 62 L60 68 Z" opacity="0.8" />
          <path d="M26 108 L70 88 L48 118 Z" opacity="0.65" />
          <path d="M74 96 L98 108 L76 116 Z" opacity="0.5" />
        </g>
      )

    // 5. 물결 — 느슨한 파형 셋. 유일하게 부드러운 자국이다.
    case 5:
      return (
        <g fill="none" stroke="currentColor" strokeLinecap="round">
          {[0, 1, 2].map((i) => (
            <path
              key={i}
              d={`M-6 ${72 + i * 16} q 26 -14 52 0 t 60 0`}
              strokeWidth={6 - i}
              opacity={0.9 - i * 0.25}
            />
          ))}
        </g>
      )

    // 6. 점 — 굵기가 다른 점들이 대각으로 흐른다(하프톤의 결).
    case 6:
      return (
        <g fill="currentColor">
          {Array.from({ length: 26 }, (_, i) => {
            const t = i / 25
            return (
              <circle
                key={i}
                cx={6 + t * 92}
                cy={116 - t * 62}
                r={4.2 - t * 3.2}
                opacity={0.95 - t * 0.55}
              />
            )
          })}
        </g>
      )

    // 7. 겹원 — 같은 중심의 테 셋. 과녁처럼 가운데를 잡아 준다.
    case 7:
      return (
        <g fill="none" stroke="currentColor">
          <circle cx="50" cy="84" r="15" strokeWidth="7" />
          <circle cx="50" cy="84" r="28" strokeWidth="4" opacity="0.7" />
          <circle cx="50" cy="84" r="41" strokeWidth="2" opacity="0.45" />
        </g>
      )

    // 8. 지그재그 — 각진 번개 한 줄.
    case 8:
      return (
        <path
          d="M-4 62 L26 92 L44 68 L70 104 L88 76 L106 96"
          fill="none"
          stroke="currentColor"
          strokeWidth="7"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )

    // 9. 격자 — 기울어진 그물. 코트의 펜스에서 왔다.
    case 9:
      return (
        <g stroke="currentColor" strokeWidth="2" opacity="0.55">
          {Array.from({ length: 9 }, (_, i) => (
            <line key={`a${i}`} x1={-20 + i * 18} y1="140" x2={20 + i * 18} y2="30" />
          ))}
          {Array.from({ length: 9 }, (_, i) => (
            <line key={`b${i}`} x1={-20 + i * 18} y1="30" x2={20 + i * 18} y2="140" />
          ))}
        </g>
      )

    // 10. 번짐 — 가운데가 진하고 가장자리로 흩어지는 얼룩.
    case 10:
      return (
        <>
          <defs>
            <radialGradient id="ss-mark-blot">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.85" />
              <stop offset="55%" stopColor="currentColor" stopOpacity="0.35" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </radialGradient>
          </defs>
          <ellipse cx="50" cy="86" rx="52" ry="40" fill="url(#ss-mark-blot)" />
        </>
      )

    default:
      return null
  }
}
