'use client'

import { createContext, useContext, useMemo, useState } from 'react'
import { ApiCallError, apiPatch } from '@/lib/api/client'
import { ALIAS, aliasOf } from '@/components/PlayerCardView'
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
 * 🔴 **정정 (2026-09-18, 사용자 요청): 사진도 저장된다.** 앞서 여기에
 * "사진 관련 넷과 `mode` 는 여전히 서버에 없다 — 이 세션 동안만 남는다"고
 * 적어 두었는데, 자리를 냈다(계약 3-5절).
 *
 *   `photoKey`  — **S3 키**. 이것이 서버로 가는 값이다
 *   `photo`     — **그려 줄 주소**. 서버가 준 `photo_url`(사전 서명)이거나,
 *                 방금 고른 사진의 미리보기다. **서버로 안 간다**
 *
 * 🔴 둘을 가른 이유: 그림 자체를 `style` 에 담으면 카드를 읽는 모든 응답에
 * 사진이 실린다 — 스쿼드 판 하나가 자리마다 카드를 부른다.
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
   * **그려 줄 사진 주소.** 서버가 준 `photo_url`(사전 서명, 유효 시간 있음)
   * 이거나, 방금 고른 사진의 미리보기(`blob:`)다.
   *
   * 🔴 **이 값은 서버로 안 간다** — `toWire` 가 안 싣는다. 서버로 가는 것은
   * 아래 `photoKey` 하나다.
   */
  photo: string | null
  /**
   * **S3 키** — 서버에 저장되는 값(`style.photo_key`).
   *
   * 🔴 `photo` 는 있는데 이것이 `null` 이면 **아직 안 올라갔다**는 뜻이다
   * (고르자마자 미리보기부터 뜨고 업로드는 그다음이다). 그 상태로 저장하면
   * 사진이 안 남으므로, 편집기가 올리기가 끝난 뒤에 이 값을 채운다.
   */
  photoKey: string | null
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
  photoKey: null,
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

/**
 * **처음 만든 카드의 모습**(사용자 지정, 2026-09-19) — 「카드 만들기」 직후 이
 * 값으로 한 번 저장해 둔다(`saveFirstLook`). 그 뒤로 바꾸는 것은 사용자 몫이다.
 * 🔴 `DEFAULT_CARD_STYLE`(아무것도 안 고친 상태) 자체를 바꾸지 **않은** 이유 —
 * 그러면 이미 카드가 있으면서 한 번도 안 꾸민 사람들의 카드가 말없이 바뀐다.
 * 붓은 「오려낸 X」(`MARKS` 12번) · 검정 · 1.4배 · 좌우 6% · 위아래 35%.
 */
export const FIRST_CARD_STYLE: CardStyle = {
  ...DEFAULT_CARD_STYLE,
  brush: 12,
  brushColor: '#000000',
  brushScale: 1.4,
  brushX: 6,
  brushY: 35,
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
    /* 🔴 **없을 수 있다** — 배포 전 실서버는 이 다섯을 아직 안 보낸다.
       그때는 기본값으로 떨어진다(타입이 선택인 이유). */
    photoKey: wire.photo_key ?? null,
    photoScale: wire.photo_scale ?? DEFAULT_CARD_STYLE.photoScale,
    photoX: wire.photo_x ?? DEFAULT_CARD_STYLE.photoX,
    photoY: wire.photo_y ?? DEFAULT_CARD_STYLE.photoY,
    mode: wire.mode ?? DEFAULT_CARD_STYLE.mode,
  }
}

/**
 * 🔴 **`photo` 는 여기서 빠진다** — 그것은 그려 줄 주소(사전 서명이거나
 * `blob:`)라 저장할 값이 아니다. 서버로 가는 것은 `photo_key` 다.
 */
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
    photo_key: style.photoKey,
    photo_scale: style.photoScale,
    photo_x: style.photoX,
    photo_y: style.photoY,
    mode: style.mode,
  }
}

/**
 * **사진 칸을 뺀 옛 모양** — 배포 전 서버가 받던 아홉 칸.
 *
 * 🔴 **`toWire` 에서 지우는 방식으로 만든다.** 아홉을 손으로 다시 적으면
 * 나중에 칸이 하나 늘 때 여기만 빠져서, **옛 서버로 떨어진 저장만 조용히
 * 값을 잃는다.**
 */
