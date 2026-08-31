import BrandMark from '@/components/ui/BrandMark'

/**
 * 아직 사람이 안 들어간 선수 카드의 틀 — 흰 바탕에 머리글(SUPERSUB ·
 * PLAYER CARD)만 있고 가운데는 비어 있다.
 *
 * 채워진 카드(`PlayerCardView`)와 **같은 클래스**(`.ss-pcard`)를 쓴다 —
 * 따로 만들면 카드 모양을 바꿀 때 두 벌이 따로 늙는다. 가운데 자리만
 * 비워서 넘겨받는다: 스쿼드 판의 빈 자리는 `+` 를, 추천 목록은 아무것도
 * 넣지 않는다(누르는 곳이 아니라 "여기가 카드가 될 자리"라는 표식이라
 * `+` 가 있으면 그걸 누르라는 말이 된다).
 *
 * 🔴 이 컴포넌트가 `SquadPanel` 밖에 따로 있는 이유는 **순환 import** 다.
 * `SquadPanel` → `SquadSuggest` 로 이미 한 방향이 나 있어서, 추천 판이
 * 이 틀을 쓰려면 되돌아가는 import 가 생긴다.
 */
export default function BlankPlayerCard({ children }: { children?: React.ReactNode }) {
  return (
    <article className="ss-pcard ss-pcard-blank">
      <div className="ss-pcard-inner">
        <header className="ss-pcard-top">
          {/* 빈 카드는 바탕이 희어서 워드마크를 검게 찍을 이유가 없다 —
              브랜드 민트로 둔다(채워진 카드는 연두 바탕이라 그 반대다). */}
          <BrandMark size={22} color="var(--ss-accent)" />
          <p className="ss-pcard-kicker">PLAYER CARD</p>
        </header>
        <div className="ss-squad-seat-body">{children}</div>
      </div>
    </article>
  )
}
