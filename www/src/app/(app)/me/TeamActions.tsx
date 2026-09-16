'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiDelete, apiErrorMessage, apiPost } from '@/lib/api/client'
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
}: {
  teams: { team_id: string; name: string; role: string }[]
  /** 나가기가 이 id 로 나간다 — 계약의 `member_id` 는 곧 `user_id` 다. */
  userId: string
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
      {teams.length > 0 && (
        <ul className="ss-profile-team-acts">
          {teams.map((t) => (
            <li key={t.team_id}>
              <button
                type="button"
                className="ss-profile-team-leave"
                disabled={leaving === t.team_id}
                onClick={() => void leave(t.team_id)}
              >
                {leaving === t.team_id ? '나가는 중…' : `${t.name} 나가기`}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* 🔴 **평소에는 접혀 있다** — 프로필은 보여주는 화면이고, 폼이 늘 펴져
          있으면 설정 화면처럼 읽힌다(`AccountActions` 와 같은 판단). */}
      <button
        type="button"
        className="ss-profile-tab"
        aria-expanded={open}
        onClick={() => {
          setOpen((v) => !v)
          setError(null)
        }}
      >
        {open ? '접기' : '팀 만들기'}
      </button>

      {open && (
        <form onSubmit={create} className="ss-profile-account-form">
          <Field label="팀 이름" value={name} onChange={setName} />
          <Field label="지역" value={region} onChange={setRegion} hint="예: 서울 강남" />
          <PillButton type="submit" disabled={busy || !name.trim() || !region.trim()}>
            만들기
          </PillButton>
        </form>
      )}

      {error && (
        <p role="alert" className="ss-profile-video-reason">
          {error}
        </p>
      )}
    </>
  )
}