function toLegacyWire(style: CardStyle): Omit<
  CardStyleWire,
  'photo_key' | 'photo_scale' | 'photo_x' | 'photo_y' | 'mode'
> {
  const { photo_key, photo_scale, photo_x, photo_y, mode, ...rest } = toWire(style)
  void photo_key
  void photo_scale
  void photo_x
  void photo_y
  void mode
  return rest
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
 * 갓 만든 카드에 {@link FIRST_CARD_STYLE} 을 저장한다. 편집기 `save` 와 같은 길 —
 * 옛 서버가 사진 칸 때문에 422 면 사진 칸 없이 한 번 더 보낸다.
 * 🔴 **실패해도 던지지 않는다** — 카드는 이미 생겼다. 모습만 기본으로 남을 뿐이다.
 * 🔴 **글자(`tagline`)도 같이 싣는다.** `style` 만 저장하면 「꾸민 적이 있는데 글자가
 * 비었다 = 일부러 지웠다」(`aliasOf`)로 읽혀 **THREE LUNGS 가 사라진다**(헤드리스로 겪음).
 */
export async function saveFirstLook(): Promise<void> {
  try {
    await apiPatch('/api/me/card', { tagline: ALIAS, style: toWire(FIRST_CARD_STYLE) })
  } catch (err) {
    if (!(err instanceof ApiCallError) || err.status !== 422) return
    await apiPatch('/api/me/card', { tagline: ALIAS, style: toLegacyWire(FIRST_CARD_STYLE) }).catch(
      () => {},
    )
  }
}

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
  /* 🔴 **그려 줄 주소는 `card.photo_url` 에서 온다** — `style` 에는 키만
     있고, 그 키로 서명한 주소를 서버가 따로 실어 준다. 여기서 안 채우면
     새로고침한 뒤 사진이 사라진 것처럼 보인다(키는 남아 있는데 그릴 주소가
     없어서다). */
  const [style, setStyle] = useState<CardStyle>(() => ({
    ...fromWire(card?.style),
    photo: card?.photo_url ?? null,
  }))
  // 🔴 **지금 카드에 보이는 그 글자로** 시작한다 — 편집기를 여는 순간 다른
  // 글자가 뜨면 안 된다. 그래서 `aliasOf` 를 같이 쓴다: 일부러 비워 둔
  // 사람에게는 빈 칸이, 한 번도 안 꾸민 사람에게는 자리 표시가 온다.
  const [tagline, setTagline] = useState(() => (card ? aliasOf(card) : ALIAS))

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
        const body = { tagline: tagline.trim() || null, style: toWire(style) }
        try {
          await apiPatch('/api/me/card', body)
          return true
        } catch (err) {
          /* 🔴 **옛 서버는 사진 칸을 받으면 422 다.** `CardStyleSchema` 가
             `extra="forbid"` 라, 아직 배포 안 된 서버가 `photo_key`·`mode` 를
             받으면 **카드 저장이 통째로 막힌다** — 사진뿐 아니라 한 줄·색·
             붓자국까지.

             배포는 「백엔드 먼저」가 맞지만 **자동으로 그렇게 되지 않는다**:
             main 에 머지하면 `www`(Vercel)는 바로 나가고 백엔드는 이미지만
             빌드된 뒤 사람이 k3s 에 롤아웃한다. 그 사이 몇 분을 여기서
             버틴다 — 사진은 못 담아도 **나머지는 저장된다.**

             🔴 **422 만 다시 보낸다.** 401·403·500 은 사진과 무관한 실패라,
             다시 보내면 같은 실패를 두 번 겪고 사용자만 기다린다.
             🔴 배포가 끝나면 이 길은 **아예 안 탄다.** 나중에 걷어도 된다. */
          if (!(err instanceof ApiCallError) || err.status !== 422) return false
          try {
            await apiPatch('/api/me/card', { ...body, style: toLegacyWire(style) })
            return true
          } catch {
            return false
          }
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
