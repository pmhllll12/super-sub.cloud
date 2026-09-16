'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiDelete, apiErrorMessage, apiPost } from '@/lib/api/client'
import { rememberHomeTeam } from '@/lib/homeTeam'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'

/**
 * 「소속」 절의 손짓 — **팀 만들기**와 **팀 나가기**.
 *
 * 🔴 **팀이 없으면 이 서비스가 거의 안 돈다.** 스쿼드 · 경기 신청 · 알림이
 * 전부 `teams/{id}` 밑이라, 새로 가입한 사람은 팀을 만들기 전까지 홈이 빈
 * 판이다. 계약(`POST /teams`)은 처음부터 있었는데 화면이 없어서 실제로는
 * 팀을 만들 방법이 없었다(2026-09-16에 붙임).
 *
 * 🔴 **종목을 안 묻는다**(사용자 결정) — 지금은 풋살만 다룬다. BFF 가 상수로
 * 채운다(`app/api/teams/route.ts`). 종목이 늘면 그 자리와 여기를 같이 연다.
 *
 * 🔴 **마지막 주장은 못 나간다**(`409 LAST_OWNER`). 화면에서 미리 막지 않고
 * 서버가 준 문구를 그대로 보여 준다 — 조건(주장이 몇이냐)은 서버만 알고,
 * 화면이 짐작해서 막으면 나갈 수 있는 사람까지 막힌다.
 */
