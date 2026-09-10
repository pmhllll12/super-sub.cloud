import PlayerCardBrush from './PlayerCardBrush'

/**
 * 카드 뒤에 깔리는 **자국**.
 *
 * 🔴 **2026-09-10 에 그림을 통째로 갈았다**(사용자 요청). 전에는 절차적 SVG
 * 열 가지(사선 · 빗살 · 호 …)였는데, 유화 · 수채 · 튄 자국 같은 **질감**은
 * 깨끗한 SVG 로 흉내 낼 수가 없다 — 그래서 그림 열둘을 **마스크**로 쓴다.
 *
 * 🔴 **색을 박은 그림이 아니라 마스크다.** `public/marks/*.png` 는 알파만
 * 담고 있고(LA 모드), 칠하는 것은 `currentColor` 다 — 그래야 「자국 색」이
 * 그대로 먹는다. 색이 구워진 그림이면 사용자가 고른 색이 죽는다.
 *
 * 🔴 크기 · 좌우 · 위아래는 `.ss-card-mark` 이 이미 받는다(`--ss-card-mark-*`).
 * 여기서는 **무엇을 그릴지만** 정한다.
 */

/**
 * 고를 수 있는 자국들.
 *
 * 🔴 첫 자리가 **기본**이다 — 사람 뒤에 원래 깔려 있던 붓칠
 * (`PlayerCardBrush`, 슬러그로 모양이 정해지는 그것)이다.
 * ⚠️ 한때 이 자리를 '없음' 으로 두었다가 되돌렸다: 편집을 여는 순간 붓칠이
 * 사라져, 고치기도 전에 카드가 달라져 버렸다.
 *
 * ⚠️ **6·7 번과 11·12 번은 서로 닮았다**(점선 별 둘 · X 둘). 받은 그림이
 * 그렇게 나왔고 **그대로 두기로 했다**(사용자 결정) — 굵기와 결이 달라서
 * 카드 위에서는 갈린다.
 */
export const MARKS = [
  '기본',
  '없음',
  '서예 번짐',
  '유화',
  '튄 자국',
  '손그림 격자',
  '캘리 S',
  '점선 별',
  '점선 별 굵게',
  '부드러운 유화',
  '물감 구름',
  '수채 구름',
  '오려낸 X',
  '긁힌 X',
] as const

/** 그림 자국이 시작하는 자리 — 앞의 둘(기본 · 없음)은 그림이 아니다. */
const FIRST_IMAGE = 2

/**
 * 인덱스가 곧 위 배열의 자리다 — `0` 기본(원래 붓칠) · `1` 없음 · 그 뒤가 그림 열둘.
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

  const n = index - FIRST_IMAGE + 1
  // 모르는 값이 오면 아무것도 안 그린다 — 저장된 값이 목록보다 클 수 있다.
  if (n < 1 || n > MARKS.length - FIRST_IMAGE) return null
  const url = `url("/marks/${String(n).padStart(2, '0')}.png")`

  return (
    <span
      className="ss-card-mark ss-card-mark-img"
      aria-hidden="true"
      /* 🔴 마스크는 **인라인으로** 준다 — 자국마다 다른 그림이라 CSS 규칙으로
         열둘을 늘어놓느니 여기서 한 줄로 주는 편이 낫고, 이 저장소는
         `mask`·`backdrop-filter` 류가 처리기를 지나며 떨어져 나간 전례가 있다. */
      style={{
        maskImage: url,
        WebkitMaskImage: url,
      }}
    />
  )
}
