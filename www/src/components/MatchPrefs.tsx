'use client'

import { useEffect, useId, useState } from 'react'
import { searchRegions } from '@/lib/regions'
import { fetchPositions } from '@/lib/positions'
import {
  DAYS,
  EMPTY_PREFS,
  HOURS,
  slotText,
  type MatchPrefs as Prefs,
  type PrefsKind,
} from '@/lib/matchPrefs'

/**
 * **어떤 경기를 찾으세요?** — 조건을 묻는 판(사용자 결정, 2026-09-10).
 *
 * 🔴 **팀장 · 팀원이 같은 조각을 쓴다.** 두 벌로 만들면 한쪽만 고쳐진다 —
 * 갈리는 것은 「내 자리」 칸 하나뿐이라 `kind` 로 가른다.
 *
 * 🔴 **처음 한 번만 묻는다.** 정하고 나면 다음부터는 바로 명단이 나오고,
 * 고칠 일이 있으면 명단 머리의 「설정 수정」으로 다시 연다 — 설정을 따로
 * 찾아가게 하지 않는다.
 */
export default function MatchPrefsForm({
  kind,
  sportCode = null,
  value,
  onDone,
  onCancel,
}: {
  kind: PrefsKind
  /** 「내 자리」 후보를 받아 올 종목 — 팀원 쪽에서만 쓴다. */
  sportCode?: string | null
  /** 고치는 중이면 지금 값. 처음이면 비어 있다. */
  value?: Prefs | null
  onDone: (prefs: Prefs) => void
  /** 고치다 그만두기 — 처음 묻는 자리에서는 안 준다(그만둘 데가 없다). */
  onCancel?: () => void
}) {
  const [prefs, setPrefs] = useState<Prefs>(value ?? EMPTY_PREFS)
  const [query, setQuery] = useState('')
  const regionId = useId()

  /** 「내 자리」 후보 — 🔴 `GET /positions` 가 정본이다(하드코딩하지 않는다). */
  const [posOptions, setPosOptions] = useState<{ code: string; label: string }[]>([])
  useEffect(() => {
    if (kind !== 'me' || !sportCode) return
    let alive = true
    void fetchPositions(sportCode).then((list) => {
      if (alive) setPosOptions(list.map((p) => ({ code: p.code, label: p.label })))
    })
    return () => {
      alive = false
    }
  }, [kind, sportCode])

  const hits = searchRegions(query, prefs.regions)

  function addRegion(name: string) {
    setPrefs((p) => ({ ...p, regions: [...p.regions, name] }))
    // 고르고 나면 적던 것을 비운다 — 안 비우면 후보가 그대로 떠 있다.
    setQuery('')
  }

  /** 🔴 **적어도 하나는 있어야 찾을 수 있다.** 빈 조건으로는 아무것도 못 좁힌다. */
  const ready = prefs.regions.length > 0 && prefs.times.length > 0

  return (
    <form
      className="ss-prefs"
      onSubmit={(e) => {
        e.preventDefault()
        if (ready) onDone(prefs)
      }}
    >
      <h2 className="ss-prefs-h">어떤 경기를 찾으세요?</h2>

      {/* 🔴 `<fieldset>`/`<legend>` 를 안 쓴다 — 브라우저가 legend 를 **테두리에
          홈을 파고 얹어서** 글자와 상자가 겹친다(사용자 지적, 2026-09-10).
          판의 다른 곳(`.ss-teams-sports`)이 이미 쓰는 `role="group"` 으로 두면
          모양을 온전히 정할 수 있고 낭독기에도 같은 뜻으로 전해진다. */}
      <div className="ss-prefs-field" role="group" aria-labelledby={`${regionId}-l`}>
        <p className="ss-prefs-legend" id={`${regionId}-l`}>
          어느 동네에서
        </p>
        {/* 🔴 자유 입력이지만 **저장되는 값은 목록의 것**이다 — 안 그러면
            「강남구」·「서울 강남구」가 다른 값이 되어 대조가 안 된다. */}
        <input
          id={regionId}
          type="text"
          className="ss-prefs-input"
          value={query}
          placeholder="동네 이름을 적으세요"
          autoComplete="off"
          onChange={(e) => setQuery(e.target.value)}
        />
        {hits.length > 0 && (
          <ul className="ss-prefs-hits">
            {hits.map((r) => (
              <li key={r}>
                <button type="button" className="ss-prefs-hit" onClick={() => addRegion(r)}>
                  {r}
                </button>
              </li>
            ))}
          </ul>
        )}
        {/* 적은 것이 목록에 없으면 그렇게 말한다 — 조용히 비어 있으면 고장으로 읽힌다. */}
        {query.trim() && hits.length === 0 && (
          <p className="ss-prefs-none">그런 동네가 목록에 없습니다.</p>
        )}
        <ul className="ss-prefs-chips">
          {prefs.regions.map((r) => (
            <li key={r}>
              <button
                type="button"
                className="ss-prefs-chip"
                aria-label={`${r} 빼기`}
                onClick={() =>
                  setPrefs((p) => ({ ...p, regions: p.regions.filter((x) => x !== r) }))
                }
              >
                {r} <span aria-hidden="true">⊗</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="ss-prefs-field" role="group" aria-labelledby={`${regionId}-t`}>
        <p className="ss-prefs-legend" id={`${regionId}-t`}>
          언제
        </p>
        <ul className="ss-prefs-times">
          {prefs.times.map((t, i) => (
            <li key={i} className="ss-prefs-time">
              <select
                aria-label="요일"
                value={t.day}
                onChange={(e) =>
                  setPrefs((p) => ({
                    ...p,
                    times: p.times.map((x, j) =>
                      j === i ? { ...x, day: Number(e.target.value) } : x,
                    ),
                  }))
                }
              >
                {DAYS.map((d, n) => (
                  <option key={d} value={n}>
                    {d}요일
                  </option>
                ))}
              </select>
              <select
                aria-label="시작 시각"
                value={t.from}
                onChange={(e) =>
                  setPrefs((p) => ({
                    ...p,
                    times: p.times.map((x, j) =>
                      /* 🔴 시작이 끝을 넘으면 끝을 밀어 준다 — 뒤집힌 시간은
                         겹침 계산에서 늘 거짓이라 조용히 아무것도 안 걸린다. */
                      j === i
                        ? {
                            ...x,
                            from: e.target.value,
                            to: x.to <= e.target.value ? nextHour(e.target.value) : x.to,
                          }
                        : x,
                    ),
                  }))
                }
              >
                {HOURS.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              <span aria-hidden="true">~</span>
              <select
                aria-label="끝 시각"
                value={t.to}
                onChange={(e) =>
                  setPrefs((p) => ({
                    ...p,
                    times: p.times.map((x, j) => (j === i ? { ...x, to: e.target.value } : x)),
                  }))
                }
              >
                {/* 시작보다 뒤만 고를 수 있다 — 뒤집힌 시간을 만들 수가 없다. */}
                {HOURS.filter((h) => h > t.from).map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="ss-prefs-drop"
                aria-label={`${slotText(t)} 빼기`}
                onClick={() =>
                  setPrefs((p) => ({ ...p, times: p.times.filter((_, j) => j !== i) }))
                }
              >
                ⊗
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="ss-prefs-add"
          onClick={() =>
            setPrefs((p) => ({ ...p, times: [...p.times, { day: 6, from: '09:00', to: '11:00' }] }))
          }
        >
          + 시간 추가
        </button>
      </div>

      {/* 🔴 **팀원 쪽에만** 있는 칸이다 — 팀은 자리를 고르지 않는다. */}
      {kind === 'me' && posOptions.length > 0 && (
        <div className="ss-prefs-field" role="group" aria-labelledby={`${regionId}-p`}>
          <p className="ss-prefs-legend" id={`${regionId}-p`}>
            내 자리
          </p>
          <ul className="ss-prefs-chips">
            {posOptions.map((p) => {
              const on = prefs.positions.includes(p.code)
              return (
                <li key={p.code}>
                  <button
                    type="button"
                    className="ss-prefs-chip"
                    data-on={on ? 'true' : undefined}
                    aria-pressed={on}
                    onClick={() =>
                      setPrefs((cur) => ({
                        ...cur,
                        positions: on
                          ? cur.positions.filter((c) => c !== p.code)
                          : [...cur.positions, p.code],
                      }))
                    }
                  >
                    {p.label}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <div className="ss-prefs-actions">
        {onCancel && (
          <button type="button" className="ss-prefs-cancel" onClick={onCancel}>
            그만두기
          </button>
        )}
        {/* 동네와 시간이 하나씩은 있어야 찾을 수 있다 — 없으면 못 누른다. */}
        <button type="submit" className="ss-prefs-go" disabled={!ready}>
          팀 찾기
        </button>
      </div>

      {/* ⚠️ 어디에 남는지 밝힌다 — 계약에 자리가 없다. */}
      <p className="ss-prefs-note">아직 이 브라우저에만 남습니다.</p>
    </form>
  )
}

/** 그 시각의 30분 뒤 — 없으면(24:00) 그대로 둔다. */
function nextHour(h: string): string {
  const at = HOURS.indexOf(h)
  return at >= 0 && at + 1 < HOURS.length ? HOURS[at + 1] : h
}