export default function TeamActions({
  teams,
  userId,
  homeTeamId,
}: {
  teams: { team_id: string; name: string; region: string; sport_code: string; role: string }[]
  /** 나가기가 이 id 로 나간다 — 계약의 `member_id` 는 곧 `user_id` 다. */
  userId: string
  /** 지금 홈에 보이는 팀. 소속이 여럿일 때만 고를 자리가 난다. */
  homeTeamId?: string
}) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [region, setRegion] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  /** 나가는 중인 팀 — 여러 팀이 있어도 누른 줄만 잠긴다. */
  const [leaving, setLeaving] = useState<string | null>(null)

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const made = await apiPost<{ id: string }>('/api/teams', { name, region })
      /* 🔴 **스쿼드도 같이 연다.** 팀만 만들면 `GET /teams/{id}/squad` 가
         404 라 홈 판이 빈 채로 뜨고, 거기 넣은 사람이 서버에 안 남는다.
         멱등이라 두 번 불러도 안전하다(계약 3-7절). */
      await apiPost(`/api/teams/${encodeURIComponent(made.id)}/squad`, {}).catch(() => {
        /* 스쿼드는 나중에 열려도 된다 — 팀이 생긴 것 자체를 실패로 돌리지
           않는다. 홈이 404 를 이미 빈 판으로 다룬다. */
      })
      setName('')
      setRegion('')
      setOpen(false)
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function leave(teamId: string) {
    if (leaving) return
    setLeaving(teamId)
    setError(null)
    try {
      await apiDelete(`/api/teams/${encodeURIComponent(teamId)}/members/${encodeURIComponent(userId)}`)
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setLeaving(null)
    }
  }

  return (
    <>
      {teams.length === 0 ? (
        /* 🔴 **팀이 없으면 이 서비스가 거의 안 돈다** — 스쿼드 · 경기 신청 ·
           알림이 전부 팀 밑이다. 「없습니다」로 끝내지 않고 무엇이 막히는지
           적는다. */
        <p className="ss-profile-muted">
          아직 소속된 팀이 없습니다. 팀을 만들어야 스쿼드와 경기 신청을 쓸 수 있습니다.
        </p>
      ) : (
        <ul className="ss-profile-teams">
          {teams.map((t) => (
            <li key={t.team_id}>
              {/* 🔴 **나가기는 팀 이름 오른쪽**이다(사용자 요청, 2026-09-16) —
                  어느 팀을 나가는지가 이름 옆에 있어야 붙는다. 아래 따로 두면
                  팀이 여럿일 때 어느 줄의 것인지 한 번 더 짚어야 한다. */}
              <p className="ss-profile-team-name">
                <span>{t.name}</span>
                <button
                  type="button"
                  className="ss-profile-team-leave"
                  disabled={leaving === t.team_id}
                  onClick={() => void leave(t.team_id)}
                >
                  {leaving === t.team_id ? '나가는 중…' : '팀 나가기'}
                </button>
              </p>
              <p className="ss-profile-muted">
                {t.region} · {t.sport_code}
              </p>
              {/* 🔴 **소속이 여럿일 때만 낸다.** 하나뿐이면 고를 것이 없고,
                  단추만 있으면 무엇을 고르는 자리인지가 안 읽힌다. */}
              {teams.length > 1 && (
                <button
                  type="button"
                  className="ss-profile-team-home"
                  data-on={homeTeamId === t.team_id ? 'true' : undefined}
                  aria-pressed={homeTeamId === t.team_id}
                  onClick={() => {
                    rememberHomeTeam(t.team_id)
                    router.refresh()
                  }}
                >
                  {homeTeamId === t.team_id ? '홈에 보이는 팀' : '홈에 이 팀 보기'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* 🔴 **팀 만들기는 늘 낸다**(사용자 지적, 2026-09-16 — 「마지막 주장이어도
          새로 만들고 싶을 수 있다」). 계약에 팀 해체도 소유권 이양도 없어서
          마지막 주장은 나갈 수가 없는데, 만들 자리까지 막으면 그 사람은 새
          팀을 시작할 방법이 아예 없다. 미결 `paik` 35번으로 올렸다.

          🔴 그래서 **홈에 보일 팀을 고르는 자리**가 함께 필요하다 — 없으면
          새로 만든 팀이 홈에 안 보인다(홈은 한 팀만 그린다). */}
      <>
          {/* 🔴 **오른쪽 아래 끝**(사용자 요청, 2026-09-16) — 「계정」 판의
              회원 탈퇴와 같은 자리다. 판마다 「지금 할 일」은 위, 「덜 쓰는
              것」은 아래 구석으로 모은다. */}
          <div className="ss-profile-account-foot">
            <button
              type="button"
              className="ss-profile-tab ss-profile-tab--sm"
              aria-expanded={open}
              onClick={() => {
                setOpen((v) => !v)
                setError(null)
              }}
            >
              {open ? '접기' : '팀 만들기'}
            </button>
          </div>

          {/* 🔴 **늘 그리고 접기만 한다**(사용자 요청 — 부드럽게 펴졌다 닫히게).
              `{open && …}` 로 붙였다 뗐다 하면 전환할 대상이 없어 툭 나타난다.
              접는 방식은 「내 경기」의 더보기와 같다(`grid-template-rows`
              0fr → 1fr) — `max-height` 로 하면 상한과 실제 높이가 달라 아무
              일도 안 일어나는 구간에서 시간이 새고 속도가 튄다.

              🔴 접힌 동안에는 **탭으로도 못 닿게** 한다(`inert`) — 안 그러면
              눈에 안 보이는 입력칸에 커서가 들어간다. `aria-hidden` 만으로는
              포커스를 막지 못한다. */}
          <div className="ss-profile-form-fold" data-open={open ? 'true' : 'false'}>
            <div inert={!open}>
              <form onSubmit={create} className="ss-profile-account-form ss-form-compact">
                <Field label="팀 이름" value={name} onChange={setName} />
                <Field label="지역" value={region} onChange={setRegion} hint="예: 서울 강남" />
                {/* 🔴 **가운데**(사용자 요청, 2026-09-16) — 폼이 좁아 왼쪽에
                    붙이면 아래 여백이 비어 보인다. */}
                <PillButton
                  type="submit"
                  disabled={busy || !name.trim() || !region.trim()}
                  className="self-center"
                >
                  만들기
                </PillButton>
              </form>
            </div>
          </div>
      </>

      {error && (
        <p role="alert" className="ss-profile-video-reason">
          {error}
        </p>
      )}
    </>
  )
}
