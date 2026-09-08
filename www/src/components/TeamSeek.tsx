'use client'

import { useEffect, useState } from 'react'
import type { OpenMatch } from '@/server/backend'

/**
 * 「팀원」 판 — **아직 사람을 못 채운 팀들의 명단**(사용자 요청, 2026-09-08).
 *
 * 알약 「팀원」을 누르면 **스쿼드 판이 물러나고 그 자리에** 이 판이 선다.
 * 나란히 세우지 않는 이유: 스쿼드 판은 *내 팀을 짜는* 자리이고 이 판은
 * *남의 팀에 들어가는* 자리라, 한 화면에 두면 어느 쪽을 하고 있는지가
 * 흐려진다. 판 오른쪽의 추천 · 지인 · 챗봇이 "한 번에 하나"인 것과 같은
 * 판단이다.
 *
 * 🔴 **목록이 붙박이가 아니다.** 계약 3-4절의 `GET /matches`(경기 탐색)를
 * 그대로 부른다 — 팀 id 를 몰라도 되는 유일한 경로라, 아직 팀이 없는 사람이
 * 갈 수 있는 곳이 여기뿐이다. 지인 판 · AI 추천 판이 아직 붙박이인 것과
 * 갈리는 점이다(그쪽은 계약에 자리가 없다).
 *
 * 🔴 **모집 글 한 건이 곧 팀 한 줄이다.** 계약이 주는 것은 경기이고 "인원이
 * 덜 찬 팀" 이라는 목록은 따로 없다 — 사람을 못 채웠으니 모집 글을 올린
 * 것이라 그 둘이 같다. 같은 팀이 두 경기를 올렸으면 두 줄로 나온다: 지원하는
 * 쪽이 고르는 것은 팀이 아니라 **그 경기**라 합치지 않는다.
 */

/** 언제 하는 경기인가 — 목록에서 훑으므로 요일까지 적는다. */
function whenText(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}.${p(d.getDate())} (${day}) ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 몇 자리가 비었나 — 「인원을 못 채웠다」가 이 판의 제목이라 합을 앞세운다. */
function openSeats(m: OpenMatch): number {
  return m.needs.reduce((sum, n) => sum + n.head_count, 0)
}

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; items: OpenMatch[]; total: number }
  | { kind: 'error'; message: string }

export default function TeamSeek({
  closing,
  onClose,
}: {
  /** 닫히는 중 — 사라지는 동안에도 DOM 에 남아야 애니메이션이 보인다. */
  closing: boolean
  onClose: () => void
}) {
  const [state, setState] = useState<State>({ kind: 'loading' })

  /**
   * 🔴 **판이 열릴 때 한 번만 받는다.** 그릴 때 부르면 서버가 그린 첫 화면과
   * 갈려 하이드레이션이 깨진다(공개 목록 · 카드 꾸미기에서 데인 자리와 같다).
   */
  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const res = await fetch('/api/matches?size=20')
        const body: unknown = await res.json().catch(() => null)
        if (!alive) return
        if (!res.ok) {
          const msg =
            typeof body === 'object' && body !== null && 'error' in body
              ? ((body as { error?: { message?: string } }).error?.message ?? null)
              : null
          setState({ kind: 'error', message: msg ?? '목록을 가져오지 못했습니다.' })
          return
        }
        const page = body as { items?: OpenMatch[]; total?: number }
        setState({ kind: 'ok', items: page.items ?? [], total: page.total ?? 0 })
      } catch {
        if (alive) setState({ kind: 'error', message: '목록을 가져오지 못했습니다.' })
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  return (
    <section
      className="ss-teams"
      data-closing={closing ? 'true' : undefined}
      aria-label="사람을 찾는 팀"
      // 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에 두면
      // Lightning CSS 를 지나며 떨어져 나간 전례가 있다(추천 판 · 시작 단추).
      style={{
        backdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
        WebkitBackdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
      }}
    >
      <header className="ss-teams-head">
        <h2>사람을 찾는 팀</h2>
        <button type="button" className="ss-teams-close" onClick={onClose} aria-label="닫기">
          <span className="material-symbols-outlined" aria-hidden="true">
            close
          </span>
        </button>
      </header>

      {state.kind === 'loading' && <p className="ss-teams-note">불러오는 중입니다…</p>}

      {/* 🔴 실패를 빈 목록으로 그리지 않는다 — "못 가져왔다"와 "그런 팀이
          없다"가 같아 보이면 없는 것을 계속 기다리게 된다. */}
      {state.kind === 'error' && (
        <p className="ss-teams-note" data-error="true" role="alert">
          {state.message}
        </p>
      )}

      {state.kind === 'ok' && state.items.length === 0 && (
        <p className="ss-teams-note">지금은 사람을 찾는 팀이 없습니다.</p>
      )}

      {state.kind === 'ok' && state.items.length > 0 && (
        <>
          <p className="ss-teams-count">{state.total}팀이 자리를 채우고 있습니다</p>
          <ul className="ss-teams-list">
            {state.items.map((m) => (
              <li key={m.id} className="ss-teams-row">
                <span className="ss-teams-name">{m.team_name}</span>
                <span className="ss-teams-where">
                  {m.region} · {m.place}
                </span>
                <span className="ss-teams-when">{whenText(m.played_at)}</span>
                {/* 어느 자리가 비었는지가 이 목록을 고르는 기준이다 — 자리
                    이름과 인원을 그대로 적는다(계약이 이름까지 준다). */}
                <span className="ss-teams-needs">
                  {m.needs.map((n) => (
                    <span key={n.position_code} className="ss-teams-need">
                      {n.position_label} {n.head_count}
                    </span>
                  ))}
                </span>
                <span className="ss-teams-seats">{openSeats(m)}자리</span>
              </li>
            ))}
          </ul>
          {/* ⚠️ 지원(신청)은 아직 없다. 계약에는 `POST /matches/{id}/applications`
              가 있지만 이번에 요청받은 것은 **명단까지**다 — 없는 단추를 그려
              두면 눌러 보고 아무 일도 안 일어난다. */}
          <p className="ss-teams-foot">고르는 것은 다음 회차입니다 — 지금은 명단까지입니다.</p>
        </>
      )}
    </section>
  )
}
