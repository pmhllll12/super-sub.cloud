/**
 * 화면이 다루는 종목. **영상 분석 화면과 내 프로필이 같은 것을 쓴다** — 두 벌로
 * 두면 한쪽에만 종목이 늘어난다.
 *
 * 🔴 기본값을 두지 않는다. 축구로 박아 두면 야구 영상이 축구 루브릭으로 조용히
 * 채점된다 — 고르지 않으면 올릴 수도 분석할 수도 없어야 한다.
 */
export const SPORTS = [
  { key: 'soccer', label: '축구', icon: 'sports_soccer' },
  { key: 'baseball', label: '야구', icon: 'sports_baseball' },
  { key: 'basketball', label: '농구', icon: 'sports_basketball' },
] as const

export type SportKey = (typeof SPORTS)[number]['key']

/**
 * 화면의 종목 키를 백엔드 `sport_code` 로 바꾼다. 화면은 `soccer`, 백엔드
 * `sport` 테이블은 `football` 이다 — 이름이 갈려 있다는 것은 미결 항목에도
 * 올라와 있다(패킷 A 13번). 백엔드가 정본(`sport` 의 기본키라 외래키가
 * 걸린다)이라 **경계에서만** 맞춘다.
 */
export const SPORT_CODE: Record<SportKey, string> = {
  soccer: 'football',
  baseball: 'baseball',
  basketball: 'basketball',
}
