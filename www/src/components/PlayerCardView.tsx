import type { PublicPlayerCard } from '@/server/backend'
import BrandMark from './ui/BrandMark'

/**
 * 세로 포스터형 선수 카드 — 참고 디자인(MOJO 시즌 카드)의 짜임을 따른다:
 * 위에 워드마크와 작은 머리글, 그 아래 이름을 크게, 인물 사진이 이름을
 * 살짝 밀고 올라오고, 맨 아래 띠에 받은 호칭이 알약으로 놓인다.
 *
 * 🔴 **수치를 그리지 않는다** (계약서 4절 / 부록 D.5).
 * 점수 · 등급 · 별점 · 진행률 바를 여기에 넣지 않는다. DB 설계가
 * `player_card` 에 능력치 컬럼을 아예 두지 않는 방식으로 이걸 막아 뒀는데,
 * 화면에서 되살아나면 그 설계가 통째로 무의미해진다.
 * titles 는 **받은 것만** 온다 — 미달 표식을 만들지 않는다.
 *
 * 공유 링크(/c/{slug})가 그대로 쓰는 화면이라, 카드 한 장만으로 무엇을
 * 보는 건지 알 수 있어야 한다 — 그래서 워드마크가 카드 안에 있다.
 */
export default function PlayerCardView({ card }: { card: PublicPlayerCard }) {
  return (
    <article className="ss-pcard">
      <header className="ss-pcard-top">
        <BrandMark size={18} />
        <p className="ss-pcard-kicker">PLAYER CARD</p>
      </header>

      <h1 className="ss-pcard-name">{card.user.nickname}</h1>

      {/* 인물 사진 — 장식이라 스크린리더에서 숨긴다. 아래로 갈수록 카드
          바닥색에 잦아들게 해서 사진의 아랫변이 선으로 보이지 않게 한다
          (FigureBackground 와 같은 방식). */}
      <div className="ss-pcard-figure" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element -- 카드 장식용 고정 이미지 */}
        <img src="/player_mono.jpg" alt="" decoding="async" />
      </div>

      <footer className="ss-pcard-foot">
        <h2 className="ss-pcard-foot-label">호칭</h2>
        {card.titles.length === 0 ? (
          <p className="ss-pcard-empty">아직 받은 호칭이 없습니다.</p>
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
      </footer>
    </article>
  )
}
