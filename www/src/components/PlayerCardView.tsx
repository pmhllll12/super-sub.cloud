import type { PublicPlayerCard } from '@/server/backend'
import PlayerCardBrush from './PlayerCardBrush'
import BrandMark from './ui/BrandMark'

/**
 * 세로 포스터형 선수 카드 — 참고 디자인(MOJO 시즌 카드)의 짜임이다.
 * 검은 테두리 안에 **흰 카드**가 들어 있고, 위에서부터 워드마크 · 작은
 * 머리글 · 큰 별명이 오고, 아래 절반을 누끼 인물이 채운다.
 *
 * 인물은 `public/player_cutout.png` — 배경이 검던 원본에서 사람만 떼어
 * 낸 것이다(만든 과정은 커밋 메시지 참고). **카드 세로 가운데 위로는
 * 올라오지 않는다** — 위쪽 절반은 워드마크와 머리글의 자리다.
 *
 * ⚠️ 가운데 큰 글자({@link ALIAS})는 **아직 붙박이 문구다.** 계약
 * (api-contract.md)에 별명 필드가 없어서 서버에서 받아올 데가 없다 —
 * 화면 모양을 먼저 잡아 두는 자리 표시다. 필드가 생기면 card 에서
 * 받아 쓰고 이 상수를 지운다.
 *
 * 🔴 카드에 **닉네임도 호칭도 글자로 적지 않는다.** 인물과 별명이
 * 가운데를 차지해 자리가 없다. 다만 카드가 누구 것인지, 무슨 호칭을
 * 받았는지는 읽어 주는 기계에 남아야 하므로 article 의 이름(aria-label)과
 * 화면 밖 목록(sr-only)으로 남긴다.
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
// 계약에 별명 필드가 생기면 지운다 — 위 주석 참고.
const ALIAS = 'THREE LUNGS'

export default function PlayerCardView({ card }: { card: PublicPlayerCard }) {
  return (
    <article className="ss-pcard" aria-label={card.user.nickname}>
      <div className="ss-pcard-inner">
        {/* 인물 뒤 검은 붓자국. 사람마다 다르되 늘 같은 모양이다 —
            자세한 이유는 PlayerCardBrush 주석 참고. */}
        <PlayerCardBrush seed={card.public_slug} />

        <header className="ss-pcard-top">
          {/* 바탕이 연두라 강조색(민트) 워드마크는 묻힌다 — 검게 찍는다. */}
          <BrandMark size={22} color="var(--ss-pcard-fg)" />
          <p className="ss-pcard-kicker">PLAYER CARD</p>
        </header>

        {/* 가운데 큰 별명 — 참고 디자인의 제목 자리. */}
        <p className="ss-pcard-alias">{ALIAS}</p>

        {/* 누끼 인물 — 장식이라 스크린리더에서 숨긴다. 아래 절반만
            차지하게 두어(top: 50%) 카드 가운데 위로 넘어가지 않는다. */}
        <div className="ss-pcard-figure" aria-hidden="true">
          {/* eslint-disable-next-line @next/next/no-img-element -- 카드 장식용 고정 이미지 */}
          <img src="/player_cutout.png" alt="" decoding="async" />
        </div>

        {/* 참고 디자인 맨 아래의 검은 막대 · 형광 알약 · 원형 배지는
            전부 뺐다(사용자 요청) — 카드 얼굴에는 워드마크 · 머리글 ·
            별명 · 인물만 남는다.

            받은 호칭은 화면에 그리지 않지만 목록으로는 남긴다. 카드에
            무엇이 담겼는지 읽어 주는 기계는 알 수 있어야 한다. */}
        <h2 className="sr-only">호칭</h2>
        <ul className="sr-only">
          {card.titles.map((t) => (
            <li key={t.code}>
              {t.category} {t.label}
            </li>
          ))}
        </ul>
      </div>
    </article>
  )
}
