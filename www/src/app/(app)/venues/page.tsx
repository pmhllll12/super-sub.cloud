import PageEnter from '@/components/PageEnter'
import { SPORT_LABEL } from '@/lib/market'
import { VENUES } from '@/lib/venues'

/**
 * 경기장 예약 목록.
 *
 * 🔴 예약은 우리가 중개하지 않는다 — 시간대별 `열려있음/마감` 배지까지만
 * 우리 화면이고, "예약하러 가기"는 서울시 공식 예약 사이트로 나가는 외부
 * 링크다(`lib/venues.ts` 주석 · 미결 7번 결정). 계약에 구장 조회·예약이
 * 아직 없어(레슨 · 상점과 같은 순서) 목록을 먼저 내놓는다.
 */
export default function VenuesPage() {
  return (
    <PageEnter className="ss-venues">
      <header className="ss-venues-head ss-rise">
        <h1>경기장 예약</h1>
        <p>
          가까운 구장을 찾아보세요. 실제 예약·결제는 서울시 공공서비스예약
          사이트에서 이루어지며, 여기서는 시간대별 접수 현황만 보여드립니다.
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
            <span className="ss-venue-sports">
              {v.sports.map((s) => (
                <span key={s} className="ss-venue-sport-tag">
                  {SPORT_LABEL[s]}
                </span>
              ))}
            </span>
            <ul className="ss-venue-slots">
              {v.slots.map((slot) => (
                <li key={`${slot.label}-${slot.hours}`} className="ss-venue-slot">
                  <span className={`ss-venue-slot-status ${slot.open ? 'is-open' : 'is-closed'}`}>
                    {slot.open ? '접수중' : '접수마감'}
                  </span>
                  <span className="ss-venue-slot-time">
                    {slot.label} · {slot.hours}
                  </span>
                  {slot.open && (
                    <a
                      className="ss-venue-slot-link"
                      href={slot.reserveUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      예약하러 가기
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </PageEnter>
  )
}
