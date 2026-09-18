'use client'

import { useEffect, useState } from 'react'
import type { PublicPlayerCard } from '@/server/backend'

/**
 * **판 위의 사람을 누르면 뜨는 간단한 프로필** (사용자 요청, 2026-09-18:
 * "카드를 클릭하면 클릭한 대상의 프로필을 간단하게 볼수있으면 좋겠어.
 * 랭크라던가 별명같은거").
 *
 * 🔴 **경기 화면을 닫지 않는다.** 이 조각은 경기 화면 **위에** 뜨는 작은
 * 칸이고, 닫으면 경기 화면이 그대로 남는다 — 사용자가 못 박은 조건이
 * 「경기매칭된 상태는 유지 되어야해」였다. 그래서 새 경로로 보내지 않고
 * (`/cards/{slug}` 로 이동하면 홈을 떠난다) 같은 화면에서 읽는다.
 *
 * 🔴 **좁은 칸만 읽는다.** 등급은 `GET /cards/{slug}/grade` 가 주는 한 칸
 * (+`provisional`, `notes`)이 전부다 — 항목별 점수·근거는 **자기 것만** 본다는
 * 것이 계약의 선이다(3-6절). 여기서 리포트를 통째로 열지 않는다.
 */

/** 등급 한 칸 — 계약 3-6절. `grade` 는 대표 영상이 없거나 분석 전이면 `null`. */
type Grade = {
  grade: string | null
  provisional: boolean
  notes: string[] | null
}

type State =
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'ok'; card: PublicPlayerCard | null; grade: Grade | null }

export default function WhoCard({
  slug,
  fallbackName,
  onClose,
}: {
  /**
   * 그 사람 **카드의 공개 슬러그**.
   *
   * ⚠️ **없을 수 있다** — 카드를 아직 안 만든 사람이다. 그때는 부르지 않고
   * 이름만 보여 준다(부르는 쪽이 `null` 을 넘기지 않게 막아도 되지만, 여기서
   * 도 견디는 편이 안전하다).
   */
  slug: string | null
  /** 카드를 못 읽었을 때 적을 이름 — 판이 이미 알고 있는 값이다. */
  fallbackName: string
  onClose: () => void
}) {
  const [state, setState] = useState<State>({ kind: 'loading' })

  /* 🔴 **부르는 쪽이 `key={slug}` 로 다시 붙인다**(`MatchWaiting`). 그래서
     여기서 「사람이 바뀌었으니 처음 상태로」를 따로 하지 않아도 된다 —
     effect 안에서 상태를 되돌리면 그릴 때마다 한 번 더 그려진다. */
  useEffect(() => {
    /* 카드를 아직 안 만든 사람이면 부를 데가 없다 — 아래에서 이름만 그린다. */
    if (!slug) return
    let alive = true
    void (async () => {
      /* 🔴 **둘을 같이 부르고, 한쪽이 실패해도 나머지는 그린다.** 등급은
         대표 영상이 없으면 아예 없는 것이 정상이라, 그것 때문에 이름까지
         안 보이면 안 된다. */
      const [cardRes, gradeRes] = await Promise.allSettled([
        fetch(`/api/cards/${encodeURIComponent(slug)}`),
        fetch(`/api/cards/${encodeURIComponent(slug)}/grade`),
      ])
      if (!alive) return
      const card =
        cardRes.status === 'fulfilled' && cardRes.value.ok
          ? ((await cardRes.value.json().catch(() => null)) as PublicPlayerCard | null)
          : null
      const grade =
        gradeRes.status === 'fulfilled' && gradeRes.value.ok
          ? ((await gradeRes.value.json().catch(() => null)) as Grade | null)
          : null
      if (!alive) return
      setState(card || grade ? { kind: 'ok', card, grade } : { kind: 'error' })
    })()
    return () => {
      alive = false
    }
  }, [slug])

  /* Esc 로 닫는다 — 경기 화면도 같은 방식이라 손이 헷갈리지 않는다.
     🔴 **여기서 멈춘다**(stopPropagation) — 안 그러면 한 번 눌러 경기 화면까지
     같이 닫힌다. 「경기매칭된 상태는 유지 되어야해」가 사용자의 조건이다. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      onClose()
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [onClose])

  /* 슬러그가 없으면 부른 적이 없으므로 「다 읽었고 아무것도 없다」로 그린다. */
  const shown: State = slug ? state : { kind: 'ok', card: null, grade: null }
  const name = shown.kind === 'ok' ? (shown.card?.user.nickname ?? fallbackName) : fallbackName
  const grade = shown.kind === 'ok' ? shown.grade : null

  return (
    <aside className="ss-who" aria-label={`${name} 프로필`}>
      <div className="ss-who-head">
        <div>
          <div className="ss-who-name">{name}</div>
          {shown.kind === 'ok' && shown.card?.tagline && (
            <div className="ss-who-sub">{shown.card.tagline}</div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {grade?.grade ? (
            <span className="ss-who-grade">
              {grade.grade}
              {/* 🔴 **「검수 전」은 반드시 같이 적는다** — 계약이 못 박은 것이다.
                  등급 문자만 떼어 쓰면 남의 화면에 박힌 뒤 회수가 안 된다. */}
              {grade.provisional && <span className="ss-who-prov">검수 전</span>}
            </span>
          ) : null}
          <button type="button" className="ss-who-close" onClick={onClose} aria-label="닫기">
            ×
          </button>
        </div>
      </div>

      {shown.kind === 'loading' && <div className="ss-who-sub">읽는 중…</div>}
      {shown.kind === 'error' && <div className="ss-who-sub">프로필을 읽지 못했습니다.</div>}

      {/* 🔴 등급이 `null` 인 것은 **고장이 아니다** — 대표 영상이 없거나 아직
          분석 전이다. 그 사실을 적어 준다(빈칸으로 두면 오류로 읽힌다). */}
      {shown.kind === 'ok' && !grade?.grade && (
        <div className="ss-who-sub">아직 분석된 등급이 없습니다.</div>
      )}

      {shown.kind === 'ok' && (shown.card?.titles.length ?? 0) > 0 && (
        <div className="ss-who-titles">
          {shown.card?.titles.map((t) => (
            <span key={t.code} className="ss-who-title">
              {t.label}
            </span>
          ))}
        </div>
      )}

      {/* 분석이 낸 한두 줄. 🔴 **화면이 짓지 않는다** — 없으면 안 그린다. */}
      {grade?.notes && grade.notes.length > 0 && (
        <ul className="ss-who-notes">
          {grade.notes.map((n) => (
            <li key={n}>· {n}</li>
          ))}
        </ul>
      )}
    </aside>
  )
}
