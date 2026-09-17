/**
 * **홈에 보일 팀** — 소속이 여럿일 때 어느 팀의 스쿼드를 그릴 것인가.
 *
 * 🔴 **계약에 「주 소속」이 없다.** `GET /me` 의 `teams` 는 순서만 줄 뿐
 * 어느 것이 대표인지 말하지 않고, 그것을 저장할 경로도 없다. 그래서 이
 * 선택은 **이 브라우저의 것**이다 — 기기를 바꾸면 다시 고른다.
 *
 * 🔴 **쿠키인 이유**: 홈(`app/page.tsx`)이 **서버 컴포넌트**라 그릴 때
 * 값을 알아야 한다. `localStorage` 는 브라우저에만 있어서 서버가 못 읽고,
 * 읽은 뒤 화면만 바꾸면 서버가 그린 첫 판과 갈려 하이드레이션이 깨진다.
 *
 * ⚠️ **비밀이 아니다** — 팀 id 하나이고, 서버는 이 값을 **믿지 않는다**:
 * 내 소속 목록에 없으면 무시하고 첫 팀으로 떨어진다(아래 `pickTeamId`).
 * 그래서 남의 팀 id 를 넣어도 아무 일이 없다.
 */
export const HOME_TEAM_COOKIE = 'ss-home-team'

/** 1년. 고른 뒤 다시 묻지 않을 만큼 길면 된다. */
const MAX_AGE = 60 * 60 * 24 * 365

/**
 * 어느 팀을 그릴 것인가 — **고른 것이 내 소속일 때만** 그것, 아니면 첫 팀.
 *
 * 🔴 **쿠키 값을 그대로 쓰지 않는다.** 사람이 고칠 수 있는 값이라, 소속이
 * 아닌 id 를 넣으면 남의 팀을 읽으려 든다(서버가 403 을 주겠지만 화면은
 * 빈 판이 된다). 여기서 걸러 내는 편이 확실하다.
 */
export function pickTeamId(
  teams: { team_id: string }[],
  chosen: string | undefined,
): string | undefined {
  if (chosen && teams.some((t) => t.team_id === chosen)) return chosen
  return teams[0]?.team_id
}

/** 브라우저에서 고른 팀을 적어 둔다. 서버 컴포넌트가 다음 렌더에 읽는다. */
export function rememberHomeTeam(teamId: string): void {
  document.cookie = `${HOME_TEAM_COOKIE}=${encodeURIComponent(teamId)}; path=/; max-age=${MAX_AGE}; samesite=lax`
}
