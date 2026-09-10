'use client'

import { useEffect, useState } from 'react'
import { applyToTeam, findTeams, type MatchTeam } from '@/lib/teamMatch'
import MatchPrefsForm from '@/components/MatchPrefs'
import { loadPrefs, savePrefs, type MatchPrefs } from '@/lib/matchPrefs'

/**
 * **비슷한 팀 명단** — 「팀 매칭」을 누르면 판 오른쪽에 선다(사용자 요청,
 * 2026-09-10).
 *
 * 자리를 다 채운 팀들 중 **우리와 조건이 비슷한** 쪽을 골라 보여 주고, 줄마다
 * 경기를 신청할 수 있다. 신청하면 상대 팀장의 수락을 기다리고, 수락되면
 * 대기 팝업(`MatchWaiting`)이 뜬다.
 *
 * 🔴 **판을 대신 서지 않고 오른쪽에 선다**(사용자 결정) — 내 스쿼드를 보면서
 * 상대를 골라야 하기 때문이다. 그래서 「팀원」 판(판 자리를 대신 차지)과
 * 다르고, 추천 판 · 챗봇과 **같은 칸을 나눠 쓴다**(한 번에 하나).
 *
 * 🔴 **처음에는 조건부터 묻는다**(사용자 결정, 2026-09-10). 「어느 동네에서 ·
 * 언제」를 모르면 무엇을 비슷하다고 할 근거가 없다 — 명단의 알약이 그 대조
 * 결과다. 한 번 정하면 다음부터는 바로 명단이고, 머리의 「설정 수정」로
 * 다시 연다(설정을 따로 찾아가게 하지 않는다).
 *
 * ⚠️ **여기서 서버로 나가는 것은 하나도 없다** — 무엇이 없는지는
 * `lib/teamMatch.ts` 첫머리에 있다.
 */

