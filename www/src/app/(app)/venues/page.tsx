import PageEnter from '@/components/PageEnter'
import { VENUES } from '@/lib/venues'
import VenueBoard from './VenueBoard'

/**
 * 경기장 예약 목록.
 *
 * 🔴 예약은 우리가 중개하지 않는다 — 시간대별 `접수중/마감` 배지까지만
 * 우리 화면이고, 「예약하러 가기」는 서울시 공식 예약 사이트로 나가는 외부
 * 링크다(`lib/venues.ts` 주석 · 미결 7번 결정). 계약에 구장 조회·예약이
 * 아직 없어(레슨 · 상점과 같은 순서) 목록을 먼저 내놓는다.
 *
 * 🔴 **거르기 때문에 판이 브라우저 쪽이다**(`VenueBoard`). 목록은 붙박이라
 * 서버에서 그려도 되지만, 종목 · 지역 · 접수중을 고르는 일이 화면 안에서
 * 일어난다 — 43곳을 한 번에 늘어놓으면 훑을 수가 없다.
 */
export default function VenuesPage() {
  return (
    <PageEnter className="ss-venues">
      <VenueBoard venues={VENUES} />
    </PageEnter>
  )
}
