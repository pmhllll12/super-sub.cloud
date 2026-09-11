'use client'

import { useState } from 'react'
import {
  ANY_GRADE,
  GRADES,
  averageGrade,
  type Grade,
  type GradeFilter,
} from '@/lib/playerGrade'

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

/**
 * 🔴 `clip` 은 **그 사람의 대표 장면**이다(사용자 요청) — 빈 카드 대신 이것이
 * 보인다. 말로 적은 특징 옆에 우리가 분석한 장면이 같이 있어야 "AI 가
 * 골랐다"가 화면에서 성립한다(코치 목록이 같은 이유로 그렇게 되어 있다).
 * ⚠️ 지금은 저장소에 있는 클립 셋(`/coach-c00N.mp4`)을 **돌려 쓰는 자리
 * 표시**다 — 계약에 영상 조회가 없어서다(5장 ASM-003, 객체 저장소 미정).
 * `lib/feed.ts` 가 같은 파일을 같은 이유로 돌려 쓴다. 🔴 **영상 파일을 더
 * 넣지 말 것** — 저장소가 무거워진다(셋이 이미 16MB). 사람이 늘면 객체
 * 저장소 이야기를 먼저 꺼낸다.
 */
/**
 * 🔴 `grade` 는 **mock 이다**(2026-09-11). 남의 등급을 읽을 경로가 계약에
 * 없다 — `GET /videos/{id}/report` 는 자기 영상만이고, 남의 것은 404 다.
 * 눈금과 「어떻게 정해지는가」는 `lib/playerGrade.ts` 에 적어 두었다.
 *
 * ⚠️ **S 와 F 를 일부러 섞어 두었다.** 서버는 지금 A~D 넷만 내므로, 그 둘이
 * 없으면 거르개의 두 칸이 개발 중에 한 번도 안 눌린다 — 팀 매칭 mock 이
 * 5:5 만 채워 뒀다가 7:7 로 바꾼 사람에게 빈 화면을 보인 것과 같은 함정이다.
 */
const SUGGESTIONS: Record<
  string,
  { name: string; title: string; notes: string[]; clip: string; grade: Grade }[]
> = {
  // 자리마다 추천 수가 다르다 — 분석에서 걸러진 만큼만 온다.
  GK: [
    {
      name: '김선우',
      grade: 'A',
      clip: '/coach-c001.mp4',
      title: '반응이 빠른',
      notes: ['가까운 거리 슈팅 대응이 빠릅니다', '골문 앞을 넓게 씁니다'],
    },
    {
      name: '오재현',
      grade: 'C',
      clip: '/coach-c002.mp4',
      title: '공중볼에 강한',
      notes: ['코너와 크로스에서 먼저 나옵니다', '수비와 말을 많이 맞춥니다'],
    },
  ],
  DF: [
    {
      name: '박도현',
      grade: 'S',
      clip: '/coach-c003.mp4',
      title: '몸싸움이 강한',
      notes: ['1대1에서 잘 밀리지 않습니다', '세컨볼을 자주 따냅니다'],
    },
    {
      name: '이건우',
      grade: 'B',
      clip: '/coach-c001.mp4',
      title: '커버가 넓은',
      notes: ['뒷공간을 미리 메웁니다', '옆 수비가 나갔을 때 자리를 채웁니다'],
    },
    {
      name: '정민석',
      grade: 'C',
      clip: '/coach-c002.mp4',
      title: '전진 패스가 좋은',
      notes: ['수비에서 공격으로 한 번에 넘깁니다', '전환 순간에 앞을 먼저 봅니다'],
    },
    {
      name: '서준혁',
      grade: 'D',
      clip: '/coach-c003.mp4',
      title: '위치 선정이 좋은',
      notes: ['라인을 잘 맞춥니다', '오프사이드를 유도합니다'],
    },
  ],
  MF: [
    {
      name: '최유진',
      grade: 'A',
      clip: '/coach-c001.mp4',
      title: '시야가 넓은',
      notes: ['반대편 빈 공간을 자주 찾습니다', '한 박자 빠른 패스를 넣습니다'],
    },
    {
      name: '강태원',
      grade: 'B',
      clip: '/coach-c002.mp4',
      title: '10경기 연속',
      notes: ['활동량이 많고 꾸준합니다', '수비 가담이 성실합니다'],
    },
    {
      name: '윤서준',
      grade: 'C',
      clip: '/coach-c003.mp4',
      title: '탈압박이 좋은',
      notes: ['좁은 곳에서 공을 지킵니다', '몰리면 방향을 바꿔 빠져나옵니다'],
    },
  ],
  FW: [
    {
      name: '조현우',
      grade: 'F',
      clip: '/coach-c001.mp4',
      title: '슈팅이 매서운',
      notes: ['박스 안에서 망설이지 않습니다', '왼발과 오른발을 모두 씁니다'],
    },
    {
      name: '임재민',
      grade: 'A',
      clip: '/coach-c002.mp4',
      title: '침투가 날카로운',
      notes: ['뒷공간으로 먼저 달립니다', '수비 사이를 파고듭니다'],
    },
    {
      name: '신동현',
      grade: 'B',
      clip: '/coach-c003.mp4',
      title: '결정력이 좋은',
      notes: ['적은 기회에서 마무리합니다', '몸을 등지고 받아 돌아섭니다'],
    },
    {
      name: '문태호',
      grade: 'C',
      clip: '/coach-c001.mp4',
      title: '연계가 좋은',
      notes: ['등지고 받아 내주는 데 능합니다', '2대1을 잘 만듭니다'],
    },
    {
      name: '배준영',
      grade: 'A',
      clip: '/coach-c002.mp4',
      title: '스피드가 빠른',
      notes: ['측면에서 한 번에 제칩니다', '역습 때 가장 먼저 달립니다'],
    },
  ],
}

