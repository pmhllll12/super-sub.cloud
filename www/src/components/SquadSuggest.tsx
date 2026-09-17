'use client'

import { useEffect, useState } from 'react'
import { ANY_GRADE, GRADES, type GradeFilter } from '@/lib/playerGrade'

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
 * 사람마다 붙는 **말로 적은 특징과 대표 장면** — 아직 mock 이다.
 *
 * 🔴 **이름과 등급은 2026-09-16 에 진짜가 됐다**(계약 3-16절, CCC 44번).
 * 걷어낸 것은 「누가 추천되는가」와 「그 사람 등급이 얼마인가」 둘이고, 계약
 * 44번이 남은 범위를 그대로 그어 두었다:
 *
 * > `clip`·`title`·`notes` 는 이 응답에 없습니다 — 그건 별도 범위입니다.
 * > 지금은 mock 클립·문구를 그대로 쓰고, **이름·등급만** 이 응답으로 바꿔
 * > 주십시오.
 *
 * 그래서 이 표는 **닉네임으로 찾는 장식**이다. 서버가 준 후보의 닉네임이 여기
 * 없으면 문구 없이 이름과 등급만 그린다 — 지어내지 않는다.
 *
 * 🔴 **정정 (2026-09-17, 사용자 판단 — 미결 `ho` 50번).** 여기 있던 **불릿
 * 두 줄(`notes`)을 걷어냈다.** 「1대1에서 잘 밀리지 않습니다」·「수비 가담이
 * 성실합니다」 같은 문장은 **경기 행동**이라 저희가 **재는 것이 아무것도
 * 없다**(정상호: 「아무 데도 없습니다 — 한 편의 자세 분석으로는 못 잽니다」).
 *
 * 🔴 그런데 이 표는 **닉네임으로** 붙는다 — 후보가 진짜 사용자가 된 지금,
 * 실제로 「김선우」인 사람이 있으면 **지어낸 문장이 그 사람의 진짜 이름·진짜
 * 등급 옆에** 걸린다. 2026-09-11 에 대표 영상을 `?? '/coach-c001.mp4'` 로
 * 떨어뜨리다 똑같이 데인 자리다.
 *
 * 🔴 **그리고 같은 날 진짜가 왔다**(CCC 56, 미결 `paik` 33·38번). 후보 목록
 * 응답에 `notes` 가 실려 온다 — **후보마다 `/grade` 를 다시 부르지 않는다.**
 * 그래서 이 표에 남은 것은 **대표 영상 폴백(`clip`)과 호칭 폴백(`title`)뿐**
 * 이고, 불릿은 서버 값만 쓴다.
 *
 * ⚠️ 클립은 저장소의 셋(`/coach-c00N.mp4`)을 돌려 쓴다. 🔴 **영상 파일을 더
 * 넣지 말 것** — 셋이 이미 16MB 다.
 */
const FLAVOR: Record<string, { clip: string; title: string }> = {
  '김선우': {
    clip: '/coach-c001.mp4',
    title: '반응이 빠른',
  },
  '오재현': {
    clip: '/coach-c002.mp4',
    title: '공중볼에 강한',
  },
  '박도현': {
    clip: '/coach-c003.mp4',
    title: '몸싸움이 강한',
  },
  '이건우': {
    clip: '/coach-c001.mp4',
    title: '커버가 넓은',
  },
  '정민석': {
    clip: '/coach-c002.mp4',
    title: '전진 패스가 좋은',
  },
  '서준혁': {
    clip: '/coach-c003.mp4',
    title: '위치 선정이 좋은',
  },
  '최유진': {
    clip: '/coach-c001.mp4',
    title: '시야가 넓은',
  },
  '강태원': {
    clip: '/coach-c002.mp4',
    title: '10경기 연속',
  },
  '윤서준': {
    clip: '/coach-c003.mp4',
    title: '탈압박이 좋은',
  },
  '조현우': {
    clip: '/coach-c001.mp4',
    title: '슈팅이 매서운',
  },
  '임재민': {
    clip: '/coach-c002.mp4',
    title: '침투가 날카로운',
  },
  '신동현': {
    clip: '/coach-c003.mp4',
    title: '결정력이 좋은',
  },
  '문태호': {
    clip: '/coach-c001.mp4',
    title: '연계가 좋은',
  },
  '배준영': {
    clip: '/coach-c002.mp4',
    title: '스피드가 빠른',
  },
}

