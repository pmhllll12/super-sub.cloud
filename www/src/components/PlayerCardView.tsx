import type { PublicPlayerCard } from '@/server/backend'
import CardMark from './CardMark'
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
 * ✅ 가운데 큰 글자는 **`card.tagline`**(CCC 18·35)에서 온다 — 안 정했으면
 * {@link ALIAS} 가 자리 표시로 남는다.
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
// `tagline`을 안 정한 카드가 보일 자리 표시. `cardStyle.tsx`의 편집 초안도
// 같은 값으로 시작한다(export 하는 이유) — 편집기를 열었을 때 지금 카드에
// 보이는 것과 다른 글자가 뜨면 안 된다.
export const ALIAS = 'THREE LUNGS'

/**
 * 카드를 꾸민 값. **안 넘기면 `card.style` 을 쓴다**(꾸민 적이 없으면 그것도
 * 없어서 지금까지와 똑같이 그려진다) — 편집기(`StyledCard`)만 **아직 저장
 * 안 한 초안**을 보여주려고 이 prop 을 직접 넘긴다.
 *
 * 🔴 색은 **CSS 변수로** 얹는다(`--ss-pcard-bg` 등). 그 변수를 카드 안의
 * 여러 규칙이 이미 읽고 있어서, 하나만 갈면 글 · 테두리 · 워드마크가 함께
 * 따라온다 — 자리마다 색을 칠하면 빠뜨린 곳이 반드시 남는다.
 */
type CardLook = {
  bg?: string
  logo?: string
  text?: string
  textColor?: string
  textX?: number
  textY?: number
  photo?: string | null
  photoScale?: number
  photoX?: number
  photoY?: number
  mode?: 'cutout' | 'full'
  brush?: number
  brushColor?: string
  brushScale?: number
  brushX?: number
  brushY?: number
}

/** `card.style` (서버, 스네이크) → `CardLook` (이 파일, 캐멀). 사진 관련은
 * 서버에 없으므로 안 채운다 — 호출부가 `??` 로 기본값을 따로 잡는다. */
function styleToLook(style: NonNullable<PublicPlayerCard['style']>): CardLook {
  return {
    bg: style.bg,
    logo: style.logo,
    textColor: style.text_color,
    textX: style.text_x,
    textY: style.text_y,
    brush: style.brush,
    brushColor: style.brush_color,
    brushScale: style.brush_scale,
    brushX: style.brush_x,
    brushY: style.brush_y,
  }
}

export default function PlayerCardView({
  card,
  look,
}: {
  card: PublicPlayerCard
  look?: CardLook
}) {
  // 🔴 **`look` 이 없어도 `card.style` 이 있으면 꾸며진 대로 그린다.** 이게
  // 없으면 저장은 되는데 편집기 밖(내 프로필 평소 보기 · 공개 카드 링크)
  // 에서는 안 보이는 반쪽짜리가 된다 — 저장한 보람이 없어진다.
  const effective = look ?? (card.style ? styleToLook(card.style) : undefined)
  const alias = look?.text ?? card.tagline ?? ALIAS
  const photo = effective?.photo ?? '/player_cutout.png'
  const full = effective?.mode === 'full'
  return (
    <article
      className="ss-pcard"
      aria-label={card.user.nickname}
      data-photo={full ? 'full' : undefined}
      data-text-free={effective ? 'true' : undefined}
      style={
        effective
          ? ({
              '--ss-pcard-bg': effective.bg,
              '--ss-pcard-fg': effective.textColor,
              '--ss-pcard-text-x': `${effective.textX ?? 50}%`,
              '--ss-pcard-text-y': `${effective.textY ?? 34}%`,
              '--ss-pcard-photo-scale': effective.photoScale ?? 1,
              '--ss-pcard-photo-x': `${effective.photoX ?? 0}%`,
              '--ss-pcard-photo-y': `${effective.photoY ?? 0}%`,
              '--ss-card-mark-color': effective.brushColor,
              '--ss-card-mark-scale': effective.brushScale ?? 1,
              '--ss-card-mark-x': `${effective.brushX ?? 0}%`,
              '--ss-card-mark-y': `${effective.brushY ?? 0}%`,
            } as React.CSSProperties)
          : undefined
      }
    >
      <div className="ss-pcard-inner">
        {/* 인물 뒤 검은 붓자국. 사람마다 다르되 늘 같은 모양이다 —
            자세한 이유는 PlayerCardBrush 주석 참고.
            🔴 사진을 통째로 까는 모드에서는 그리지 않는다 — 사진 위에 검은
            자국이 얹히면 그림이 더러워 보인다. */}
        {/* 🔴 꾸민 값(저장했거나 편집 중)이 있으면 **고른 자국**이, 아니면
            지금까지의 붓자국이 깔린다. 둘을 같이 그리지 않는다 — 자국이
            겹치면 어느 것을 고른 것인지 알 수 없다. */}
        {effective ? (
          /* 🔴 사진을 통째로 까는 모드에서는 **기본 붓칠만** 뺀다 — 사진 위에
             검은 자국이 얹히면 그림이 더러워 보인다. 다만 사용자가 **고른**
             자국은 그린다: 일부러 얹은 것을 말없이 지우면 안 된다. */
          full && (effective.brush ?? 0) === 0 ? null : (
            <CardMark index={effective.brush ?? 0} seed={card.public_slug} />
          )
        ) : (
          !full && <PlayerCardBrush seed={card.public_slug} />
        )}

        {/* 🔴 사진을 통째로 까는 모드에서는 **글자보다 먼저** 그린다 — 나중에
            그리면 사진이 로고와 머리글을 덮는다. */}
        {full && (
          <div className="ss-pcard-figure" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element -- 위와 같은 이유 */}
            <img src={photo} alt="" decoding="async" />
          </div>
        )}

        <header className="ss-pcard-top">
          {/* 바탕이 연두라 강조색(민트) 워드마크는 묻힌다 — 검게 찍는다. */}
          <BrandMark size={22} color={effective?.logo ?? 'var(--ss-pcard-fg)'} />
          <p className="ss-pcard-kicker">PLAYER CARD</p>
        </header>

        {/* 가운데 큰 별명 — 참고 디자인의 제목 자리. */}
        {/* 글자를 비우면 그리지 않는다 — 빈 <p> 가 남으면 그 자리만큼 인물이
            밀린다. */}
        {alias && <p className="ss-pcard-alias">{alias}</p>}

        {/* 누끼 인물 — 장식이라 스크린리더에서 숨긴다. 아래 절반만
            차지하게 두어(top: 50%) 카드 가운데 위로 넘어가지 않는다. */}
        {!full && (
          <div className="ss-pcard-figure" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element -- 사용자가 고른 그림이라
                크기를 미리 알 수 없다(next/image 는 크기를 요구한다) */}
            <img src={photo} alt="" decoding="async" />
          </div>
        )}

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
