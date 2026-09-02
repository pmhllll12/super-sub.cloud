'use client'

import { useState } from 'react'
import { TransitionLink } from '@/lib/pageTransition'
import { LEVEL_LABEL, SPORT_LABEL, won, type Coach } from '@/lib/market'
import LessonApply, { LessonApplyButton } from './[id]/LessonApply'

/**
 * 신청서에서 고를 수 있는 항목.
 *
 * ⚠️ 자리 표시다 — 실제로는 **내 최근 리포트**에서 가져온다. 계약에 리포트 조회가
 * 아직 없다(미결). 여기 한 곳에 둔 것은, 두 자리(주소로 열 때 · 판 안에서 열 때)가
 * 같은 것을 보여 줘야 하기 때문이다.
 */
const MY_FINDINGS = [
  '디딤발이 공보다 앞서 있습니다',
  '측면으로 벌리는 움직임이 많습니다',
  '두 번째 동작으로 이어지는 속도가 빠릅니다',
]

/**
 * 코치 상세의 **알맹이** — "우리만의 기준"이 사는 곳이다.
 *
 * 차례가 곧 주장이다:
 *   ① 이 코치의 분석      ← 간판. 우리만 있는 것
 *   ② 확인된 것           자격 · 경력은 **받침**이지 간판이 아니다
 *   ③ 가르친 사람들의 변화  아직 비어 있다 — 비워 두는 것이 설계다
 *   ④ 후기  ⑤ 레슨 정보
 *
 * 🔴 ① 의 모양이 영상 분석 화면의 리포트와 **같다**(요약 · 이렇게 본 장면).
 * 사용자가 자기 리포트에서 이미 본 모양이라 읽는 법을 새로 배울 것이 없다.
 *
 * 🔴 **수치를 그리지 않는다.** 카드에 능력치 컬럼을 두지 않는 원칙(부록 D.5)이
 * 코치에게도 그대로 적용된다 — 호칭 · 문장 · 장면뿐이다.
 *
 * 🔴 이것이 **한 벌뿐**인 것이 요점이다. 제 주소(`/market/coaches/{id}`)로 열릴
 * 때와 레슨 · 상점 입구의 오른쪽 판 안에서 열릴 때가 같은 것을 그린다 — 두 벌로
 * 두면 한쪽만 고쳐진다. 자리마다 다른 것은 **머리글과 돌아가는 길**뿐이라
 * 그것만 밖에서 받는다.
 */