/** 후보 한 줄 — 서버가 주는 것(계약 3-16절)에 위 장식을 얹은 모양. */
type Candidate = {
  user_id: string
  nickname: string
  card_public_slug: string | null
  grade: string | null
  provisional: boolean | null
  /** 분석이 낸 불릿 한두 줄 (CCC 56). 🔴 한 줄·`null` 둘 다 정상이다. */
  notes?: string[] | null
}

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; list: Candidate[] }
  | { kind: 'error'; message: string }

export default function SquadSuggest({
  position,
  closing,
  me,
  teamId,
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
   * ⚠️ **남의 것은 아직 이 판에 안 붙였다** — 후보 응답의 `card_public_slug`
   * 로 `GET /cards/{slug}/featured-video` 를 부르면 되지만, 계약 44번이
   * 「지금은 mock 클립을 그대로」로 범위를 그어서 그 줄은 남겨 두었다.
   */
  me?: { nickname: string; clip: string | null } | null
  /**
   * 내 팀 id — 후보는 이 팀 밑에서 찾는다(계약 3-16절). `null` 이면 아직 못
   * 읽었거나 팀이 없다 — 그때는 「후보가 없다」가 아니라 **못 물어본 것**이라
   * 그렇게 적는다.
   */
  teamId?: string | null
  /** 닫히는 중 — 사라지는 동안에도 DOM 에 남아 있어야 애니메이션이 보인다. */
  closing: boolean
  /**
   * 고른 사람 — **슬러그도 같이 넘긴다**(2026-09-17). 이름만 넘기면 판이 그
   * 사람의 **진짜 카드를 못 그린다**(빈 카드에 이름만 찍힌다). 카드를 아직 안
   * 만든 사람은 `null` 이고, 그때는 이름표로 남는 것이 맞다.
   */
  onPick: (name: string, cardSlug: string | null, userId: string) => void
  onClose: () => void
}) {
  /* 🔴 **첫 값은 「상관없음」이다**(2026-09-16에 바뀜). 전에는 판에 앉은
     사람들의 평균을 화면에서 계산해 첫 값으로 썼는데, 이제 **서버가 그 평균과
     가까운 순으로 정렬해서** 준다 — 화면이 다시 계산하면 두 곳이 갈린다
     (계약 44번의 「하지 말 것」). */
  const [grade, setGrade] = useState<GradeFilter>(ANY_GRADE)
  const [state, setState] = useState<State>({ kind: 'loading' })
  /**
   * 후보의 **대표 영상 주소** — `user_id` → 재생 URL (계약 3-6절).
   *
   * 🔴 **후보 응답에는 영상이 없다.** `card_public_slug` 로 한 사람씩 따로
   * 물어야 한다 — 그래서 목록이 먼저 뜨고 영상이 나중에 채워진다(빈 칸이
   * 잠깐 보이는 것이 정상이다).
   *
   * ⚠️ 이 주소는 **사전 서명 URL 이라 만료된다**(`expires_in`, 보통 15분).
   * 판을 여는 동안만 쓰고 어디에도 오래 담아 두지 않는다.
   */
  const [clips, setClips] = useState<Record<string, string>>({})
  /**
   * 후보가 **직접 적은 호칭** — `user_id` → 첫 호칭 (미결 `paik` 36번).
   *
   * 🔴 후보 응답에 없어서 `card_public_slug` 로 따로 읽는다(대표 영상과 같다).
   * 카드의 `titles[0].label` 이다 — 사람이 적은 글이라 **지어내지 않는다**.
   */
  const [titles, setTitles] = useState<Record<string, string>>({})

  /* 🔴 **거르개를 서버에 넘긴다.** 화면에서 거르면 「이 등급에 몇 명인가」가
     받아 온 페이지 안에서만 맞는 값이 된다 — 계약이 하드 필터를 서버에 두었다. */
  useEffect(() => {
    if (!teamId) {
      // 물어볼 곳이 없다 — 「후보가 없다」와 갈라 적는다. 규칙은 effect 안의
      // 동기 setState 를 싫어하지만, 여기는 부를 것이 아예 없는 갈래다.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState({ kind: 'error', message: '팀을 먼저 만들어야 후보를 찾습니다.' })
      return
    }
    let alive = true
    setState({ kind: 'loading' })
    void (async () => {
      try {
        const q = new URLSearchParams({ position_code: position })
        if (grade !== ANY_GRADE) q.set('grade', grade)
        const res = await fetch(
          `/api/teams/${encodeURIComponent(teamId)}/squad/candidates?${q}`,
        )
        const body: unknown = await res.json().catch(() => null)
        if (!alive) return
        if (!res.ok) {
          const msg =
            typeof body === 'object' && body !== null && 'error' in body
              ? ((body as { error?: { message?: string } }).error?.message ?? null)
              : null
          setState({ kind: 'error', message: msg ?? '후보를 가져오지 못했습니다.' })
          return
        }
        setState({ kind: 'ok', list: Array.isArray(body) ? (body as Candidate[]) : [] })
      } catch {
        if (alive) setState({ kind: 'error', message: '후보를 가져오지 못했습니다.' })
      }
    })()
    return () => {
      alive = false
    }
  }, [teamId, position, grade])

  const list = state.kind === 'ok' ? state.list : []

  /* 🔴 **목록을 기다렸다가 영상을 받는다.** 후보마다 요청이 하나씩 더 나가지만
     (계약이 목록에 영상을 안 실었다), 목록을 그것 때문에 늦추지는 않는다 —
     이름과 등급이 먼저 서고 영상이 뒤따라 채워진다. */
  useEffect(() => {
    if (state.kind !== 'ok') return
    const withCard = state.list.filter((c) => c.card_public_slug)
    if (withCard.length === 0) return
    let alive = true
    void (async () => {
      const found = await Promise.all(
        withCard.map(async (c) => {
          try {
            const res = await fetch(
              `/api/cards/${encodeURIComponent(c.card_public_slug as string)}/featured-video`,
            )
            // 🔴 **404 는 오류가 아니다** — 대표 영상을 아직 안 고른 사람이다
            //    (계약 3-6절 `NO_FEATURED_VIDEO`). 조용히 넘긴다.
            if (!res.ok) return null
            const body = (await res.json().catch(() => null)) as { url?: string } | null
            return body?.url ? ([c.user_id, body.url] as const) : null
          } catch {
            return null
          }
        }),
      )
      if (!alive) return
      const next = Object.fromEntries(found.filter((x): x is readonly [string, string] => !!x))
      setClips(next)

      /* 🔴 **호칭도 같이 읽는다**(미결 `paik` 36번) — 후보 응답에 없어서
         카드로 한 번 더 묻는다. 대표 영상과 **따로** 부르는 이유는 둘이
         다른 경로이고(`/featured-video` · `/cards/{slug}`), 한쪽이 404 여도
         다른 쪽은 있을 수 있어서다. */
      const named = await Promise.all(
        withCard.map(async (c) => {
          try {
            const r = await fetch(`/api/cards/${encodeURIComponent(c.card_public_slug as string)}`)
            if (!r.ok) return null
            const b = (await r.json().catch(() => null)) as { titles?: { label: string }[] } | null
            const label = b?.titles?.[0]?.label?.trim()
            return label ? ([c.user_id, label] as const) : null
          } catch {
            return null
          }
        }),
      )
      if (!alive) return
      setTitles(Object.fromEntries(named.filter((x): x is readonly [string, string] => !!x)))
    })()
    return () => {
      alive = false
    }
  }, [state])

  /**
   * 이 후보가 틀 장면 — 나라면 내가 고른 것, 아니면 **아는 자리 표시만**.
   *
   * 🔴 **모르는 사람에게 아무 클립이나 붙이지 않는다.** 전에는 자리 표시
   * 하나로 떨어뜨렸는데(`?? '/coach-c001.mp4'`), 그러면 **진짜 사용자 전원**
   * 에게 남의 농구 영상이 「그 사람 대표 장면」으로 붙는다 — 이름과 등급이
   * 진짜가 된 지금은 그 옆의 가짜 영상이 진짜로 읽힌다. 없으면 없다고 한다.
   */
  const clipFor = (c: Candidate): string | null => {
    // 내가 방금 고른 것이 가장 최신이다 — 서버 값보다 앞선다.
    if (me && me.clip && c.nickname === me.nickname) return me.clip
    // 🔴 그다음이 **진짜 대표 영상**이다. `FLAVOR` 는 맨 뒤 — 그것은 화면
    //    mock 이라, 진짜가 있으면 진짜가 이겨야 한다.
    return clips[c.user_id] ?? FLAVOR[c.nickname]?.clip ?? null
  }

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

      {/* 🔴 **넷을 갈라 적는다.** 받아 오는 중 · 못 받은 것 · 좁혀서 아무도
          안 남은 것 · 그 자리에 원래 후보가 없는 것은 서로 다른 뜻이고, 사람이
          다음에 할 일이 갈린다(등급을 넓힐지, 기다릴지, 포기할지). */}
      {state.kind === 'loading' && (
        <p className="ss-suggest-empty" role="status">
          후보를 찾고 있습니다…
        </p>
      )}
      {state.kind === 'error' && (
        <p className="ss-suggest-empty" role="alert">
          {state.message}
        </p>
      )}
      {state.kind === 'ok' && list.length === 0 && (
        <p className="ss-suggest-empty" role="status">
          {grade === ANY_GRADE
            ? '이 자리에 맞는 추천이 아직 없습니다.'
            : '이 등급에 맞는 사람이 없습니다 — 등급을 넓혀 보세요.'}
        </p>
      )}

      <ul className="ss-suggest-list">
        {list.map((s, i) => (
          /* 차례로 들어온다 — 판만 통째로 나타나면 툭 튀어나온 느낌이다.
             순번은 CSS 가 지연으로 쓴다(--ss-i). */
          <li
            key={s.user_id}
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
            <button
              type="button"
              className="ss-suggest-item"
              onClick={() => onPick(s.nickname, s.card_public_slug, s.user_id)}
            >
              {/* 🔴 빈 선수 카드가 있던 자리다 — **그 사람의 대표 장면**으로
                  바꿨다(사용자 요청). 카드는 아직 없는 것을 그리는 표식이었고,
                  장면은 실제로 보여 줄 것이 있다.

                  🔴 **틀에 맞춰 자르지 않는다**(사용자 요청) — 세로 틀에 영상
                  전체를 넣고 남는 곳은 검게 둔다(`object-fit: contain`, 바탕은
                  globals.css). 클립마다 비율이 달라서(세로 1080×1920 · 가로
                  1280×720) 채우려면 어느 쪽이든 사람이 잘린다. */}
              <span className="ss-suggest-card" aria-hidden={clipFor(s) ? true : undefined}>
                {clipFor(s) === null ? (
                  /* 🔴 **없으면 없다고 적는다.** 대표 영상을 아직 안 고른
                     사람이다 — 남의 영상을 대신 틀면 그것이 이 사람 장면으로
                     읽힌다(이름·등급이 진짜라서 더 그렇다). */
                  <span className="ss-suggest-card-empty">아직 대표 영상이 없습니다</span>
                ) : (
                <video
                  // 🔴 주소 뒤의 `#t=0.1` 은 "0.1초 자리를 보여 달라"는 뜻이다.
                  //    이게 없으면 브라우저가 `preload="metadata"` 만 보고 **그림은
                  //    안 그려서** 멈춰 있는 동안 칸이 검게만 남는다(코치 목록에서
                  //    같은 것을 겪었다). 0 이 아니라 0.1 인 것은 맨 첫 칸이 검은
                  //    영상이 흔해서다.
                  src={`${clipFor(s)}#t=0.1`}
                  // 🔴 `autoPlay` 를 주지 않는다 — 판이 나올 때는 멈춰 있어야 한다.
                  //    🔴 `muted` 없이는 브라우저가 재생을 막고, `playsInline` 이
                  //    없으면 iOS 가 전체 화면으로 띄운다.
                  muted
                  loop
                  playsInline
                  preload="metadata"
                />
                )}
              </span>
              <span className="ss-suggest-text">
                {/* 🔴 이름과 등급을 **한 줄에** 둔다(사용자 요청) — 등급을
                    따로 떼면 누구의 등급인지 한 번 더 짚어야 한다. */}
                <span className="ss-suggest-nameline">
                  <span className="ss-suggest-name">{s.nickname}</span>
                  {/* 🔴 **등급을 모르면 칸을 안 그린다** — 대표 영상이 없거나
                      아직 분석 전이라는 뜻이고, `F` 로 치면 「없다」가 「낮다」가
                      된다(26번의 「하지 말 것」). */}
                  {s.grade && (
                    <span className="ss-suggest-grade" data-grade={s.grade}>
                      {s.grade}
                    </span>
                  )}
                  {/* 🔴 **검수 전 값이면 반드시 그렇게 적는다**(정상호 조건,
                      2026-09-14). 지금 루브릭은 `review_required: true` 라 남에게
                      보이는 등급이 잠정이다 — 등급 문자만 떼어 보이면 받는 쪽은
                      확정으로 읽고, 남의 화면에 박힌 등급은 회수가 안 된다. */}
                  {s.provisional && <span className="ss-suggest-provisional">검수 전</span>}
                </span>
                {/* 🔴 **그 사람이 적은 호칭이 먼저다.** `FLAVOR` 는 화면 mock
                    이라 진짜가 있으면 진짜가 이긴다(대표 영상과 같은 순서).

                    🔴 **출처 표식(「본인이 적음」)을 화면에 적지 않는다**
                    (2026-09-17, 사용자 판단). `ho` 50번이 「출처를 화면에서
                    구분해 달라」고 했지만, 제품 화면에 「본인이 적음」·「AI가
                    적음」이 붙어 있으면 **읽는 사람에게는 이상한 말**이다 —
                    카드는 선수를 소개하는 자리지 출처를 밝히는 자리가 아니다.
                    대신 **섞지 않는 것으로 가른다**: 이 줄은 사람이 적은
                    호칭만 오고(`paik` 36번), 에이전트 불릿은 아래 제 칸에
                    따로 선다. */}
                {(titles[s.user_id] || FLAVOR[s.nickname]?.title) && (
                  <span className="ss-suggest-title">
                    {titles[s.user_id] ?? FLAVOR[s.nickname].title}
                  </span>
                )}
                {/* 🔴 **분석이 낸 불릿**(CCC 56, 2026-09-17). 오늘 아침까지는
                    여기 붙박이 문장이 있었는데 **재는 것이 없는 말**이라
                    걷었고(`ho` 50번), 같은 날 정어진이 진짜 값을 냈다.

                    🔴 **한 줄·`null` 둘 다 정상이다** — 두 줄을 채우려고
                    지어내지 않는 것이 에이전트 쪽 규칙이라, 없으면 이 칸을
                    아예 안 그린다. 화면에서 문장을 짓지 않는다.

                    🔴 **이름 아래 한 줄과 다른 자리다** — 그쪽은 **사람이
                    적은 호칭**(CCC 51)이고 이건 **분석이 낸 것**이다. 섞으면
                    팀장이 사람이 적은 글까지 AI 판정으로 읽는다. */}
                {s.notes && s.notes.length > 0 && (
                  <span className="ss-suggest-notes">
                    {s.notes.map((n) => (
                      <span key={n}>{n}</span>
                    ))}
                  </span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
