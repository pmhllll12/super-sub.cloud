'use client'

import { createContext, useContext, useMemo, useState } from 'react'
import { apiPatch } from '@/lib/api/client'
import { ALIAS } from '@/components/PlayerCardView'
import type { CardStyleWire, PlayerCard } from '@/server/backend'

/**
 * 카드 꾸미기 설정.
 *
 * ✅ **서버에 저장된다** (CCC 35, 2026-09-11). `PATCH /me/card`의 `style`이
 * 그 자리다 — `bg`·`logo`·`text_color`·`text_x`·`text_y`·`brush`·
 * `brush_color`·`brush_scale`·`brush_x`·`brush_y`(스네이크 표기는 서버
 * 계약, 여기 `CardStyle`은 화면 관례대로 캐멀 표기다. `toWire`/`fromWire`가
 * 그 경계다).
 *
 * 🔴 **`text`(가운데 큰 글자)는 여기 없다.** 이미 있던 `tagline`이 같은
 * 자리였다 — 04-09에 그걸 몰라 `style.text`를 새로 만들었던 것을 이번에
 * 합쳤다. 아래 `tagline`은 그 자리다(자리 이름을 그대로 쓴다 — 다른 개념이
 * 아니라 같은 값의 편집 버퍼다).
 *
 * ⚠️ **사진 관련 넷(`photo`·`photoScale`·`photoX`·`photoY`)과 `mode`는
 * 여전히 서버에 없다.** `og_image_key`가 "규칙은 있는데 파일이 없는" 것과
 * 같은 이유다(저장 위치 미정) — `cardStyleStore.ts` 없이 **이 세션 동안만**
 * 남는다. 새로고침하면 사라지는 것이 지금은 맞는 동작이다.
 */
export type CardStyle = {
  /** 카드 바탕. */
  bg: string
  /** 워드마크(SUPERSUB) 색. */
  logo: string
  /** 가운데 큰 글자(`tagline`)의 색. */
  textColor: string
  /**
   * 글자 자리 — 카드 폭 · 높이에 대한 백분율(가운데 기준).
   * 🔴 `PLAYER CARD` 머리글 **아래로만** 갈 수 있다(사용자 요청) — 위로
   *   올라가면 로고와 머리글을 덮는다. 그 하한이 `TEXT_MIN_Y` 다.
   */
  textX: number
  textY: number
  /**
   * 올린 사진. **브라우저 안에만, 이 세션 동안만 있다**(파일을 읽은 data
   * URL) — 카드 이미지를 올릴 자리가 계약에 정해져 있지 않아서 서버로
   * 보내지 않는다. `og_image_key` 가 "그 위치에 파일이 아직 없다" 인 것과
   * 같은 자리다.
   */
  photo: string | null
  /** 사진 크기(1 이 원래 크기). */
  photoScale: number
  /** 사진 위치 — 카드 폭 · 높이에 대한 백분율. */
  photoX: number
  photoY: number
  /**
   * 사진을 어떻게 놓는가.
   *
   * `cutout` — 지금까지의 모습. 사람만 오려 낸 그림이 **아래 절반**에 서고
   *   위쪽은 바탕색 · 글자의 자리다.
   * `full` — **누끼를 안 딴 사진**을 카드 전체에 깐다(사용자 요청). 오려 내는
   *   수고 없이 카드를 만들 수 있는 길이다.
   */
  mode: 'cutout' | 'full'
  /** 뒤에 깔리는 자국. */
  brush: number
  brushColor: string
  brushScale: number
  brushX: number
  brushY: number
}

/** 글자가 올라갈 수 있는 가장 위 — 이보다 위는 로고와 머리글의 자리다. */
export const TEXT_MIN_Y = 24

/** 지금 카드가 그려지는 모습 그대로 — 아무것도 안 고친 상태가 이 값이다. */
export const DEFAULT_CARD_STYLE: CardStyle = {
  bg: '#91ea92',
  logo: '#0b0b0b',
  textColor: '#0b0b0b',
  // 지금 카드에서 글자가 앉아 있는 자리 그대로.
  textX: 50,
  textY: 34,
  photo: null,
  photoScale: 1,
  photoX: 0,
  photoY: 0,
  mode: 'cutout',
  brush: 0,
  brushColor: '#0b0b0b',
  brushScale: 1,
  brushX: 0,
  brushY: 0,
}