export default function CoachDetail({
  coach,
  /**
   * 돌아가는 길. 자리마다 다르다 — 주소로 열면 링크, 판 안에서는 없다(판이 제
   * 화살표를 따로 그린다). 🔴 **머리글은 여기서 만든다** — 자리마다 만들면 두
   * 벌이 되어 한쪽만 늙는다.
   */
  back,
  /** 코치 영상으로 나가는 링크를 보일 것인가. 판 안에서는 안 나간다. */
  video = true,
}: {
  coach: Coach
  back?: React.ReactNode
  video?: boolean
}) {
  /**
   * 🔴 신청서를 여는 상태는 **여기**가 쥔다. 단추는 머리글 오른쪽에 있고 신청서는
   * 머리글 **아래**에서 펴지므로(사용자 요청) 둘이 떨어져 있어, 둘을 다 보는
   * 자리에서 쥐어야 한다.
   */
  const [applyOpen, setApplyOpen] = useState(false)

  return (
    <>
      {back}
      <header className="ss-market-head">
        <div className="ss-coach-title">
          <div>
            <h1>{coach.name}</h1>
            <p>
              {SPORT_LABEL[coach.sport]} · {coach.region} · 회당{' '}
              {won(coach.pricePerSession)}
            </p>
          </div>
          {/* 🔴 신청서가 펴져 있는 동안에는 **이 단추가 사라진다**(사용자 요청) —
              같은 일을 하는 자리가 둘이면 어느 것이 지금 살아 있는지 헷갈린다.
              자리는 남겨 둔 채 흐려지기만 한다: 없애 버리면 머리글이 그 폭만큼
              줄어들며 이름이 옆으로 흔들린다. */}
          <LessonApplyButton hidden={applyOpen} onClick={() => setApplyOpen(true)} />
        </div>
      </header>

      {/* 🔴 신청서는 **머리글 바로 아래**에서 펴진다(사용자 요청) — 단추 옆에서
          펴지면 머리글이 통째로 부풀어 이름이 밀려난다. */}
      <LessonApply
        coachName={coach.name}
        myFindings={MY_FINDINGS}
        open={applyOpen}
        onClose={() => setApplyOpen(false)}
      />
    {/* ① 간판 */}
    <section className="ss-coach-sec ss-coach-analysis ss-rise" style={{ '--ss-rise-i': 1 } as React.CSSProperties}>
      <h2>이 코치의 분석</h2>
      <p className="ss-coach-analysis-why">
        코치도 <b>수강생과 같은 잣대</b>로 잽니다. 자기소개가 아니라 리포트입니다.
      </p>

      <div className="ss-coach-titles">
        {coach.titles.map((t) => (
          <b key={t}>{t}</b>
        ))}
      </div>

      <p className="ss-coach-summary">{coach.report.summary}</p>

      <h3>이렇게 본 장면</h3>
      <ul className="ss-report-scenes">
        {coach.report.scenes.map((s) => (
          <li key={s.at}>
            <b>{s.at}</b>
            {s.what}
          </li>
        ))}
      </ul>

      {/* 🔴 이 링크는 **판 안에서는 안 나온다**(`video={false}`). 판 안에서
          누르면 화면이 통째로 갈려 "저 판에서만 바뀐다"가 깨지고, 무엇보다
          `/v/{slug}` 라우트가 **아직 없다**(누르면 404). 영상 화면이 생기면
          그때 판 안에서 어떻게 보일지 정한다. */}
      {video ? (
        <TransitionLink href={`/v/${coach.report.videoSlug}`} className="ss-coach-video">
          코치의 영상 보기 →
        </TransitionLink>
      ) : null}
    </section>

    {/* ② 받침 */}
    <section className="ss-coach-sec ss-rise" style={{ '--ss-rise-i': 2 } as React.CSSProperties}>
      <h2>확인된 것</h2>
      {/* 🔴 코치가 **적은 것**이 아니라 우리가 **확인한 것**만 적는다. */}
      <ul className="ss-coach-verified">
        {coach.verified.map((v) => (
          <li key={v}>{v}</li>
        ))}
      </ul>
    </section>

    {/* ③ 비워 두는 것이 설계다 */}
    <section className="ss-coach-sec ss-rise" style={{ '--ss-rise-i': 3 } as React.CSSProperties}>
      <h2>가르친 사람들의 변화</h2>
      <p className="ss-coach-empty">
        아직 데이터가 쌓이지 않았습니다. 레슨 전후로 영상을 분석하면 여기에
        그 변화가 쌓입니다.
      </p>
    </section>

    <section className="ss-coach-sec ss-rise" style={{ '--ss-rise-i': 4 } as React.CSSProperties}>
      <h2>후기 {coach.reviews.length}</h2>
      {coach.reviews.length === 0 ? (
        <p className="ss-coach-empty">아직 후기가 없습니다.</p>
      ) : (
        <ul className="ss-coach-reviews">
          {coach.reviews.map((r) => (
            <li key={r.at}>
              <b>{r.by}</b>
              <p>{r.text}</p>
              <time>{r.at}</time>
            </li>
          ))}
        </ul>
      )}
    </section>

    <section className="ss-coach-sec ss-rise" style={{ '--ss-rise-i': 5 } as React.CSSProperties}>
      <h2>레슨 정보</h2>
      <dl className="ss-coach-info">
        <dt>장소</dt>
        <dd>{coach.lesson.places.join(' · ')}</dd>
        <dt>시간대</dt>
        <dd>{coach.lesson.hours}</dd>
        <dt>받는 수준</dt>
        <dd>{coach.levels.map((l) => LEVEL_LABEL[l]).join(' · ')}</dd>
        <dt>그 밖에</dt>
        <dd>{coach.lesson.note}</dd>
      </dl>
    </section>
    </>
  )
}
