'use client'

/**
 * 스쿼드 판 오른쪽에서 나오는 추천 판 — 빈 자리를 누르면 그 포지션에
 * 맞는 선수를 골라 준다.
 *
 * ⚠️ **추천 목록은 아직 붙박이다.** 계약(api-contract.md)에 추천
 * 엔드포인트가 없다 — 영상 분석 파이프라인이 붙어야 나오는 값이다.
 * 화면 모양을 먼저 잡아 두는 자리 표시이고, API 가 생기면 이 상수를
 * 지우고 그 응답을 그대로 흘려 넣으면 된다(카드 목록의 모양은 그대로다).
 * 선수 카드의 별명(ALIAS)을 붙박이로 둔 것과 같은 이유 · 같은 방식이다.
 */
const SUGGESTIONS: Record<string, { name: string; title: string }[]> = {
  GK: [
    { name: '김선우', title: '반응이 빠른' },
    { name: '오재현', title: '공중볼에 강한' },
    { name: '한지수', title: '발밑이 좋은' },
  ],
  DF: [
    { name: '박도현', title: '몸싸움이 강한' },
    { name: '이건우', title: '커버가 넓은' },
    { name: '정민석', title: '전진 패스가 좋은' },
  ],
  MF: [
    { name: '최유진', title: '시야가 넓은' },
    { name: '강태원', title: '10경기 연속' },
    { name: '윤서준', title: '탈압박이 좋은' },
  ],
  FW: [
    { name: '조현우', title: '슈팅이 매서운' },
    { name: '임재민', title: '침투가 날카로운' },
    { name: '신동현', title: '결정력이 좋은' },
  ],
}

export default function SquadSuggest({
  position,
  closing,
  onPick,
  onClose,
}: {
  /** 지금 채우려는 자리(GK · DF · MF · FW). */
  position: string
  /** 닫히는 중 — 사라지는 동안에도 DOM 에 남아 있어야 애니메이션이 보인다. */
  closing: boolean
  onPick: (name: string) => void
  onClose: () => void
}) {
  const list = SUGGESTIONS[position] ?? []

  return (
    <aside
      className="ss-suggest"
      data-state={closing ? 'closing' : 'open'}
      aria-label={`${position} 추천 선수`}
    >
      <header className="ss-suggest-head">
        <div>
          <p className="ss-suggest-kicker">AI 추천</p>
          <h3>{position} 자리</h3>
        </div>
        <button
          type="button"
          aria-label="추천 닫기"
          className="ss-suggest-close material-symbols-outlined"
          onClick={onClose}
        >
          close
        </button>
      </header>

      <ul className="ss-suggest-list">
        {list.map((s) => (
          <li key={s.name}>
            <button type="button" className="ss-suggest-item" onClick={() => onPick(s.name)}>
              {/* 카드가 될 자리를 알려 주는 표식. 워드마크를 넣어 봤지만
                  이 크기(30px)에서는 읽히지도 않고 글자 위로 넘쳤다. */}
              <span className="ss-suggest-card" aria-hidden="true" />
              <span className="ss-suggest-text">
                <span className="ss-suggest-name">{s.name}</span>
                <span className="ss-suggest-title">{s.title}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
