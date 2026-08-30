import type { PublicPlayerCard } from '@/server/backend'
import BrandMark from './ui/BrandMark'

/**
 * 세로 포스터형 선수 카드 — 참고 디자인(MOJO 시즌 카드)의 짜임이다.
 * 검은 테두리 안에 **흰 카드**가 들어 있고, 위에 워드마크와 작은 머리글,
 * 아래 절반에 누끼 인물, 맨 아래에 형광 알약과 검은 막대 · 원형 배지가 온다.
 *
 * 인물은 `public/player_cutout.png` — 배경이 검던 원본에서 사람만 떼어
 * 낸 것이다(만든 과정은 커밋 메시지 참고). **카드 세로 가운데 위로는
 * 올라오지 않는다** — 위쪽 절반은 워드마크와 머리글의 자리다.
 *
 * 🔴 카드에 **닉네임을 글자로 적지 않는다.** 참고 디자인처럼 인물이
 * 가운데를 차지하는 그림이라 이름이 들어갈 자리가 없다. 다만 카드가
 * 누구 것인지는 읽어 주는 기계에도 남아야 하므로 article 의 이름으로
 * 준다(aria-label).
 *
 * 🔴 사이트 전체가 어두운 화면인데 이 카드만 밝다. 의도한 것이다 —
 * 참고 디자인이 그렇고, 카드는 밖으로 공유되는 물건이라 어디에 놓여도
 * 같은 얼굴이어야 한다. 그래서 색을 사이트 토큰(--ss-fg/--ss-bg)이
 * 아니라 **카드 전용 토큰(--ss-pcard-*)** 에서 가져온다.
 *
 * 🔴 **수치를 그리지 않는다** (계약서 4절 / 부록 D.5).
 * 점수 · 등급 · 별점 · 진행률 바를 여기에 넣지 않는다. DB 설계가
 * `player_card` 에 능력치 컬럼을 아예 두지 않는 방식으로 이걸 막아 뒀는데,
 * 화면에서 되살아나면 그 설계가 통째로 무의미해진다.
 * titles 는 **받은 것만** 온다 — 미달 표식을 만들지 않는다.
 */
export default function PlayerCardView({ card }: { card: PublicPlayerCard }) {
  return (
    <article className="ss-pcard" aria-label={card.user.nickname}>
      <div className="ss-pcard-inner">
        <header className="ss-pcard-top">
          <BrandMark size={22} color="var(--ss-pcard-fg)" />
          <p className="ss-pcard-kicker">PLAYER CARD</p>
        </header>

        {/* 누끼 인물 — 장식이라 스크린리더에서 숨긴다. 아래 절반만
            차지하게 두어(top: 50%) 카드 가운데 위로 넘어가지 않는다. */}
        <div className="ss-pcard-figure" aria-hidden="true">
          {/* eslint-disable-next-line @next/next/no-img-element -- 카드 장식용 고정 이미지 */}
          <img src="/player_cutout.png" alt="" decoding="async" />
        </div>

        {/* 맨 아래 두 줄. 참고 디자인은 [검은 막대][형광 알약][원형 배지]가
            한 줄인데, 그건 알약이 하나(날짜)일 때 이야기다 — 호칭은 여러
            개일 수 있어 한 줄에 밀어 넣으면 알약이 접히면서 검은 막대가
            조각으로 남는다. 그래서 알약에 제 줄을 주고, 막대와 배지가
            그 아래 한 줄을 이룬다. */}
        <footer className="ss-pcard-foot">
          {/* 라벨은 화면에 두지 않지만 읽어 주는 기계에는 남긴다 —
              알약만 있으면 이게 무엇의 목록인지 알 수 없다. */}
          <h2 className="sr-only">호칭</h2>
          {card.titles.length === 0 ? (
            <p className="ss-pcard-empty">아직 받은 호칭이 없습니다</p>
          ) : (
            <ul className="ss-pcard-titles">
              {card.titles.map((t) => (
                <li key={t.code}>
                  <span className="ss-pcard-title-category">{t.category}</span>
                  <span className="ss-pcard-title-label">{t.label}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="ss-pcard-foot-row">
            <span className="ss-pcard-bar" aria-hidden="true" />
            <span className="ss-pcard-badge material-symbols-outlined" aria-hidden="true">
              sports_soccer
            </span>
          </div>
        </footer>
      </div>
    </article>
  )
}
