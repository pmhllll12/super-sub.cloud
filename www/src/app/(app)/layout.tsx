import SiteHeader from '@/components/SiteHeader'
import { DESTINATIONS } from '@/lib/destinations'
import { getMyCardOrNull, requireUser } from '@/server/currentUser'

// 로그인 전용 화면(analysis/, me/) 셸 — 이 그룹의 페이지는 모두 requireUser()
// 로 이미 로그인이 보장돼 있다. `/`(홈)는 이 그룹 밖에 있다.
//
// 헤더(워드마크 · 목적지 글자 · 내 프로필)는 홈에만 있던 것을 **모든 화면**
// 으로 옮긴 것이다(사용자 요청). 홈과 같은 컴포넌트를 쓴다 — 두 벌이면
// 목적지가 늘 때 한쪽만 고치게 된다.
//
// 🔴 여기서는 **고정하지 않는다**(fixed 를 주지 않는다). 홈은 한 화면을 통째로
// 쓰는 배치라 고정이 맞지만, 이 그룹은 위에서 아래로 읽는 문서다 — 고정하면
// 본문에 헤더 높이만큼 위 여백을 따로 줘야 하는데 그 높이가 **카드 유무에 따라
// 달라져** 어긋난다. 흐름에 두면 본문이 알아서 그 아래에서 시작한다.
//
// 하단 내비바(FloatingNavBar)는 2026-08-30 에 없앴다 — 목적지가 이제 헤더에
// 다 있으므로 되살릴 이유도 없어졌다.
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser()
  const card = await getMyCardOrNull()

  return (
    <>
      <SiteHeader user={user} card={card} destinations={DESTINATIONS} />
      <div className="mx-auto max-w-[1120px] px-6 pb-32">{children}</div>
    </>
  )
}
