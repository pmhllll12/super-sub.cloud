'use client'

import { useState } from 'react'
import { SPORT_LABEL, won, type Product, type SportCode } from '@/lib/market'
import { FilterBar, SortSelect } from './FilterBar'

/**
 * 줄 세우는 법. 🔴 `recommended` 는 **목록에 손을 안 대는 것**이다 — 지금은
 * 데이터가 들어 있는 차례가 곧 우리 차례다(코치 목록과 같은 규칙).
 * ⚠️ 판매 수가 없어 '많이 팔린 순'은 아직 못 만든다. 생기면 여기에 붙인다.
 */
const SHOP_SORTS = [
  { value: 'recommended', label: '추천순' },
  { value: 'price-asc', label: '가격 낮은 순' },
  { value: 'price-desc', label: '가격 높은 순' },
  { value: 'videos', label: '영상 많은 순' },
] as const
type ShopSort = (typeof SHOP_SORTS)[number]['value']

/**
 * 상품 목록과 거름망.
 *
 * 🔴 **사는 곳은 우리가 아니다.** 링크는 브랜드 사이트로 나가는 바깥 링크라
 * 새 탭으로 열고 화살표(↗)로 나간다는 것을 밝힌다 — 우리 화면 안에서 결제가
 * 이어질 것처럼 보이면 안 된다(설계 §1-1, `docs/2026-09-01-레슨-상점-설계.md`).
 * 나중에 이 `href` 에 추적 파라미터(우리 ID + 영상 주인 ID)가 붙는다.
 *
 * 🔴 종목 알약은 코치 목록(`CoachList`)과 **같은 모양**을 쓴다(`.ss-shot-sport`).
 * 같은 뜻의 것에 다른 모양을 주지 않는다.
 *
 * 거름망을 클라이언트에 둔 이유도 코치 목록과 같다 — 지금은 mock 이라 목록이
 * 몇 개뿐이고, 서버로 다시 물으면 화면이 한 번 비었다 돌아온다.
 */
export default function ShopList({ products }: { products: Product[] }) {
  const [sport, setSport] = useState<SportCode | null>(null)
  const [sort, setSort] = useState<ShopSort>('recommended')

  const shown = products
    .filter((p) => !sport || p.sport === sport)
    // `filter` 가 이미 새 배열을 준다 — 부모가 가진 목록은 안 건드린다.
    .sort((a, b) => {
      if (sort === 'price-asc') return a.price - b.price
      if (sort === 'price-desc') return b.price - a.price
      if (sort === 'videos') return b.videoCount - a.videoCount
      return 0
    })

  return (
    <>
      {/* 코치 목록과 **같은 거름망 한 줄**을 쓴다(`FilterBar`) — 두 목록이
          다르게 생기면 여기서 조작을 새로 배워야 한다. */}
      <FilterBar
        fields={[
          {
            key: 'sport',
            label: '종목',
            value: sport ? SPORT_LABEL[sport] : null,
            picked: sport,
            onPick: (v) => setSport(v as SportCode | null),
            options: (Object.keys(SPORT_LABEL) as SportCode[]).map((code) => ({
              value: code,
              label: SPORT_LABEL[code],
            })),
          },
        ]}
        end={
          <>
            <span className="ss-filterbar-count">
              상품 <b>{shown.length}</b>
              {sport ? <em> / {products.length}</em> : null}
            </span>
            <SortSelect value={sort} options={[...SHOP_SORTS]} onChange={setSort} />
          </>
        }
      />

      {shown.length === 0 ? (
        <p className="ss-market-empty">조건에 맞는 상품이 아직 없습니다.</p>
      ) : (
        <ul className="ss-coach-list">
          {shown.map((p) => (
            <li key={p.id}>
              <a
                href={p.href}
                className="ss-coach-card"
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="ss-coach-card-head">
                  <b>{p.brand}</b>
                  <span>
                    {SPORT_LABEL[p.sport]} · {p.category}
                  </span>
                </span>

                <span className="ss-coach-card-tagline">{p.name}</span>

                {/* 🔴 우리만 가진 것 — 이 상품이 **어떤 영상에 나왔는지**다.
                    브랜드 사이트에는 없는 정보라 이것이 여기서 보는 이유다. */}
                <span className="ss-coach-card-analysis">
                  <em>영상에 태그된 장비</em>
                  <span className="ss-coach-titles">
                    <b>영상 {p.videoCount}개</b>
                  </span>
                </span>

                <span className="ss-coach-card-foot">
                  {won(p.price)}
                  <i>브랜드에서 보기 ↗</i>
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