/** 서버 값(있으면) 위에 기본값을 채운다 — 필드가 늘어나도 옛 카드가 화면을 안 깬다. */
function fromWire(wire: CardStyleWire | null | undefined): CardStyle {
  if (!wire) return DEFAULT_CARD_STYLE
  return {
    ...DEFAULT_CARD_STYLE,
    bg: wire.bg,
    logo: wire.logo,
    textColor: wire.text_color,
    textX: wire.text_x,
    textY: wire.text_y,
    brush: wire.brush,
    brushColor: wire.brush_color,
    brushScale: wire.brush_scale,
    brushX: wire.brush_x,
    brushY: wire.brush_y,
  }
}

/** 사진 관련 넷은 서버에 자리가 없다 — 여기서 빠지는 것이 그 경계다. */
function toWire(style: CardStyle): CardStyleWire {
  return {
    bg: style.bg,
    logo: style.logo,
    text_color: style.textColor,
    text_x: style.textX,
    text_y: style.textY,
    brush: style.brush,
    brush_color: style.brushColor,
    brush_scale: style.brushScale,
    brush_x: style.brushX,
    brush_y: style.brushY,
  }
}

type Ctx = {
  style: CardStyle
  /** 가운데 큰 글자의 편집 버퍼 — 저장하면 `tagline` 이 된다. */
  tagline: string
  set: (patch: Partial<CardStyle>) => void
  setTagline: (v: string) => void
  /** 화면의 값만 **공장 기본값**으로 되돌린다 — 저장된 것은 건드리지 않는다. */
  reset: () => void
  /** 지금 값을 서버에 담는다. 실패하면 `false`. */
  save: () => Promise<boolean>
}

const CardStyleContext = createContext<Ctx | null>(null)

/**
 * 카드와 편집기가 **같은 값을 본다**. 둘이 화면에서 떨어져 있어서(카드는 선
 * 위, 편집기는 선 아래) 상태를 한쪽이 들고 있을 수가 없다.
 *
 * 🔴 **초기값을 서버가 준 `card` 에서 채운다.** 예전엔 `localStorage`를
 * 마운트 뒤 `useEffect`로 읽었다(서버 렌더와 갈릴까 봐) — 이제 값의 정본이
 * 서버이고 `card`는 서버 컴포넌트가 이미 들고 있는 값이라, 처음 렌더부터
 * 같은 것을 그린다. 하이드레이션이 갈릴 자리가 없다.
 */
export function CardStyleProvider({
  card,
  children,
}: {
  card: PlayerCard | null
  children: React.ReactNode
}) {
  const [style, setStyle] = useState<CardStyle>(() => fromWire(card?.style))
  // 🔴 안 정했으면 `ALIAS` 자리 표시로 시작한다 — 지금 카드(비편집 화면)에
  // 보이는 것과 편집기를 여는 순간 보이는 것이 달라지면 안 된다.
  const [tagline, setTagline] = useState(() => card?.tagline ?? ALIAS)

  const value = useMemo<Ctx>(
    () => ({
      style,
      tagline,
      set: (patch) => setStyle((prev) => ({ ...prev, ...patch })),
      setTagline,
      reset: () => {
        setStyle(DEFAULT_CARD_STYLE)
        setTagline(ALIAS)
      },
      save: async () => {
        try {
          await apiPatch('/api/me/card', {
            tagline: tagline.trim() || null,
            style: toWire(style),
          })
          return true
        } catch {
          return false
        }
      },
    }),
    [style, tagline],
  )
  return <CardStyleContext.Provider value={value}>{children}</CardStyleContext.Provider>
}

/**
 * 🔴 provider 밖에서도 **죽지 않는다.** 카드는 편집 모드가 아닐 때도 그려지고
 * (홈 헤더 · 스쿼드 판 · 공개 카드 화면), 그때는 기본값이 맞다.
 */
export function useCardStyle(): Ctx {
  return (
    useContext(CardStyleContext) ?? {
      style: DEFAULT_CARD_STYLE,
      tagline: '',
      set: () => {},
      setTagline: () => {},
      reset: () => {},
      save: async () => false,
    }
  )
}
