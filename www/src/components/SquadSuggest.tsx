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
import BlankPlayerCard from '@/components/BlankPlayerCard'

const SUGGESTIONS: Record<string, { name: string; title: string; notes: string[] }[]> = {
  // 자리마다 추천 수가 다르다 — 분석에서 걸러진 만큼만 온다.
  GK: [
    {
      name: '김선우',
      title: '반응이 빠른',
      notes: ['가까운 거리 슈팅 대응이 빠릅니다', '골문 앞을 넓게 씁니다'],
    },
    {
      name: '오재현',
      title: '공중볼에 강한',
      notes: ['코너와 크로스에서 먼저 나옵니다', '수비와 말을 많이 맞춥니다'],
    },
  ],
  DF: [
    {
      name: '박도현',
      title: '몸싸움이 강한',
      notes: ['1대1에서 잘 밀리지 않습니다', '세컨볼을 자주 따냅니다'],
    },
    {
      name: '이건우',
      title: '커버가 넓은',
      notes: ['뒷공간을 미리 메웁니다', '옆 수비가 나갔을 때 자리를 채웁니다'],
    },
    {
      name: '정민석',
      title: '전진 패스가 좋은',
      notes: ['수비에서 공격으로 한 번에 넘깁니다', '전환 순간에 앞을 먼저 봅니다'],
    },
    {
      name: '서준혁',
      title: '위치 선정이 좋은',
      notes: ['라인을 잘 맞춥니다', '오프사이드를 유도합니다'],
    },
  ],
  MF: [
    {
      name: '최유진',
      title: '시야가 넓은',
      notes: ['반대편 빈 공간을 자주 찾습니다', '한 박자 빠른 패스를 넣습니다'],
    },
    {
      name: '강태원',
      title: '10경기 연속',
      notes: ['활동량이 많고 꾸준합니다', '수비 가담이 성실합니다'],
    },
    {
      name: '윤서준',
      title: '탈압박이 좋은',
      notes: ['좁은 곳에서 공을 지킵니다', '몰리면 방향을 바꿔 빠져나옵니다'],
    },
  ],
  FW: [
    {
      name: '조현우',
      title: '슈팅이 매서운',
      notes: ['박스 안에서 망설이지 않습니다', '왼발과 오른발을 모두 씁니다'],
    },
    {
      name: '임재민',
      title: '침투가 날카로운',
      notes: ['뒷공간으로 먼저 달립니다', '수비 사이를 파고듭니다'],
    },
    {
      name: '신동현',
      title: '결정력이 좋은',
      notes: ['적은 기회에서 마무리합니다', '몸을 등지고 받아 돌아섭니다'],
    },
    {
      name: '문태호',
      title: '연계가 좋은',
      notes: ['등지고 받아 내주는 데 능합니다', '2대1을 잘 만듭니다'],
    },
    {
      name: '배준영',
      title: '스피드가 빠른',
      notes: ['측면에서 한 번에 제칩니다', '역습 때 가장 먼저 달립니다'],
    },
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
      // 🔴 backdrop-filter 는 **인라인으로** 준다. globals.css 에 두면 같은
      // 규칙의 color-mix() 때문에 Lightning CSS 가 통째로 떨어뜨린다(계산값
      // none) — 이 판에서 실제로 그렇게 날아갔었다.
      //
      // 스쿼드 판은 굴절(warp)만 걸지만 여기는 **흐림**이다. 굴절은 대비를
      // 하나도 낮추지 못해서, 뒤 연기가 또렷한 채로 글자 사이를 지나간다.
      // 어두운 막(globals.css)이 밝기를 눌러 주고 흐림이 무늬를 지운다 —
      // 둘 다 있어야 어느 배경 위에서든 읽힌다.
      style={{
        backdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
        WebkitBackdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
      }}
    >
      <header className="ss-suggest-head">
        {/* 한 줄로 가운데에 — 무슨 자리에 몇 명이 왔는지가 곧 제목이다. */}
        <h3>
          AI 추천 {position} {list.length}명
        </h3>
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
        {list.map((s, i) => (
          /* 차례로 들어온다 — 판만 통째로 나타나면 툭 튀어나온 느낌이다.
             순번은 CSS 가 지연으로 쓴다(--ss-i). */
          <li key={s.name} style={{ '--ss-i': i } as React.CSSProperties}>
            <button type="button" className="ss-suggest-item" onClick={() => onPick(s.name)}>
              {/* 카드가 될 자리를 알려 주는 표식 — 빈 선수 카드를 그대로
                  줄여 놓는다(스쿼드 판의 빈 자리와 같은 틀). **`+` 는 넣지
                  않는다** — 누르는 곳은 이 줄 전체지 카드가 아니다.
                  ⚠️ `.ss-pcard-mini` 는 카드를 **직접 자식**으로 찾으므로
                  (`> .ss-pcard`) 사이에 다른 요소를 끼우면 축소가 풀린다. */}
              <span className="ss-suggest-card ss-pcard-mini" aria-hidden="true">
                <BlankPlayerCard />
              </span>
              <span className="ss-suggest-text">
                <span className="ss-suggest-name">{s.name}</span>
                <span className="ss-suggest-title">{s.title}</span>
                {/* 영상 분석이 정리한 특징 — 수치가 아니라 말로 적는다
                    (카드에 수치를 그리지 않는 규칙과 같은 이유). */}
                <span className="ss-suggest-notes">
                  {s.notes.map((n) => (
                    <span key={n}>{n}</span>
                  ))}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
