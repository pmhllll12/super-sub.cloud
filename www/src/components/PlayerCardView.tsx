import type { PublicPlayerCard } from '@/server/backend'
import BrandMark from './ui/BrandMark'

/**
 * 세로 포스터형 선수 카드 — 참고 디자인(MOJO 시즌 카드)의 짜임이다.
 * 검은 테두리 안에 **흰 카드**가 들어 있고, 위에서부터 워드마크 · 작은
 * 머리글 · 굵은 검은 이름이 쌓이며 맨 아래에 형광 알약과 검은 막대 ·
 * 원형 배지가 온다.
 *
 * 🔴 **인물 사진을 넣지 않는다.** 참고 디자인의 중앙에는 선수 사진이
 * 있지만 우리에겐 그 자리에 넣을 것이 없다 — 계약(api-contract.md)에
 * 사용자 사진 필드가 아예 없고(`og_image_key` 는 서버가 만드는 공유
 * 미리보기 이미지의 키다), 한때 `public/player_mono.jpg` 라는 스톡
 * 사진을 깔아 뒀는데 **모든 사람의 카드에 같은 남의 사진**이 박히는
 * 꼴이었다. 사진 필드가 계약에 생기면 그때 이 자리를 연다.
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
    <article className="ss-pcard">
      <div className="ss-pcard-inner">
        <header className="ss-pcard-top">
          <BrandMark size={22} color="var(--ss-pcard-fg)" />
          <p className="ss-pcard-kicker">PLAYER CARD</p>
        </header>

        <h1 className="ss-pcard-name">{card.user.nickname}</h1>

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