/** `2026-09-20T10:00:00` → `토 10:00`. 명단은 훑는 자리라 짧게 적는다. */
function whenText(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${day} ${p(d.getHours())}:${p(d.getMinutes())}`
}

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; teams: MatchTeam[] }

export default function TeamMatch({
  size,
  closing,
  onClose,
  onMatched,
}: {
  /** 우리 판 크기 — **같은 크기의 팀만** 찾는다. */
  size: string
  /** 닫히는 중 — 물러나는 동안 DOM 에 남아야 애니메이션이 보인다. */
  closing: boolean
  onClose: () => void
  /** 상대가 수락했다 — 대기 팝업을 띄우는 것은 부모의 몫이다. */
  onMatched: (team: MatchTeam) => void
}) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  /** 지금 수락을 기다리는 팀. 하나뿐이다 — 두 곳에 동시에 신청하지 않는다. */
  const [waiting, setWaiting] = useState<string | null>(null)

  /**
   * 정해 둔 조건. `null` 은 **아직 안 정했다**는 뜻이라 조건 판이 뜬다 —
   * 빈 조건(다 지운 것)과 갈라야 한다.
   *
   * 🔴 **그릴 때 저장소를 읽지 않는다**(하이드레이션) — 붙은 뒤에 읽는다.
   * 그동안은 「찾고 있습니다」가 떠 있어 화면이 비지 않는다.
   */
  const [prefs, setPrefs] = useState<MatchPrefs | null>(null)
  const [asking, setAsking] = useState(false)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const saved = loadPrefs('team')
    setPrefs(saved)
    setAsking(saved === null)
    setReady(true)
  }, [])

  useEffect(() => {
    if (!prefs) return
    let alive = true
    setState({ kind: 'loading' })
    void findTeams(size, prefs).then((teams) => {
      if (alive) setState({ kind: 'ok', teams })
    })
    return () => {
      alive = false
    }
  }, [size, prefs])

  /**
   * 🔴 **한 번에 한 곳에만 신청한다.** 여러 곳에 걸어 두면 둘이 동시에
   * 수락했을 때 어느 경기가 잡힌 것인지 화면이 답할 수 없다.
   */
  async function apply(team: MatchTeam) {
    if (waiting) return
    setWaiting(team.id)
    const { accepted } = await applyToTeam(team.id)
    if (accepted) onMatched(team)
    setWaiting(null)
  }

  return (
    <section
      className="ss-tm"
      data-closing={closing ? 'true' : undefined}
      aria-label="비슷한 팀"
      /* 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에 두면
         Lightning CSS 를 지나며 떨어져 나간 전례가 있다.

         🔴 **흐림을 판에서 올린다**(사용자 요청, 2026-09-10 — 「안 읽힌다」).
         줄마다 걸 수가 없다: 이 판이 펼쳐지는 연출로 `transform` 을 계속
         쥐고 있어 **변형된 조상이 backdrop root 를 만들고**, 자식의 흐림은
         조용히 죽는다. 그래서 흐림은 여기서 한 번에 세게 걸고, 글자가
         읽히는 일은 줄의 검은 막(`.ss-tm-row`)이 맡는다.

         ⚠️ `--ss-glass-blur` 를 **전역에서 올리지 않는다** — 로그인 카드 ·
         홈 카드 · 추천 판이 다 같이 흐려진다. 여기서만 배로 쓴다. */
      style={{
        backdropFilter:
          'blur(calc(var(--ss-glass-blur) * 2)) saturate(var(--ss-glass-saturate))',
        WebkitBackdropFilter:
          'blur(calc(var(--ss-glass-blur) * 2)) saturate(var(--ss-glass-saturate))',
      }}
    >
      <header className="ss-tm-head">
        <h2>비슷한 팀</h2>
        <div className="ss-tm-head-right">
          {/* 조건을 정해 둔 뒤에만 나온다 — 정하는 중에 또 열 자리는 없다. */}
          {prefs && !asking && (
            <button type="button" className="ss-tm-edit" onClick={() => setAsking(true)}>
              {/* 🔴 아이콘은 **장식**이라 낭독기에서 숨긴다 — 옆의 글자가
                  이미 무엇인지 말하고 있다(두 번 읽히면 성가시다). */}
              <span className="material-symbols-outlined" aria-hidden="true">
                rule_settings
              </span>
              설정 수정
            </button>
          )}
          <button type="button" className="ss-tm-close" onClick={onClose} aria-label="닫기">
            <span className="material-symbols-outlined" aria-hidden="true">
              close
            </span>
          </button>
        </div>
      </header>

      {/* 🔴 조건이 먼저다 — 없으면 명단을 아예 안 그린다. */}
      {asking && (
        <MatchPrefsForm
          kind="team"
          value={prefs}
          onDone={(next) => {
            savePrefs('team', next)
            setPrefs(next)
            setAsking(false)
          }}
          /* 처음 묻는 자리에서는 그만둘 데가 없다 — 고칠 때만 준다. */
          onCancel={prefs ? () => setAsking(false) : undefined}
        />
      )}

      {!asking && (!ready || state.kind === 'loading') && (
        <p className="ss-tm-note">비슷한 팀을 찾고 있습니다…</p>
      )}

      {!asking && state.kind === 'ok' && state.teams.length === 0 && (
        <p className="ss-tm-note">지금은 조건이 맞는 팀이 없습니다.</p>
      )}

      {!asking && state.kind === 'ok' && state.teams.length > 0 && (
        <ul className="ss-tm-list">
          {state.teams.map((t) => (
            <li key={t.id} className="ss-tm-row">
              <span className="ss-tm-name">{t.name}</span>
              <span className="ss-tm-where">
                {t.region} · {whenText(t.playedAt)}
              </span>
              {/* 🔴 **왜 이 팀이 나왔는지 적는다**(사용자 결정). 근거 없이
                  「비슷합니다」만 말하면 목록을 믿을 근거가 없다. */}
              <span className="ss-tm-why">
                {t.why.map((w) => (
                  <span key={w} className="ss-tm-tag">
                    {w}
                  </span>
                ))}
              </span>
              <button
                type="button"
                className="ss-tm-apply"
                /* 다른 곳에 신청해 둔 동안에는 못 누른다 — 위 `apply` 주석. */
                disabled={waiting !== null}
                onClick={() => void apply(t)}
              >
                {waiting === t.id ? '수락을 기다립니다…' : '경기 신청'}
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* ⚠️ 아무 데도 안 보낸다는 것을 밝힌다 — 숨기면 진짜 신청된 줄 안다. */}
      {!asking && (
        <p className="ss-tm-foot">아직 데모입니다 — 신청이 실제로 상대에게 가지 않습니다.</p>
      )}
    </section>
  )
}
