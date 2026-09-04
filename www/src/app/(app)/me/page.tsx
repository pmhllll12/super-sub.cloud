import Link from 'next/link'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import {
  BackendError,
  getBackend,
  type Match,
  type MyVideo,
  type PlayerCard,
  type User,
} from '@/server/backend'
import { requireUser } from '@/server/currentUser'
import { SESSION_COOKIE } from '@/server/session'
import AccountActions from './AccountActions'
import CardEditor from './CardEditor'
import StyledCard from './StyledCard'
import { CardStyleProvider } from './cardStyle'
import MyVideos from './MyVideos'
import ProfileStage from './ProfileStage'
import NicknameForm from './NicknameForm'
import { when, ymd } from './format'
import { SECTION_GLASS, SHEET_GLASS } from './glass'

/** 정보 절의 한 줄 — 흐린 이름표와 진한 값. */
function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="ss-profile-info-row">
      <dt className="ss-profile-info-label">{label}</dt>
      <dd className="ss-profile-info-value">{children}</dd>
    </div>
  )
}

/**
 * 마크업만 따로 뺀 것 — `MePage` 가 서버 컴포넌트로 쿠키 · 백엔드를 부르게
 * 되면서 테스트가 이 함수를 직접 렌더한다(`HomeBody` 와 같은 이유 · 같은 방식).
 *
 * 선수 카드가 여기 같이 있다. 예전에는 `/me/card` 라는 별도 화면이었는데
 * 홈 목적지를 6개로 정리하면서 '내 선수 카드'를 '내 프로필'에 합쳤다 —
 * 프로필과 카드는 결국 같은 사람에 대한 한 화면이라 나눌 이유가 약했다.
 * `/me/card` 는 그 자리로 보내는 스텁으로 남겨 뒀다(옛 링크 호환).
 *
 * 🔴 **화면을 거의 다 쓰고, 가운데서 좌우로 갈린다**(사용자 요청).
 *
 *   왼쪽  — 신원 · 소속 · 정보
 *   오른쪽 — 내 영상 (분석 영상 · 업로드 영상을 알약으로 갈라 한 편씩)
 *
 * ⚠️ 영상에 **그림이 없다.** 계약이 주는 것은 저장 키뿐이고 조회용 주소가
 * 아직 없어서(3-6절 "아직 없는 것"), 목록은 메타와 상태로만 그린다.
 *
 * 🔴 원본(장인 프로필)의 **원형 얼굴 사진 자리에 선수 카드를 넣었다**(사용자
 * 요청). 우리에겐 프로필 사진이 없고, 카드가 곧 그 사람의 얼굴이다. 틀은
 * 헤더가 쓰는 `.ss-pcard-mini` 를 그대로 읽는다 — 여기서 따로 만들지 않는다.
 *
 * ⚠️ 좋아요 · 북마크는 **만들지 않았다.** 계약에 그런 값이 없어서 숫자를
 * 지어내야 하는데, 카드가 수치를 안 그리기로 한 것과 같은 이유로 프로필에도
 * 두지 않는다(`PlayerCardView` 주석 참고).
 *
 * ⚠️ 원본의 Biography 에 해당하는 **소개글이 우리에겐 없다.** 그 자리는
 * 소속 팀이 쓴다 — 빈 칸을 두거나 문장을 지어내지 않는다.
 */
