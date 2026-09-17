'use client'

import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { apiPost } from '@/lib/api/client'

/**
 * 스쿼드 판 옆에서 나오는 **지인 찾기** 판 — 닉네임으로 찾아 고르면,
 * 스쿼드 판의 빈 자리를 눌러 그 자리에 앉힌다.
 *
 * 🔴 **자리는 여기서 안 고른다.** 작은 스쿼드 판을 여기 하나 더 그리는
 * 안도 있었지만(사용자 제안), 그러면 한 화면에 스쿼드 판이 둘이 되어
 * 어느 쪽이 진짜인지 헷갈린다 — 이 저장소가 `/`·`/home` 과 '내 프로필'
 * 에서 이미 두 번 같은 판단을 했다. 게다가 1-2-1 은 MF 가 둘이라 포지션
 * 이름만으로는 어느 쪽인지 못 고른다. **왼쪽 판의 진짜 자리를 직접**
 * 누르면 그 모호함이 아예 생기지 않는다.
 *
 * ✅ **2026-09-16 — 붙박이 명단을 걷고 진짜 사용자를 부른다**(계약 3-12절,
 * CCC 37번). 전에는 이 파일에 8명이 박혀 있었다.
 *
 * 🔴 **세 목록은 성격이 다르다. 하나로 합치면 안 된다.**
 *
 *   받은 신청 — `GET /me/contacts/requests` · 수락해야 지인이 된다
 *   내 지인   — `GET /me/contacts`          · **여기 있는 사람만 판에 앉힌다**
 *   검색 결과 — `GET /users/search?q=`      · 아직 남이다. 신청만 보낸다
 *
 * 지인은 **상호 관계**라서(신청 → 수락) 검색으로 나온 사람을 곧바로 판에
 * 앉힐 수는 없다. 앉히기는 `onChoose` 로 나가는데, 그 사람이 정말 내 팀에
 * 들어올 사람인지는 상대의 수락으로만 확인되기 때문이다.
 */

type Contact = {
  contact_id: string
  user_id: string
  nickname: string
  note: string | null
  accepted_at: string
  /**
   * 그 사람의 공개 카드 슬러그 — 카드를 안 만들었으면 `null`(미결 `paik` 39번).
   * 🔴 **이것이 있어야 판에 앉혔을 때 그 사람 카드가 뜬다.** 없으면 이름표다.
   */
  card_public_slug: string | null
}

type ContactRequest = {
  id: string
  requester_user_id: string
  target_user_id: string
  note: string | null
  created_at: string
}

type Found = { id: string; nickname: string }

/** 입력이 멎고 이만큼 지나야 서버에 묻는다 — 글자마다 부르면 목록이 깜빡인다. */
const SEARCH_DEBOUNCE_MS = 250

