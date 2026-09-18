/**
 * 「팀을 만들어주세요」 **한 번 표**(사용자 요청, 2026-09-19).
 *
 * 팀 없이도 이 서비스를 쓰는 사람이 있다 — 팀원으로만 들어가거나, 영상 분석만
 * 하거나, 영상만 올리는 사람. 그래서 내 프로필에 올 때마다 「팀을 만들어주세요」로
 * 어둡게 막으면 말이 안 된다. 대신:
 *
 * 1. 홈 스쿼드 판에서 빈 자리를 눌러 「내 프로필에서 팀을 먼저 만들어주세요」가
 *    **떴을 때** 표를 하나 남긴다(`markTeamNudge`)
 * 2. 내 프로필이 그 표를 보면 **한 번** 안내하고 표를 지운다(`clearTeamNudge`)
 * 3. 표가 없으면 몇 번을 들어와도 안 띄운다 — 다시 1 을 거쳐야 또 뜬다
 *
 * 이 탭 동안만(sessionStorage). 🔴 저장소가 막히면 조용히 「표 없음」 — 안내가
 * 안 뜰 뿐 화면은 멀쩡하다.
 */
const KEY = 'ss-team-nudge-pending'

export function markTeamNudge(): void {
  try {
    sessionStorage.setItem(KEY, '1')
  } catch {
    /* 못 적으면 프로필 안내가 안 뜰 뿐이다 */
  }
}

export function hasTeamNudge(): boolean {
  try {
    return sessionStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

export function clearTeamNudge(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    /* 없어도 그만 */
  }
}
