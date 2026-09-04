import { BackendError, getBackend, type PlayerCard, type Squad, type User } from '@/server/backend'
import { getMyCardOrNull, requireUser } from '@/server/currentUser'
import { cookies } from 'next/headers'
import { SESSION_COOKIE } from '@/server/session'
import HomeStage from '@/components/HomeStage'
import { DEFAULT_FEATURED, DESTINATIONS, FEATURED } from '@/lib/destinations'

/**
 * 마크업만 따로 뺀 것 — `Home` 이 서버 컴포넌트로 쿠키 · 백엔드를 부르게
 * 되면서 테스트가 이 함수를 직접 렌더한다(쿠키/백엔드 호출 분기를 타지
 * 않는다).
 *
 * 홈은 격자가 아니라 화면 한 장을 통째로 쓰므로 `(app)` 레이아웃처럼
 * `max-w-[1120px]` 로 가운데 폭을 좁히지 않는다 — 헤더 · 하단 줄을
 * `HomeStage` 가 `position: fixed` 로 화면 전체 기준으로 배치한다.
 */
export function HomeBody({
  user,
  card = null,
  squad = null,
}: {
  user: Pick<User, 'nickname'> | null
  card?: PlayerCard | null
  /** 팀의 스쿼드. 팀이 없거나 아직 안 만들었으면 null 이다. */
  squad?: Squad | null
}) {
  return (
    <HomeStage
      user={user}
      card={card}
      squad={squad}
      destinations={DESTINATIONS}
      featured={FEATURED}
      defaultActive={DEFAULT_FEATURED}
    />
  )
}

// `/` 가 곧 홈이다 — 앱처럼 홈이 하나뿐이다(공개 랜딩과 로그인 후 런처로
// 나뉘어 있지 않다). 인트로(`IntroGate`, 루트 레이아웃)를 지나면 이 화면이 나온다.
//
// 2026-08-28 부터 **로그인해야 들어올 수 있다.** 앞단의 `proxy.ts` 가 쿠키
// 없는 요청을 이미 `/login` 으로 보내지만, 그건 쿠키가 "있는지"까지만 본다 —
// 썩은 토큰을 들고 온 경우까지 막으려면 여기서 백엔드에 확인해야 한다.
// `requireUser()` 가 그 일을 하고, 401 이면 `/login` 으로 보낸다.
//
// `HomeBody` 는 여전히 `user: null` 을 받을 수 있게 두었다 — 인사말 자리가
// 갈리는 마크업은 테스트가 직접 렌더해 검증한다.
export default async function Home() {
  const user: User = await requireUser()

  // 헤더의 프로필 자리와 스쿼드 판 가운데가 같은 카드를 쓴다 — /me 와도 같다.
  // 카드가 아직 없는 것은 정상이라 화면 안에서 닉네임 글자로 대신한다.
  const card = await getMyCardOrNull()

  /* 🔴 스쿼드는 **첫 소속 팀** 것을 읽는다. 계약에 "내 스쿼드" 하나짜리
     경로가 없고 `GET /teams/{id}/squad` 뿐이라, 팀을 먼저 골라야 한다 —
     팀이 여럿인 사람에게 어느 팀을 보일지는 아직 화면에 고를 자리가 없다.

     🔴 404(`SQUAD_NOT_FOUND`)는 **정상이다.** 아직 안 만든 팀이라는 뜻이라
     빈 판을 그린다 — 계약이 "만들지 않은 것"과 "비어 있는 것"을 일부러
     갈라 두었다(3-7절). 그 밖의 실패도 판을 죽이지 않는다. */
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  const teamId = user.teams[0]?.team_id
  let squad: Squad | null = null
  if (token && teamId) {
    try {
      squad = await getBackend().getSquad(token, teamId)
    } catch (e) {
      if (!(e instanceof BackendError)) throw e
    }
  }

  return <HomeBody user={user} card={card} squad={squad} />
}
