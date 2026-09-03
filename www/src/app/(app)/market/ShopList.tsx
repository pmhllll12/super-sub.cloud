'use client'

import Image from 'next/image'
import { useEffect, useRef, useState } from 'react'
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
  const banner = useRef<HTMLDivElement | null>(null)
  /** 붙는 자리의 과녁 — 이 줄의 윗선이 머리 띠의 아랫선에 닿아야 한다. */
  const word = useRef<HTMLDivElement | null>(null)

  /**
   * 굴린 만큼을 **0~1 로** 배너에 넘긴다 — 흐려지고 올라가는 것은 CSS 가 한다
   * (`globals.css` 의 `.ss-shop-banner`).
   *
   * 🔴 **창이 아니라 판이 구른다.** 이 화면은 오른쪽 판(`.ss-market-detail-body`)
   * 안에서 굴러가므로 `window` 의 굴림은 0 그대로다 — 굴림 자리를 타고 올라가
   * 찾는다. 못 찾으면(판 밖에서 쓰이게 되면) 창을 듣는다.
   * 🔴 사진 키의 **70%** 에서 다 사라진다. 100% 로 두면 사진이 이미 화면 밖으로
   * 나간 뒤에야 다 사라져서, 흐려지는 것이 눈에 안 띈다.
   * 🔴 매 굴림마다 그리지 않고 **한 프레임에 한 번**만 쓴다(`requestAnimationFrame`).
   *    트랙패드는 한 프레임에 굴림을 여러 번 보낸다.
   */
  useEffect(() => {
    const el = banner.current
    if (!el) return
    const box = el.closest('.ss-market-detail-body')
    if (!(box instanceof HTMLElement)) return
    const at = () => box.scrollTop

    let raf = 0
    const draw = () => {
      raf = 0
      const span = el.offsetHeight * 0.7 || 1
      el.style.setProperty(
        '--ss-shop-banner-p',
        String(Math.min(1, Math.max(0, at() / span))),
      )
    }

    /**
     * 붙는 자리 — **간판(STORE)의 윗선이 머리 띠의 아랫선에 닿는** 굴림 값.
     *
     * 🔴 계산하지 않고 **잰다**(`getBoundingClientRect`). 띠의 키도 간판까지의
     * 거리도 `clamp` 와 글꼴에서 나와 창마다 다르다 — 여백을 더하고 빼서 맞추려
     * 들면 어떤 폭에서는 반드시 어긋난다(이 화면의 `sticky` 자리를 그렇게 두 번
     * 틀렸다).
     */
    const anchor = () => {
      const head = box.querySelector('.ss-filterbar-wrap')
      const mark = word.current
      if (!mark || !(head instanceof HTMLElement)) return 0
      return (
        at() + mark.getBoundingClientRect().top - head.getBoundingClientRect().bottom
      )
    }

    /**
     * 🔴 **이 화면은 손으로 굴리지 않는다**(사용자 요청). 손짓은 "다음 자리로
     * 가 달라"는 뜻으로만 받고, 실제로 옮기는 것은 **0.8초 뒤에 우리가** 한다.
     *
     * 🔴 그래서 굴림을 통째로 막는다(`preventDefault`, 그래서 `passive` 가
     *    아니다). 흘려보내면 손을 따라 조금씩 밀려 올라간 뒤에 붙어서, "가만히
     *    있다가 저 혼자 넘어간다"가 안 된다(사용자 지적).
     * 🔴 시간은 **첫 손짓에서 잰다.** 손짓마다 다시 재면 트랙패드의 관성이
     *    끝날 때까지 기다리게 되어 "0.8초"가 사람마다 달라진다.
     * 🔴 움직임을 줄여 달라고 한 사람에게는 **아예 안 한다**(막지도 않는다) —
     *    부탁한 적 없는 움직임이라 그쪽에서는 굴림 그대로가 맞다.
     */
    let calm = false
    try {
      calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    } catch {
      calm = false
    }

    /**
     * 설 수 있는 자리들. 첫째는 배너가 다 보이는 맨 위, 둘째는 **간판이 띠 밑에
     * 붙는 자리**, 그 아래로는 **보이는 만큼씩** 내려간다.
     *
     * 🔴 손으로 못 굴리므로 **끝까지 갈 수 있어야 한다** — 마지막 자리를 늘
     * 바닥으로 두지 않으면 마지막 줄을 아무도 못 본다.
     * 🔴 한 걸음은 "화면 키"가 아니라 **띠에 가려지지 않는 높이**다. 화면 키로
     * 걸으면 띠에 가린 만큼이 매번 건너뛰어진다.
     */
    const stops = () => {
      const max = Math.max(0, box.scrollHeight - box.clientHeight)
      const list = [0]
      const to = anchor()
      if (to > 2) list.push(Math.min(to, max))
      const head = box.querySelector('.ss-filterbar-wrap')
      const hidden = head instanceof HTMLElement ? head.getBoundingClientRect().bottom : 0
      const page = Math.max(160, box.clientHeight - hidden)
      let v = (list[list.length - 1] ?? 0) + page
      while (v < max - 2) {
        list.push(v)
        v += page
      }
      if (max > (list[list.length - 1] ?? 0) + 2) list.push(max)
      return list
    }

    let pending = 0

    const step = (dir: number) => {
      pending = 0
      const list = stops()
      const now = at()
      // 지금 어느 자리에 있나 — 가장 가까운 자리를 지금으로 본다.
      let i = 0
      for (let k = 1; k < list.length; k++) {
        if (Math.abs(list[k] - now) < Math.abs(list[i] - now)) i = k
      }
      const next = Math.min(list.length - 1, Math.max(0, i + dir))
      box.scrollTo({ top: list[next], behavior: 'smooth' })
    }

    const hold = (e: Event, dy: number) => {
      if (calm || dy === 0) return
      e.preventDefault()
      if (pending) return
      const dir = dy > 0 ? 1 : -1
      pending = window.setTimeout(() => step(dir), 800)
    }

    const onWheel = (e: WheelEvent) => hold(e, e.deltaY)

    let touchY = 0
    const onTouchStart = (e: TouchEvent) => {
      touchY = e.touches[0]?.clientY ?? 0
    }
    const onTouchMove = (e: TouchEvent) => {
      const y = e.touches[0]?.clientY ?? 0
      // 손가락이 위로 올라가면 내용은 아래에서 위로 — 굴림으로는 내리는 쪽이다.
      hold(e, touchY - y)
    }

    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(draw)
    }

    draw()
    box.addEventListener('scroll', onScroll, { passive: true })
    box.addEventListener('wheel', onWheel, { passive: false })
    box.addEventListener('touchstart', onTouchStart, { passive: true })
    box.addEventListener('touchmove', onTouchMove, { passive: false })
    return () => {
      box.removeEventListener('scroll', onScroll)
      box.removeEventListener('wheel', onWheel)
      box.removeEventListener('touchstart', onTouchStart)
      box.removeEventListener('touchmove', onTouchMove)
      window.clearTimeout(pending)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [])

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

      {/* 🔴 목록 위에 **배너 한 장**(사용자 요청). 한동안 목록 없이 배너만 두던
          자리인데, 아래에 목록이 돌아오면서 이제는 목록의 머리 그림이다.

          ⚠️ 사진은 **자리 표시**다(`public/shop-banner.jpg`, 사용자 제공). 실제
          상품 그림이 오면 갈아 끼운다. 원본(4.8MB PNG)을 2400px JPEG 449KB 로
          줄여 넣었다 — 저장소에 원본을 그대로 넣지 말 것.

          ⚠️ **벽 쪽이 뭉개져 보이는 것은 우리가 줄여서가 아니다.** 받은 파일
          자체가 이미 한 번 압축된 그림을 화면에서 캡처한 것이라, 어두운 벽의
          매끈한 그러데이션에 블록이 배어 있다(원본 픽셀에서 확인). 여기서 더
          살릴 수 있는 정보가 없다 — **브랜드 원본 파일**을 받아 갈아 끼우는 것이
          유일한 해결이다. 그때까지는 다시 압축하며 더 망가뜨리지 않도록 품질을
          높게(96) 잡아 둔다.

          🔴 **갈아 끼울 때는 파일 이름도 같이 바꾼다.** 같은 이름에 덮어쓰면
          브라우저 · Next 이미지 최적화 · CDN 이 주소가 그대로라는 이유로 **옛
          그림을 계속 보여준다** — 서버는 새 파일을 주는데 화면만 안 바뀌어서
          원인을 찾기 어렵다(2026-09-03 에 다른 사진으로 갈아 보다 겪었다).
          🔴 그리고 아래 `width`/`height` 도 같이 고칠 것 — 그 둘이 자리를 잡아
          두는 값이라 안 맞으면 사진이 실릴 때 아래 글이 한 번 덜컥인다. */}
      <div className="ss-shop-banner" ref={banner}>
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

      {/* 🔴 배너와 목록 사이의 간판 한 마디(사용자 요청). 배너만 있던 때는 빈
          초록 자리를 채우는 것이었고, 목록이 돌아온 지금은 **목록의 머리글**이다.
          🔴 그래서 남는 자리를 차지하지 않는다(`flex: none`) — 늘어나게 두면
          목록을 저 아래로 밀어낸다. */}
      <div className="ss-shop-word" ref={word}>
        <p className="ss-shop-word-title">STORE</p>
        {/* 🔴 한글이라 **Anton 을 쓰지 않는다** — 라틴만 있는 장식 글꼴이라
            한글이 OS 기본 글꼴로 떨어지면서 두 줄이 따로 논다. 여기는 본문
            글꼴 그대로 두는 것이 맞다(다른 장식 글꼴들과 같은 규칙). */}
        <p className="ss-shop-word-sub">
          다양한 스포츠 브랜드들의 상품을 만나보세요.
        </p>
      </div>

      {/* 🔴 상품 목록 — **한 줄에 넷**이다(사용자 요청, 레퍼런스 "Explore Our
          Collection"). 카드는 브랜드 판 · 글 · 나가는 단추 세 층이다.

          🔴 **사는 곳은 우리가 아니다.** 카드를 통째로 바깥 링크로 두고 새 탭에서
          연다(위 컴포넌트 주석의 규칙 그대로다). 화살표(↗)만으로는 낭독기가 그걸
          못 읽으므로 숨은 글 한 줄을 같이 둔다.

          ⚠️ **상품 사진이 아직 없다.** 빈 칸을 두는 대신 브랜드 이름을 크게 넣은
          판을 뒀다 — 사진이 오면 이 자리에 `<Image>` 를 넣고 글은 그 위에 겹치면
          된다(레퍼런스가 그 모양이다). */}
      {shown.length === 0 ? (
        <p className="ss-market-empty">조건에 맞는 상품이 아직 없습니다.</p>
      ) : (
        <ul className="ss-shop-grid">
          {shown.map((p) => (
            <li key={p.id}>
              <a
                className="ss-shop-card"
                href={p.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="ss-shop-card-plate">{p.brand}</span>
                {/* 아래 줄은 **글 왼쪽 · 단추 오른쪽**이다(사용자 요청). 글을
                    한 상자로 묶어야 단추가 그 옆에 설 수 있다. */}
                <span className="ss-shop-card-body">
                  <span className="ss-shop-card-text">
                    <b>{p.name}</b>
                    <span className="ss-shop-card-desc">
                      {SPORT_LABEL[p.sport]} · {p.category}
                      <br />
                      {won(p.price)}
                    </span>
                  </span>
                  <span className="ss-shop-card-go">
                    SHOP NOW <i aria-hidden="true">↗</i>
                    <span className="sr-only">새 탭에서 열립니다</span>
                  </span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
