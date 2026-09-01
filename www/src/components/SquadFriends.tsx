'use client'

import { useId, useMemo, useState } from 'react'

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
 * ⚠️ **목록은 아직 붙박이다.** 계약(api-contract.md)에 지인·친구
 * 엔드포인트가 없다. 화면 모양을 먼저 잡아 두는 자리 표시이고, API 가
 * 생기면 이 상수를 지우고 그 응답을 그대로 흘려 넣으면 된다(행의 모양은
 * 그대로다). AI 추천 목록 · 카드 별명을 붙박이로 둔 것과 같은 방식이다.
 */
const FRIENDS = [
  { nickname: '홍길동', note: '같은 동네 · 수요일 저녁' },
  { nickname: '김철수', note: '지난 시즌 같은 팀' },
  { nickname: '이영희', note: '풋살 모임에서 만남' },
  { nickname: '박준호', note: '회사 동호회' },
  { nickname: '최민서', note: '같은 동네' },
  { nickname: '정하늘', note: '주말 경기 자주 뜀' },
  { nickname: '강도윤', note: '지난 시즌 같은 팀' },
  { nickname: '윤가온', note: '학교 후배' },
]

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
  onChoose: (nickname: string | null) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const inputId = useId()

  // 공백만 친 경우까지 걸러 전부 보여준다 — 빈 목록보다 전체가 낫다.
  const list = useMemo(() => {
    const q = query.trim()
    if (!q) return FRIENDS
    return FRIENDS.filter((f) => f.nickname.includes(q))
  }, [query])

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

      <ul className="ss-friends-list">
        {list.map((f, i) => (
          <li key={f.nickname} style={{ '--ss-i': i } as React.CSSProperties}>
            <button
              type="button"
              className="ss-friends-row"
              data-chosen={placing === f.nickname ? 'true' : undefined}
              data-placed={placed[f.nickname] ? 'true' : undefined}
              disabled={Boolean(placed[f.nickname])}
              aria-pressed={placed[f.nickname] ? undefined : placing === f.nickname}
              // 고른 사람을 한 번 더 누르면 고르기를 푼다 — 자리를 누르기
              // 전에 마음이 바뀌면 되돌릴 길이 있어야 한다.
              onClick={() => onChoose(placing === f.nickname ? null : f.nickname)}
            >
              <span className="ss-friends-text">
                <span className="ss-friends-name">{f.nickname}</span>
                <span className="ss-friends-note">{f.note}</span>
              </span>
              {placed[f.nickname] && (
                <span className="ss-friends-in">
                  {/* 글리프 이름('check')이 그대로 읽히지 않게 숨긴다. */}
                  <span className="material-symbols-outlined" aria-hidden="true">
                    check
                  </span>
                  {placed[f.nickname]}
                  <span className="sr-only"> 자리에 있음</span>
                </span>
              )}
            </button>
          </li>
        ))}
        {list.length === 0 && (
          <li className="ss-friends-empty" role="status">
            찾는 지인이 없습니다
          </li>
        )}
      </ul>
    </aside>
  )
}
