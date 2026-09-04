/**
 * 프로필 화면의 유리 재질.
 *
 * 🔴 **흐림은 인라인으로만 준다.** `globals.css` 에 적으면 Lightning CSS 를
 * 지나며 통째로 떨어져 나간다 — 이 저장소의 다른 유리 판들(HomeNav ·
 * AnalysisStage · MarketGates)도 같은 이유로 전부 인라인이고, 이 화면에서도
 * 실제로 그렇게 사라졌다(계산된 값이 `none` 이었다).
 *
 * 큰 판과 그 안의 절이 **둘 다** 흐린다. 뒤의 것을 흐리는 성질이라 겹치면
 * 더 뿌예지고, 그래서 절 쪽은 판보다 작은 값이면 충분하다.
 */
const glass = (px: number) => ({
  backdropFilter: `blur(${px}px) saturate(1.4)`,
  WebkitBackdropFilter: `blur(${px}px) saturate(1.4)`,
})

/** 배경 사진 위에 놓이는 큰 판. */
export const SHEET_GLASS = glass(15)

/** 그 안의 네 절(소속 · 정보 · 내 경기 · 계정). */
export const SECTION_GLASS = glass(60)
