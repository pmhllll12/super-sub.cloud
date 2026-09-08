/**
 * 화면이 다루는 종목. **영상 분석 화면과 내 프로필이 같은 것을 쓴다** — 두 벌로
 * 두면 한쪽에만 종목이 늘어난다.
 *
 * 세 종목이 다 여기 남아 있다. 루브릭도 지표도 셋 다 있고(`rubricFocus.ts`),
 * 지금은 **화면이 축구만 내보인다**(아래 `DEFAULT_SPORT`).
 */
export const SPORTS = [
  { key: 'soccer', label: '축구', icon: 'sports_soccer' },
  { key: 'baseball', label: '야구', icon: 'sports_baseball' },
  { key: 'basketball', label: '농구', icon: 'sports_basketball' },
] as const

export type SportKey = (typeof SPORTS)[number]['key']

/**
 * 분석 화면이 쓰는 종목. **지금은 축구 하나다**(팀 결정, 2026-09-08:
 * "일단 축구 영상만 넣고 나중에 확장한다").
 *
 * 🔴 **앞서 여기 「기본값을 두지 않는다」고 적어 둔 것을 뒤집는다.** 그 이유는
 * *야구 영상이 축구 루브릭으로 조용히 채점되는 것*이었고, 그 위험은 **사라지지
 * 않았다** — 넣는 영상을 축구로 한정하기로 한 운용 약속으로 막고 있을 뿐이다.
 *
 * 🔴 **종목을 다시 늘릴 때는 고르는 자리를 같이 되살려야 한다.** 이 상수만 바꾸고
 * 단추를 안 되살리면 그때 그 조용한 오채점이 그대로 돌아온다. 되살릴 자리는
 * `AnalysisStage` 의 머리줄(`.ss-shot-bar-right`)이고, 시험이 지금 "고르는 자리가
 * 없다"를 붙들고 있으므로 **그 시험이 먼저 빨개진다.**
 */
export const DEFAULT_SPORT: SportKey = 'soccer'

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
