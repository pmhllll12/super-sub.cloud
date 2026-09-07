import type { CardStyle } from './cardStyle'

/**
 * 꾸민 카드를 담아 두는 곳.
 *
 * ⚠️ **서버가 아니라 이 브라우저다.** 계약에 카드를 꾸미는 필드가 없어서
 * (미결 paik 3번 「카드를 **꾸밀** 수가 없습니다」) 보낼 데가 없다.
 *
 * 🔴 **앞서 `cardStyle.tsx` 에 "브라우저 저장도 일부러 안 넣었다"고 적었던 것을
 * 정정한다**(2026-09-04, 사용자 요청). 그 판단의 근거는 "서버가 붙는 순간
 * 상태가 두 곳에 생겨 어느 쪽이 진짜인지 헷갈린다" 였는데, 저장이 아예 없으면
 * **편집기를 닫는 순간 꾸민 것이 전부 사라져** 기능이 성립하지 않는다. 서버가
 * 생기면 **이 파일을 지우고** 그쪽을 정본으로 삼는다 — 그때 남는 것은 이
 * 한 파일뿐이라 옮기기 쉽다.
 *
 * ⚠️ 공개 카드(`/c/{slug}`)에는 **반영되지 않는다.** 그 화면은 남의 브라우저에서
 * 열리고 여기 값은 이 브라우저에만 있다.
 */
export const CARD_STYLE_KEY = 'ss.cardStyle.v1'

/**
 * 🔴 기본값을 **인자로 받는다.** 여기서 `cardStyle` 의 상수를 끌어오면 그쪽도
 * 이 파일을 부르므로 순환 import 가 된다 — 지금은 돌지만 평가 순서에 기대는
 * 구조라, 애초에 만들지 않는 편이 낫다.
 */
export function loadCardStyle(base: CardStyle): CardStyle | null {
  try {
    const raw = localStorage.getItem(CARD_STYLE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
    // 🔴 기본값 위에 얹는다 — 값이 늘어나도 옛 저장본이 화면을 깨지 않는다.
    return { ...base, ...(parsed as Partial<CardStyle>) }
  } catch {
    return null
  }
}

/** 저장했으면 `true`. 🔴 사진(data URL)이 크면 한도를 넘어 실패할 수 있다. */
export function saveCardStyle(style: CardStyle): boolean {
  try {
    localStorage.setItem(CARD_STYLE_KEY, JSON.stringify(style))
    return true
  } catch {
    return false
  }
}
