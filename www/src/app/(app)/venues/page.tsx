import PageEnter from '@/components/PageEnter'
import { SPORT_LABEL, won } from '@/lib/market'
import { VENUES } from '@/lib/venues'

/**
 * 경기장 예약 목록.
 *
 * 🔴 아직 **보기만** 된다 — 예약(계약·결제)은 붙어 있지 않다. 계약에 구장
 * 조회·예약이 아직 없어(`lib/venues.ts` 주석) 목록을 먼저 내놓는다(레슨 ·
 * 상점과 같은 순서).
 */
export default function VenuesPage() {
  return (
    <PageEnter className="ss-venues">
      <header className="ss-venues-head ss-rise">
        <h1>경기장 예약</h1>
        <p>
          가까운 구장을 찾아보세요. 예약 접수는 아직 준비 중이라
          지금은 목록만 볼 수 있습니다.
        </p>
      </header>

      <ul className="ss-venue-list ss-rise" style={{ '--ss-rise-i': 1 } as React.CSSProperties}>
        {VENUES.map((v) => (
          <li key={v.id} className="ss-venue-card">
            <div className="ss-venue-card-head">
              <b>{v.name}</b>
              <span>{v.region}</span>
            </div>
            <p className="ss-venue-card-address">{v.address}</p>
            <p className="ss-venue-card-tagline">{v.tagline}</p>
            <div className="ss-venue-card-foot">
              <span className="ss-venue-sports">
                {v.sports.map((s) => (
                  <span key={s} className="ss-venue-sport-tag">
                    {SPORT_LABEL[s]}
                  </span>
                ))}
              </span>
              <span className="ss-venue-price">시간당 {won(v.pricePerHour)}</span>
            </div>
          </li>
        ))}
      </ul>
    </PageEnter>
  )
}