export function MeBody({
  user,
  card,
  videos,
  matches,
  editing = false,
}: {
  user: User
  card: PlayerCard | null
  videos: MyVideo[]
  matches: Match[]
  /**
   * 카드 편집 모드인가. 🔴 **주소(`/me?edit=1`)가 들고 있다** — 컴포넌트
   * 상태로 두면 뒤로 가기로 닫을 수 없고, 새로고침하면 풀린다.
   */
  editing?: boolean
}) {
  const titles = card?.titles ?? []

  return (
    <ProfileStage editing={editing}>
      {/* 🔴 카드와 편집기가 화면에서 떨어져 있어(카드는 선 위, 편집기는 선
          아래) 한쪽이 상태를 들 수 없다 — 둘을 함께 감싼다. */}
      <CardStyleProvider>
      {/* 판 **바깥 위**에 얹는 한 마디. 워드마크가 가운데에 서므로 이쪽은
          왼쪽 끝에 둔다 — 둘이 같은 줄에서 좌우로 갈린다. */}
      <p className="ss-profile-title">MY PROFILE</p>

      {/* 흐림은 인라인으로만 걸린다 — 이유는 `glass.ts` 주석 참고. */}
      <div className="ss-profile-sheet" style={SHEET_GLASS}>
        {/* ── 왼쪽. 신원 · 소속 · 정보 ─────────────────────────────── */}
        <div className="ss-profile-left">
          {/* 🔴 카드가 없는 사람에게 **어떻게 만드는지** 알린다.
              ⚠️ 여기 오래 "경기 영상이 분석되면 만들어집니다" 라고 적혀
              있었는데 **사실이 아니었다.** 카드는 분석과 무관하게, 사용자가
              부탁할 때 생긴다(계약 3장 「카드는 언제 생기나 — 요청할 때」).
              분석이 붙이는 것은 카드가 아니라 **호칭**이다. */}
          {!card && (
            <p className="ss-profile-nocard">
              아직 선수 카드가 없습니다 — <strong>프로필 카드 수정</strong>에서 바로 만들 수
              있습니다.
            </p>
          )}

          {/* 🔴 접히는 칸은 **래퍼가 하나 더** 필요하다. `grid-template-rows`
              를 `1fr → 0fr` 로 전환하는 방식이라(아래 CSS), 그 격자의 자식이
              정확히 하나여야 내용 높이를 그대로 따라간다. */}
          <div className="ss-profile-fold" data-open={editing ? 'false' : 'true'}>
            <div className="ss-profile-body">
            <section className="ss-profile-bio" style={SECTION_GLASS}>
              <h2 className="ss-profile-h">소속</h2>
              {user.teams.length === 0 ? (
                <p className="ss-profile-muted">아직 소속된 팀이 없습니다.</p>
              ) : (
                <ul className="ss-profile-teams">
                  {user.teams.map((t) => (
                    <li key={t.team_id}>
                      <p className="ss-profile-team-name">{t.name}</p>
                      <p className="ss-profile-muted">
                        {t.region} · {t.sport_code}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="ss-profile-info" style={SECTION_GLASS}>
              <h2 className="ss-profile-h">정보</h2>
              <dl>
                <InfoRow label="호칭">
                  {titles.length === 0 ? (
                    <span className="ss-profile-muted">아직 받은 호칭이 없습니다.</span>
                  ) : (
                    <span className="ss-profile-pills">
                      {titles.map((t) => (
                        <span key={t.code} className="ss-profile-pill">
                          <b>{t.category}</b>
                          {t.label}
                        </span>
                      ))}
                    </span>
                  )}
                </InfoRow>
                <InfoRow label="이메일">{user.email}</InfoRow>
                <InfoRow label="함께한 날">{ymd(user.created_at)}부터</InfoRow>
              </dl>
            </section>

            <section className="ss-profile-matches" style={SECTION_GLASS}>
              <h2 className="ss-profile-h">내 경기</h2>
              {matches.length === 0 ? (
                /* ⚠️ "경기가 없다" 가 아니라 "**다가오는** 것이 없다" 다 —
                   계약이 지난 경기를 이 목록에서 빼기 때문이다(3-4절).
                   지난 경기가 있어도 여기는 비어 있을 수 있다. */
                <p className="ss-profile-muted">다가오는 경기가 없습니다.</p>
              ) : (
                <ul className="ss-profile-match-list">
                  {matches.map((m) => (
                    <li key={m.id}>
                      <p className="ss-profile-match-when">{when(m.played_at)}</p>
                      <p className="ss-profile-match-place">{m.place}</p>
                      {m.needs.length > 0 && (
                        <p className="ss-profile-muted">
                          {m.needs.map((n) => `${n.position_label} ${n.head_count}`).join(' · ')}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <AccountActions />
            </div>
          </div>

          {/* 🔴 **신원 묶음이 칸의 맨 아래에 앉는다**(사용자 요청). 위쪽은
              소속 · 정보가 읽히는 자리고, 카드와 이름은 바닥에서 화면을
              받친다. `margin-top: auto` 가 남는 높이를 다 밀어 준다. */}
          <div className="ss-profile-id">
            <div className="ss-profile-id-main">
              <div className="ss-profile-face-col">
                {card ? (
                  /* 편집 중에만 꾸민 값을 입는다 — 평소에는 서버가 준 그대로다
                     (설정은 아직 저장되지 않는다).
                     🔴 편집 중에는 `StyledCard` 가 **바깥 상자까지** 그린다.
                     `.ss-pcard-mini > .ss-pcard` 가 직계 자식을 찾으므로 사이에
                     상자를 끼울 수 없다. */
                  editing ? (
                    <StyledCard card={card} />
                  ) : (
                    <span className="ss-pcard-mini ss-profile-face">
                      <PlayerCardView card={card} />
                    </span>
                  )
                ) : (
                  /* 카드가 아직 없는 사람 — 자리를 비우면 줄이 무너지므로 같은
                     크기의 판에 이름 첫 글자를 넣는다. */
                  <span className="ss-profile-face ss-profile-face-empty" aria-hidden="true">
                    {user.nickname.slice(0, 1)}
                  </span>
                )}

                {/* 🔴 **주소로 연다**(`/me?edit=1`). 상태로 두면 뒤로 가기가
                    안 먹고 새로고침하면 풀린다. 닫기는 같은 자리에서 `/me`
                    로 돌아가는 링크가 된다. */}
                <Link
                  href={editing ? '/me' : '/me?edit=1'}
                  className="ss-profile-tab ss-profile-edit-link"
                >
                  {editing ? '편집 닫기' : '프로필 카드 수정'}
                </Link>
              </div>

              {/* 머리글은 카드 위가 아니라 **이름 쪽**에 있다(사용자 요청) —
                  카드 위를 비워야 카드를 그만큼 키울 수 있다. */}
              <div className="ss-profile-id-text">
                {/* ⚠️ **아직 붙박이 문구다.** 계약에 이 사람이 코치인지 알려
                    주는 값이 없다 — `user` 에는 소속 팀의 역할(`teams[].role`)
                    뿐이고, 그건 팀 안에서의 역할이지 코치 인증이 아니다.
                    (DB 의 `coach` 테이블에 `user_id` 가 없는 것도 같은 자리다 —
                    작업 현황 0.9절 참고.) 값이 생기면 여기서 '코치'로 갈린다. */}
                <p className="ss-profile-kicker">일반 유저</p>
                <NicknameForm nickname={user.nickname} />
              </div>
            </div>
          </div>

          {/* 🔴 편집기는 신원 줄 아래에 온다(사용자 요청). **늘 그려 두고
              접는다** — 열 때만 그리면 닫을 때 뚝 사라진다(빠져나가는 연출을
              붙일 요소가 이미 없기 때문이다).
              🔴 접혀 있는 동안은 `inert` 로 잠근다. 안 그러면 보이지도 않는
              단추에 탭이 들어간다. */}
          <div
            className="ss-profile-fold ss-profile-editor-fold"
            data-open={editing ? 'true' : 'false'}
            inert={!editing}
          >
            <CardEditor card={card} />
          </div>
        </div>

        {/* ── 오른쪽. 내 영상 ─────────────────────────────────────── */}
        <div className="ss-profile-right">
          <MyVideos videos={videos} />
        </div>
      </div>
      </CardStyleProvider>
    </ProfileStage>
  )
}

export default async function MePage({
  searchParams,
}: {
  searchParams: Promise<{ edit?: string }>
}) {
  const { edit } = await searchParams
  const user = await requireUser()

  // 카드가 아직 없는 것은 정상이다 — CARD_NOT_FOUND 는 화면 안에서
  // "아직 없습니다"로 안내한다. 401 은 requireUser() 가 이미 걸러 냈지만
  // 그 사이 토큰이 죽을 수도 있어 여기서도 로그인으로 보낸다.
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  let card: PlayerCard | null = null
  let videos: MyVideo[] = []
  let matches: Match[] = []
  if (token) {
    try {
      card = await getBackend().getMyCard(token)
    } catch (e) {
      if (e instanceof BackendError && e.status === 401) redirect('/login')
      if (!(e instanceof BackendError && e.code === 'CARD_NOT_FOUND')) throw e
    }

    // 🔴 영상 목록이 실패해도 **화면 전체를 죽이지 않는다.** 카드 · 소속 ·
    // 정보는 이미 받아 놨고, 목록 하나 때문에 프로필을 못 보는 것이 더 나쁘다.
    // 401 만은 위와 같이 로그인으로 보낸다.
    try {
      videos = await getBackend().listMyVideos(token)
    } catch (e) {
      if (e instanceof BackendError && e.status === 401) redirect('/login')
    }

    /* 🔴 경기는 **팀별로** 부른다 — 계약에 "내 경기" 하나짜리 경로가 없고
       `GET /teams/{id}/matches` 뿐이다. 소속이 여럿이면 그만큼 부른 뒤
       합쳐서 **이른 것부터** 다시 세운다(각 응답은 그 팀 안에서만 정렬돼
       있어서, 그냥 이어 붙이면 팀 순서대로 뭉친다).
       한 팀이 실패해도 나머지는 보여 준다 — 목록 하나 때문에 화면을 죽이지
       않는다는 위 규칙과 같다. */
    const perTeam = await Promise.all(
      user.teams.map(async (t) => {
        try {
          return await getBackend().listTeamMatches(token, t.team_id)
        } catch {
          return []
        }
      }),
    )
    matches = perTeam.flat().sort((a, b) => a.played_at.localeCompare(b.played_at))
  }

  return (
    <MeBody
      user={user}
      card={card}
      videos={videos}
      matches={matches}
      editing={edit === '1'}
    />
  )
}
