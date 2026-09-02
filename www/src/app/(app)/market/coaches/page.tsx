import PageEnter from '@/components/PageEnter'
import { TransitionLink } from '@/lib/pageTransition'
import { COACHES } from '@/lib/market'
import CoachList from './CoachList'

/** 코치 목록. 거름망은 클라이언트가 쥔다(`CoachList`). */
export default function CoachesPage() {
  return (
    <PageEnter className="ss-market">
      <header className="ss-market-head ss-rise">
        <TransitionLink href="/market" className="ss-market-back">
          ← 레슨 · 상점
        </TransitionLink>
        <h1>코치</h1>
        <p>
          코치도 영상을 올려 <b>수강생과 같은 분석</b>을 받습니다. 자기소개가
          아니라 리포트를 보고 고르세요.
        </p>
      </header>

      <div className="ss-rise" style={{ '--ss-rise-i': 1 } as React.CSSProperties}>
        <CoachList coaches={COACHES} />
      </div>
    </PageEnter>
  )
}
