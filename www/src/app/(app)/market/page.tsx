import HeroFit from '@/components/HeroFit'
import PageEnter from '@/components/PageEnter'
import HeroGate from '@/components/HeroGate'
import { COACHES, PRODUCTS } from '@/lib/market'
import MarketGates from './MarketGates'

/**
 * 레슨 · 상점 **입구**.
 *
 * 🔴 목록으로 바로 보내지 않는다. 내비 항목은 `레슨 · 상점` 하나인데 그 안의
 * 두 갈래는 **의도가 다르다**(배우러 옴 vs 사러 옴) — 바로 보내면 한 항목에
 * 두 화면이 걸려 어느 쪽이 열릴지 예측이 안 된다. 홈에서 알약 셋을 나눈 것과
 * 같은 이유다.
 *
 * 설계: `www/docs/2026-09-01-레슨-상점-설계.md`
 */
export default function MarketPage() {
  return (
    <PageEnter className="ss-market ss-market-entry">
      {/* 🔴 이 화면은 **굴러가지 않는다**(사용자 요청). 한 화면 안에서 표지 글이
          나가면 그 자리에 두 문이 들어온다. 굴림은 그 신호로만 쓴다. */}
      <HeroGate />
      {/* 🔴 이 덩어리는 **첫 화면 안에 다 들어와야 한다.** 그런데 위에 있는
          헤더 높이가 사용자마다 달라(카드 유무) 상수로는 못 맞춘다 — 실제로
          재서 맞춘다. HeroFit 주석 참고. */}
      <HeroFit className="ss-market-head" bottom={32}>
        {/* 🔴 제목은 화면에 안 보이지만 **있어야 한다.** 아래 두 덩어리가 각각
            제 제목(h2)을 갖고 있어서, 이 화면 전체를 가리키는 제목이 없으면
            화면 낭독기로 읽을 때 두 덩어리가 어디에 속하는지 알 수 없다. */}
        <h1 className="sr-only">레슨 · 상점</h1>

        {/* 🔴 사진의 **빈 자리(왼쪽 아래)**에 앉힌다(사용자 요청). 인물이
            오른쪽에 있어 왼쪽이 비는데, 거기에 글을 두면 사진을 가리지 않고
            둘이 한 화면으로 읽힌다. 폭을 좁게 묶어 두는 것이 그 조건이다. */}
        {/* 🔴 여기서는 `ss-rise`(아래에서 위로)를 쓰지 않는다. 이 화면은
            위에서 아래로 읽는 문서가 아니라 **한 화면짜리 표지**라, 넷이
            차례로 왼쪽에서 미끄러져 들어오는 편이 낫다(사용자 요청). */}
        <div className="ss-market-intro">
          <section className="ss-market-in" style={{ '--ss-in-i': 0 } as React.CSSProperties}>
            <span className="ss-market-intro-kind">
              레슨
              <span className="material-symbols-outlined" aria-hidden="true">
                play_lesson
              </span>
            </span>
            <h2>코치와 함께하는 레슨</h2>
            {/* 줄바꿈 자리를 못 박는다(사용자 요청) — 저절로 접히면 "레슨을"
                이 앞 줄 끝에 매달려 읽는 결이 끊긴다. */}
            <p>
              유저들과 AI 분석을 통해 인정받은 코치에게
              <br />
              레슨을 신청하고 배워보세요.
            </p>
          </section>

          {/* 🔴 가르는 선을 `border` 가 아니라 **진짜 요소**로 둔다 — 선도 차례에
              끼어 따로 들어와야 하는데, 테두리는 제 순서를 가질 수가 없다. */}
          <hr className="ss-market-rule ss-market-in" style={{ '--ss-in-i': 1 } as React.CSSProperties} />

          <section className="ss-market-in" style={{ '--ss-in-i': 2 } as React.CSSProperties}>
            <span className="ss-market-intro-kind">
              상점
              <span className="material-symbols-outlined" aria-hidden="true">
                store
              </span>
            </span>
            <h2>스포츠 브랜드들이 한 곳에</h2>
            <p>
              내가 원하는 스포츠 브랜드를 찾아보고
              <br />
              상품을 구매하세요.
            </p>
          </section>

          {/* 🔴 두 문(레슨/상점)은 스크롤을 내려야 나온다 — 첫 화면에 일부러
              안 보이게 해 뒀으므로, 내려야 한다는 것을 여기서 알려 준다.
              안 그러면 이 화면이 막다른 길처럼 읽힌다. */}
          <p className="ss-market-scroll ss-market-in" style={{ '--ss-in-i': 3 } as React.CSSProperties}>
            {/* 🔴 그림을 한 겹 싸는 이유 — 껍데기는 가운데 셈에서 빠지도록
                흐름 밖으로 빼고(CSS), 안쪽 그림은 제 흔들림(transform)을
                그대로 쓴다. 한 겹으로 하면 두 transform 이 서로 덮어쓴다. */}
            <span className="ss-market-scroll-icon" aria-hidden="true">
              <span className="material-symbols-outlined">
                keyboard_double_arrow_down
              </span>
            </span>
            아래로 내리면 레슨과 상점으로 갑니다.
          </p>
        </div>
      </HeroFit>

      {/* 두 문과 그 옆으로 펼쳐지는 목록 판. 열림/닫힘이 화면 안의 상태라
          거기서부터는 클라이언트다(`MarketGates`). */}
      <MarketGates coaches={COACHES} products={PRODUCTS} />
    </PageEnter>
  )
}