export default function SquadFriends({
  placing,
  placed,
  closing,
  onChoose,
  onClose,
}: {
  /** 지금 골라 둔 지인. 이 사람이 정해지면 왼쪽 판의 빈 자리를 누를 차례다. */
  placing: string | null
  /**
   * 이미 스쿼드에 들어가 있는 사람 → 그 자리 이름(`MF` 등).
   *
   * 🔴 **표식이 없으면 목록에서 구별이 안 된다.** 방금 넣은 사람이 그대로
   * 평범한 줄로 남아 있어 또 고르게 된다 — 실제로 같은 사람을 두 자리에
   * 넣을 수 있었다. 여기 있는 사람은 고를 수 없다(빼는 것은 왼쪽 판의
   * 그 카드를 누르는 것이다 — 넣고 빼는 곳이 둘로 갈리면 더 헷갈린다).
   */
  placed: Record<string, string>
  /** 닫히는 중 — 사라지는 동안에도 DOM 에 남아 있어야 애니메이션이 보인다. */
  closing: boolean
  /**
   * 앉힐 사람을 고른다 — **슬러그도 같이 넘긴다**(2026-09-17). 이름만
   * 넘기면 판이 그 사람의 진짜 카드를 못 그린다(빈 카드에 이름만 찍힌다).
   */
  onChoose: (nickname: string | null, cardSlug: string | null) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const [contacts, setContacts] = useState<Contact[] | null>(null)
  const [requests, setRequests] = useState<ContactRequest[]>([])
  const [found, setFound] = useState<Found[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  /**
   * 내가 방금 신청을 보낸 사람들.
   *
   * 🔴 **서버에 물어볼 길이 없다** — 계약에 「내가 보낸 신청」 경로가 없고
   * (`/me/contacts/requests` 는 *받은* 것만 준다), 수락 전까지는 어느
   * 목록에도 안 나온다. 그래서 누른 사실은 이 화면이 들고 있어야 한다.
   * 새로고침하면 사라진다 — 그때는 다시 눌러도 409 로 막히니 안전하다.
   */
  const [requested, setRequested] = useState<Record<string, true>>({})
  const inputId = useId()

  /** 지인 · 받은 신청을 다시 읽는다. 수락 직후에도 부른다. */
  const reload = useCallback(async () => {
    try {
      const [cRes, rRes] = await Promise.all([
        fetch('/api/me/contacts'),
        fetch('/api/me/contacts/requests'),
      ])
      if (cRes.ok) {
        const body = (await cRes.json().catch(() => null)) as { items?: Contact[] } | null
        setContacts(body?.items ?? [])
      } else {
        setContacts([])
      }
      if (rRes.ok) {
        const body = (await rRes.json().catch(() => null)) as ContactRequest[] | null
        setRequests(Array.isArray(body) ? body : [])
      }
    } catch {
      setContacts([])
      setError('지인 목록을 가져오지 못했습니다.')
    }
  }, [])

  useEffect(() => {
    // 판이 열릴 때 한 번 읽는다. 규칙은 effect 안의 setState 를 싫어하지만
    // 여기서 바뀌는 것은 **응답이 온 뒤**다(동기 렌더를 더 부르지 않는다).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload()
  }, [reload])

  // 닉네임 검색 — 입력이 멎으면 묻는다. 비우면 서버를 안 부르고 결과만 지운다
  // (계약의 `q` 는 필수라 빈 값은 부를 것이 없다).
  const timer = useRef(0)
  useEffect(() => {
    const q = query.trim()
    clearTimeout(timer.current)
    if (!q) {
      /* 🔴 **지난 결과를 지운다.** 안 지우면 검색어를 비웠다가 다른 이름을
         칠 때, 기다리는 0.25초 동안 **앞사람의 결과**가 그대로 붙어 있다. */
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFound(null)
      setSearching(false)
      return
    }
    setSearching(true)
    let alive = true
    timer.current = window.setTimeout(() => {
      void (async () => {
        try {
          const res = await fetch(`/api/users/search?q=${encodeURIComponent(q)}`)
          if (!alive) return
          const body = (await res.json().catch(() => null)) as Found[] | null
          setFound(res.ok && Array.isArray(body) ? body : [])
        } catch {
          if (alive) setFound([])
        } finally {
          if (alive) setSearching(false)
        }
      })()
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      alive = false
      clearTimeout(timer.current)
    }
  }, [query])

  async function request(user: Found) {
    setError(null)
    try {
      await apiPost('/api/me/contacts', { target_user_id: user.id })
      setRequested((prev) => ({ ...prev, [user.id]: true }))
    } catch (e) {
      // 🔴 **409 는 오류로 보여주지 않는다** — "이미 신청했거나 이미 지인"은
      // 사용자가 잘못한 것이 아니다. 보낸 것으로 표시하고 넘어간다.
      if (e instanceof Error && 'code' in e && e.code === 'ALREADY_REQUESTED') {
        setRequested((prev) => ({ ...prev, [user.id]: true }))
        return
      }
      setError(e instanceof Error ? e.message : '신청하지 못했습니다.')
    }
  }

  async function accept(id: string) {
    setError(null)
    try {
      await apiPost(`/api/me/contacts/${encodeURIComponent(id)}/accept`, null)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : '수락하지 못했습니다.')
    }
  }

  /**
   * 🔴 **치는 동안에도 내 지인은 계속 걸러서 보여준다.** 검색으로 갈아타
   * 버리면, 이미 지인인 사람을 찾으려고 이름을 쳤을 때 그 사람이 목록에서
   * 사라지고 「신청」 줄로만 나온다 — 판에 앉힐 수 있는 사람이 화면에서
   * 없어지는 셈이다. 거르기는 **여기서**(서버에 안 묻고) 한다.
   */
  const q = query.trim()
  const visibleContacts = (contacts ?? []).filter((c) => !q || c.nickname.includes(q))
  /** 이미 지인인 사람은 검색 결과에 또 내지 않는다 — 위 줄에 이미 있다. */
  const contactIds = new Set((contacts ?? []).map((c) => c.user_id))
  const searchRows = (found ?? []).filter((f) => !contactIds.has(f.id))

  return (
    <aside
      className="ss-suggest ss-friends"
      data-state={closing ? 'closing' : 'open'}
      aria-label="지인 찾기"
      // 🔴 backdrop-filter 는 **인라인으로** 준다(추천 판과 같은 이유) —
      // globals.css 에 두면 Lightning CSS 를 지나며 떨어져 나간 전례가 있다.
      style={{
        backdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
        WebkitBackdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
      }}
    >
      <header className="ss-suggest-head">
        <h3>지인 찾기</h3>
        <button
          type="button"
          aria-label="지인 찾기 닫기"
          className="ss-suggest-close material-symbols-outlined"
          onClick={onClose}
        >
          close
        </button>
      </header>

      {/* 🔴 라벨을 htmlFor + id 로 **명시적으로** 잇는다. 암묵적 <label> 래핑은
          안쪽에 버튼이 생기는 순간 접근성 이름이 섞인다(Field.tsx 에서 겪었다). */}
      <label htmlFor={inputId} className="sr-only">
        지인 닉네임
      </label>
      <input
        id={inputId}
        type="search"
        className="ss-friends-search"
        placeholder="닉네임으로 찾기"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoComplete="off"
      />

      {/* 고른 사람이 있으면 다음에 할 일을 적어 준다 — 왼쪽 판의 빈 자리가
          깜빡이지만, 무엇을 하라는 건지는 글로도 있어야 한다. */}
      {placing && (
        <p className="ss-friends-hint" role="status">
          <b>{placing}</b> 를 넣을 <b>빈 자리</b>를 누르세요
        </p>
      )}

      {error && (
        <p className="ss-friends-hint" role="alert">
          {error}
        </p>
      )}

      <ul className="ss-friends-list">
        {/* 받은 신청 — 수락해야 지인이 된다. 맨 위에 둔다(내가 할 일이다). */}
        {requests.map((r, i) => (
          <li key={r.id} style={{ '--ss-i': i } as React.CSSProperties}>
            <div className="ss-friends-row" data-kind="request">
              <span className="ss-friends-text">
                <span className="ss-friends-name">지인 신청이 왔습니다</span>
                <span className="ss-friends-note">{r.note ?? '수락하면 서로 지인이 됩니다'}</span>
              </span>
              <button type="button" className="ss-friends-act" onClick={() => void accept(r.id)}>
                수락
              </button>
            </div>
          </li>
        ))}

        {/* 내 지인 — 판에 앉힐 수 있는 사람은 여기뿐이다. */}
        {visibleContacts.map((c, i) => (
            <li key={c.contact_id} style={{ '--ss-i': requests.length + i } as React.CSSProperties}>
              <button
                type="button"
                className="ss-friends-row"
                data-chosen={placing === c.nickname ? 'true' : undefined}
                data-placed={placed[c.nickname] ? 'true' : undefined}
                disabled={Boolean(placed[c.nickname])}
                aria-pressed={placed[c.nickname] ? undefined : placing === c.nickname}
                // 고른 사람을 한 번 더 누르면 고르기를 푼다 — 자리를 누르기
                // 전에 마음이 바뀌면 되돌릴 길이 있어야 한다.
                onClick={() =>
                  onChoose(
                    placing === c.nickname ? null : c.nickname,
                    placing === c.nickname ? null : c.card_public_slug,
                  )
                }
              >
                <span className="ss-friends-text">
                  <span className="ss-friends-name">{c.nickname}</span>
                  {/* 🔴 `note` 는 **내가 신청자일 때만** 온다(계약) — 없는 것이
                      정상이라 빈 자리로 두지 않고 관계를 적는다. */}
                  <span className="ss-friends-note">{c.note ?? '지인'}</span>
                </span>
                {placed[c.nickname] && (
                  <span className="ss-friends-in">
                    {/* 글리프 이름('check')이 그대로 읽히지 않게 숨긴다. */}
                    <span className="material-symbols-outlined" aria-hidden="true">
                      check
                    </span>
                    {placed[c.nickname]}
                    <span className="sr-only"> 자리에 있음</span>
                  </span>
                )}
              </button>
            </li>
          ))}

        {/* 검색 결과 — 아직 남이다. 누르면 앉는 게 아니라 **신청**이 나간다. */}
        {q &&
          searchRows.map((f, i) => (
            <li
              key={f.id}
              style={
                {
                  '--ss-i': requests.length + visibleContacts.length + i,
                } as React.CSSProperties
              }
            >
              <div className="ss-friends-row" data-kind="found">
                <span className="ss-friends-text">
                  <span className="ss-friends-name">{f.nickname}</span>
                  <span className="ss-friends-note">
                    {requested[f.id] ? '신청함 · 수락을 기다립니다' : '아직 지인이 아닙니다'}
                  </span>
                </span>
                <button
                  type="button"
                  className="ss-friends-act"
                  disabled={Boolean(requested[f.id])}
                  onClick={() => void request(f)}
                >
                  {requested[f.id] ? '신청함' : '지인 신청'}
                </button>
              </div>
            </li>
          ))}

        {/* 빈 상태 — 검색 중인지, 아직 안 읽었는지, 정말 없는지를 가른다.
            셋을 한 문구로 뭉치면 "없다"와 "아직 모른다"가 같아 보인다. */}
        {q ? (
          // 🔴 **거른 지인이 남아 있으면 빈 상태가 아니다** — 이름을 쳐서 내
          // 지인 한 명만 남은 화면에 "찾는 지인이 없습니다"가 같이 뜨면 안 된다.
          visibleContacts.length === 0 &&
          searchRows.length === 0 &&
          (searching ? (
            <li className="ss-friends-empty" role="status">
              찾는 중…
            </li>
          ) : (
            <li className="ss-friends-empty" role="status">
              찾는 지인이 없습니다
            </li>
          ))
        ) : contacts === null ? (
          <li className="ss-friends-empty" role="status">
            불러오는 중…
          </li>
        ) : (
          contacts.length === 0 &&
          requests.length === 0 && (
            <li className="ss-friends-empty" role="status">
              아직 지인이 없습니다 — 닉네임으로 찾아 신청해 보세요
            </li>
          )
        )}
      </ul>
    </aside>
  )
}
