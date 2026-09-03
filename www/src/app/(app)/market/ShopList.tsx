'use client'

import Image from 'next/image'
import { useState } from 'react'
import { SPORT_LABEL, type Product, type SportCode } from '@/lib/market'
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

      {/* 🔴 상품 칸을 걷어내고 **배너 한 장**만 둔다(사용자 요청). 지금 상점은
          자리 표시라(제휴 링크 · mock 데이터, `docs/2026-09-01-레슨-상점-설계.md`)
          빈 칸 여섯이 서 있는 것보다 한 장이 낫다는 판단이다.

          🔴 목록을 **지운 것이 아니라 안 그리는 것**이다 — `products` · 거름망 ·
          정렬은 그대로 살아 있고 위 줄이 세는 수도 진짜 값이다. 상품 사진이
          생기면 이 자리에 `<ul className="ss-coach-list">` 를 도로 넣으면 된다
          (지운 모양은 `CoachList` 의 카드와 같은 짜임이었다).

          ⚠️ 사진은 **자리 표시**다(`public/shop-banner.jpg`, 사용자 제공). 실제
          상품 그림이 오면 갈아 끼운다. 원본(4.8MB PNG)을 2400px JPEG 449KB 로
          줄여 넣었다 — 저장소에 원본을 그대로 넣지 말 것.

          ⚠️ **벽 쪽이 뭉개져 보이는 것은 우리가 줄여서가 아니다.** 받은 파일
          자체가 이미 한 번 압축된 그림을 화면에서 캡처한 것이라, 어두운 벽의
          매끈한 그러데이션에 블록이 배어 있다(원본 픽셀에서 확인). 여기서 더
          살릴 수 있는 정보가 없다 — **브랜드 원본 파일**을 받아 갈아 끼우는 것이
          유일한 해결이다. 그때까지는 다시 압축하며 더 망가뜨리지 않도록 품질을
          높게(96) 잡아 둔다. */}
      <div className="ss-shop-banner">
        {/* `next/image` 로 둔다 — 이 화면에서 **가장 큰 그림**이라 기기 폭에 맞는
            크기로 잘라 보내는 값이 크다(`sizes`). 비율은 원본 그대로고, 폭 맞추기와
            높이 자동은 `globals.css` 가 한다. */}
        <Image
          src="/shop-banner.jpg"
          alt="SUPERSUB 축구화"
          width={2400}
          height={901}
          sizes="100vw"
        />
      </div>
    </>
  )
}
