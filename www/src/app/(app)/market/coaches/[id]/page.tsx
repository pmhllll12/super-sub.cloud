import { notFound } from 'next/navigation'
import PageEnter from '@/components/PageEnter'
import { TransitionLink } from '@/lib/pageTransition'
import { SPORT_LABEL, LEVEL_LABEL, findCoach, won } from '@/lib/market'
import LessonApply from './LessonApply'

/**
 * 코치 상세 — **"우리만의 기준"이 사는 곳**이다.
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
 */
export default async function CoachPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const coach = findCoach(id)
  if (!coach) notFound()

  return (
    <PageEnter className="ss-market ss-coach">
      <header className="ss-market-head ss-rise">
        <TransitionLink href="/market/coaches" className="ss-market-back">
          ← 코치
        </TransitionLink>
        <div className="ss-coach-title">
          <div>
            <h1>{coach.name}</h1>
            <p>
              {SPORT_LABEL[coach.sport]} · {coach.region} · 회당{' '}
              {won(coach.pricePerSession)}
            </p>
          </div>
          <LessonApply
            coachName={coach.name}
            // ⚠️ 자리 표시 — 실제로는 내 최근 리포트에서 가져온다. 계약에
            // 리포트 조회가 아직 없다(미결).
            myFindings={[
              '디딤발이 공보다 앞서 있습니다',
              '측면으로 벌리는 움직임이 많습니다',
              '두 번째 동작으로 이어지는 속도가 빠릅니다',
            ]}
          />
        </div>
      </header>

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

        <TransitionLink href={`/v/${coach.report.videoSlug}`} className="ss-coach-video">
          코치의 영상 보기 →
        </TransitionLink>
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
    </PageEnter>
  )
}