/**
 * 이름으로 등급을 되짚는다 — 판에 앉은 사람의 등급을 알아내는 유일한 길이다.
 *
 * 🔴 **mock 을 뒤지는 함수다.** 서버가 남의 등급을 주기 시작하면 이 함수째
 * 지우고 그 값을 쓰면 된다 — 부르는 쪽(`SquadPanel`)은 안 고쳐도 된다.
 * ⚠️ 모르면 `null` 이다. 0(F)으로 치면 아직 분석을 안 한 사람이 팀 평균을
 * 끌어내린다(`averageGrade` 가 그래서 `null` 을 빼고 센다).
 */
export function gradeOfPlayer(name: string): Grade | null {
  for (const list of Object.values(SUGGESTIONS)) {
    const hit = list.find((s) => s.name === name)
    if (hit) return hit.grade
  }
  return null
}

export default function SquadSuggest({
  position,
  closing,
  me,
  seated = [],
  onPick,
  onClose,
}: {
  /** 지금 채우려는 자리의 포지션 코드 — 목록의 정본은 `GET /positions` 다. */
  position: string
  /**
   * 나 자신 — 후보 목록에 내가 있으면 **내가 고른 대표 영상**을 쓴다
   * (사용자 요청, 2026-09-08). 사람마다 자기 `/me` 에서 한 편을 고르고,
   * 이 판이 그 사람의 그 장면을 튼다는 뜻이다.
   *
   * ⚠️ **남의 것은 아직 못 읽는다** — 계약에 「대표」 표시도, 남의 영상을
   * 읽을 경로도 없다(미결). 그래서 지금 실제로 갈리는 것은 내 것뿐이고,
   * 나머지는 저장소의 자리 표시 클립 그대로다.
   */
  me?: { nickname: string; clip: string | null } | null
  /**
   * 이미 판에 앉은 사람들의 등급 — **거르개의 첫 값을 정하는 데만** 쓴다
   * (사용자 요청: 넷이 찼고 하나를 더 구할 때 그 넷의 평균과 비슷한 등급을
   * 보여 준다). 등급을 모르는 사람은 `null` 로 넘긴다 — `averageGrade` 가
   * 셈에서 뺀다.
   *
   * 🔴 **나중에 RAG 가 할 일의 자리다.** 지금은 등급 하나로만 좁히지만,
   * 「비슷하다」의 기준은 서버가 정해야 한다(미결).
   */
  seated?: (Grade | null)[]
  /** 닫히는 중 — 사라지는 동안에도 DOM 에 남아 있어야 애니메이션이 보인다. */
  closing: boolean
  onPick: (name: string) => void
  onClose: () => void
}) {
  const all = SUGGESTIONS[position] ?? []

  /* 🔴 **첫 값은 팀 평균이다**(사용자 요청). 아무도 등급이 없으면 「상관없음」
     으로 연다 — 모르는 것을 기준으로 좁히면 빈 화면만 남는다. */
  const [grade, setGrade] = useState<GradeFilter>(() => averageGrade(seated) ?? ANY_GRADE)

  /* ⚠️ **안 맞는 사람을 목록에서 뺀다.** 팀 매칭의 「비슷한 팀」과 반대
     판단인데, 거기는 사람이 적어 놓은 조건이라 조금 틀렸을 수 있었고
     여기는 **사람이 방금 누른 값**이라 뜻이 분명하다. */
  const list = grade === ANY_GRADE ? all : all.filter((s) => s.grade === grade)

  /** 이 후보가 틀 장면 — 나라면 내가 고른 것, 아니면 자리 표시. */
  const clipFor = (name: string, fallback: string) =>
    me && me.clip && name === me.nickname ? me.clip : fallback

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

      {/* 🔴 **등급으로 좁히는 줄**(사용자 요청). 첫 값은 판에 앉은 사람들의
          평균이고, 「상관없음」까지 있어 되돌릴 길이 늘 있다.

          ⚠️ **지금은 화면 안에서만 거른다.** 진짜로는 서버가 「비슷하다」를
          판단해야 한다(RAG) — 여기서 거르는 것은 그때까지의 자리 표시다. */}
      <div className="ss-suggest-grades" role="group" aria-label="등급으로 좁히기">
        {[...GRADES, ANY_GRADE].map((g) => (
          <button
            key={g}
            type="button"
            className="ss-suggest-grade-pill"
            data-on={grade === g}
            aria-pressed={grade === g}
            onClick={() => setGrade(g)}
          >
            {g === ANY_GRADE ? '등급 상관없음' : g}
          </button>
        ))}
      </div>

      {/* 🔴 **빈 목록을 말없이 두지 않는다.** 좁혀서 아무도 안 남은 것과
          그 자리에 원래 후보가 없는 것은 다르다 — 뒤엣것이면 등급을 바꿔도
          소용없다는 뜻이라, 사람이 알아야 할 정보가 갈린다. */}
      {list.length === 0 && (
        <p className="ss-suggest-empty" role="status">
          {all.length === 0
            ? '이 자리에 맞는 추천이 아직 없습니다.'
            : '이 등급에 맞는 사람이 없습니다 — 등급을 넓혀 보세요.'}
        </p>
      )}

      <ul className="ss-suggest-list">
        {list.map((s, i) => (
          /* 차례로 들어온다 — 판만 통째로 나타나면 툭 튀어나온 느낌이다.
             순번은 CSS 가 지연으로 쓴다(--ss-i). */
          <li
            key={s.name}
            style={{ '--ss-i': i } as React.CSSProperties}
            // 🔴 **가져다 대면 돈다**(사용자 요청). 판이 나올 때는 멈춰 있다
            //    — `autoPlay` 를 안 주는 것이 그 뜻이다. 훑어보는 동안 장면이
            //    도는 것은 고르기 전의 일이라, 누르는 것(고르기)과 갈라 둔다.
            // 🔴 과녁을 단추가 아니라 **줄(li)** 로 잡는다 — 단추에 걸면 영상
            //    위로 마우스가 넘어갈 때 나갔다 들어온 것으로 잡혀 재생이 한 번
            //    끊긴다(코치 목록에서 겪은 것과 같다).
            // 🔴 `play()` 는 약속을 돌려주고 **거절될 수 있다**(아직 못 읽었거나
            //    바로 떠났거나). 안 받으면 콘솔에 잡히지 않은 오류가 쌓인다.
            onMouseEnter={(e) => {
              e.currentTarget.querySelector('video')?.play().catch(() => {})
            }}
            onMouseLeave={(e) => {
              const v = e.currentTarget.querySelector('video')
              if (!v) return
              v.pause()
              // 처음으로 되돌린다 — 다음에 가져다 댔을 때 늘 같은 자리에서
              // 시작해야 "이 사람의 대표 장면"으로 읽힌다.
              v.currentTime = 0
            }}
          >
            <button type="button" className="ss-suggest-item" onClick={() => onPick(s.name)}>
              {/* 🔴 빈 선수 카드가 있던 자리다 — **그 사람의 대표 장면**으로
                  바꿨다(사용자 요청). 카드는 아직 없는 것을 그리는 표식이었고,
                  장면은 실제로 보여 줄 것이 있다.

                  🔴 **틀에 맞춰 자르지 않는다**(사용자 요청) — 세로 틀에 영상
                  전체를 넣고 남는 곳은 검게 둔다(`object-fit: contain`, 바탕은
                  globals.css). 클립마다 비율이 달라서(세로 1080×1920 · 가로
                  1280×720) 채우려면 어느 쪽이든 사람이 잘린다. */}
              <span className="ss-suggest-card" aria-hidden="true">
                <video
                  // 🔴 주소 뒤의 `#t=0.1` 은 "0.1초 자리를 보여 달라"는 뜻이다.
                  //    이게 없으면 브라우저가 `preload="metadata"` 만 보고 **그림은
                  //    안 그려서** 멈춰 있는 동안 칸이 검게만 남는다(코치 목록에서
                  //    같은 것을 겪었다). 0 이 아니라 0.1 인 것은 맨 첫 칸이 검은
                  //    영상이 흔해서다.
                  src={`${clipFor(s.name, s.clip)}#t=0.1`}
                  // 🔴 `autoPlay` 를 주지 않는다 — 판이 나올 때는 멈춰 있어야 한다.
                  //    🔴 `muted` 없이는 브라우저가 재생을 막고, `playsInline` 이
                  //    없으면 iOS 가 전체 화면으로 띄운다.
                  muted
                  loop
                  playsInline
                  preload="metadata"
                />
              </span>
              <span className="ss-suggest-text">
                {/* 🔴 이름과 등급을 **한 줄에** 둔다(사용자 요청) — 등급을
                    따로 떼면 누구의 등급인지 한 번 더 짚어야 한다. */}
                <span className="ss-suggest-nameline">
                  <span className="ss-suggest-name">{s.name}</span>
                  <span className="ss-suggest-grade" data-grade={s.grade}>
                    {s.grade}
                  </span>
                </span>
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
