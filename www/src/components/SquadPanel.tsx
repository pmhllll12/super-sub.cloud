'use client'

import { useState } from 'react'
import GlassPanel from '@/components/ui/GlassPanel'

/**
 * 홈 첫 화면의 스쿼드 판 — 풋살 5인을 채워 넣는 자리다.
 *
 * ⚠️ **아직 서버에 저장하지 않는다.** 계약(api-contract.md)에 스쿼드를
 * 만들거나 사람을 넣는 엔드포인트가 없다 — `GET /me` 의 `teams` 는 이미
 * 소속된 팀을 읽기만 하는 값이다. 그래서 지금은 이 컴포넌트의 상태로만
 * 들고 있고 새로고침하면 사라진다. 백엔드가 생기면 아래 setSquad 를
 * 부르는 자리 셋(추가 · 지우기)을 API 호출로 바꾸면 된다.
 *
 * 브라우저에 저장(localStorage)하지 않은 것도 일부러다 — 서버가 붙는
 * 순간 상태가 두 곳에 생겨 어느 쪽이 진짜인지 헷갈린다.
 */

// 풋살 5인의 자리. 이름은 고정이고 사람만 채운다 — 자리를 사용자가
// 정하게 하면 5인 스쿼드라는 성격이 흐려진다.
const SLOTS = ['GK', 'DF', 'DF', 'MF', 'FW'] as const

export default function SquadPanel() {
  const [squad, setSquad] = useState<(string | null)[]>(() => SLOTS.map(() => null))
  // 지금 이름을 입력받고 있는 칸. null 이면 입력 중인 칸이 없다.
  const [editing, setEditing] = useState<number | null>(null)
  const [draft, setDraft] = useState('')

  function commit(i: number) {
    const name = draft.trim()
    if (name) setSquad((prev) => prev.map((v, n) => (n === i ? name : v)))
    setEditing(null)
    setDraft('')
  }

  const filled = squad.filter(Boolean).length

  return (
    <GlassPanel className="ss-squad">
      <header className="ss-squad-head">
        <h2>MY SQUAD</h2>
        <p>
          {filled} / {SLOTS.length}
        </p>
      </header>

      <ul className="ss-squad-list">
        {SLOTS.map((slot, i) => {
          const name = squad[i]
          return (
            <li key={i}>
              <span className="ss-squad-slot">{slot}</span>

              {editing === i ? (
                <input
                  autoFocus
                  aria-label={`${slot} 선수 이름`}
                  className="ss-squad-input"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={() => commit(i)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') commit(i)
                    if (e.key === 'Escape') {
                      setEditing(null)
                      setDraft('')
                    }
                  }}
                />
              ) : name ? (
                <>
                  <span className="ss-squad-name">{name}</span>
                  <button
                    type="button"
                    aria-label={`${name} 빼기`}
                    className="ss-squad-remove material-symbols-outlined"
                    onClick={() => setSquad((prev) => prev.map((v, n) => (n === i ? null : v)))}
                  >
                    close
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="ss-squad-add"
                  onClick={() => {
                    setEditing(i)
                    setDraft('')
                  }}
                >
                  + 선수 추가
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </GlassPanel>
  )
}
