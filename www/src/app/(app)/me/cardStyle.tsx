'use client'

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { loadCardStyle, saveCardStyle } from './cardStyleStore'

/**
 * 카드 꾸미기 설정.
 *
 * ⚠️ **아직 서버에 저장되지 않는다.** 계약에 카드를 꾸미는 필드가 없다
 * (미결 paik 3번).
 *
 * 🔴 **앞서 "브라우저 저장도 일부러 안 넣었다"고 적었던 것을 정정한다**
 * (2026-09-04, 사용자 요청). 근거는 "서버가 붙으면 상태가 두 곳에 생긴다"
 * 였는데, 저장이 아예 없으면 **편집기를 닫는 순간 꾸민 것이 전부 사라져**
 * 기능이 성립하지 않았다. 지금은 `cardStyleStore.ts` 한 파일이 그 자리를
 * 맡고, 서버가 생기면 그 파일만 지우면 된다.
 *
 * 🔴 **여기 담긴 이름들이 곧 계약에 요청할 필드 목록**이다. 화면에서 무엇이
 * 필요한지 먼저 굳혀 두면, 규격을 낼 때 짐작으로 정하지 않아도 된다.
 */
export type CardStyle = {
  /** 카드 바탕. */
  bg: string
  /** 워드마크(SUPERSUB) 색. */
  logo: string
  /** 가운데 큰 글자. 비우면 카드에 글자가 없다. */
  text: string
  /** 그 글자의 색. */
  textColor: string
  /**
   * 글자 자리 — 카드 폭 · 높이에 대한 백분율(가운데 기준).
   * 🔴 `PLAYER CARD` 머리글 **아래로만** 갈 수 있다(사용자 요청) — 위로
   *   올라가면 로고와 머리글을 덮는다. 그 하한이 `TEXT_MIN_Y` 다.
   */
  textX: number
  textY: number
  /**
   * 올린 사진. **브라우저 안에만 있다**(파일을 읽은 data URL) — 카드 이미지를
   * 올릴 자리가 계약에 정해져 있지 않아서 서버로 보내지 않는다.
   * `og_image_key` 가 "그 위치에 파일이 아직 없다" 인 것과 같은 자리다.
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
  /** 뒤에 깔리는 자국. `-1` 이면 아무것도 안 깐다. */
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
  text: 'THREE LUNGS',
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

type Ctx = {
  style: CardStyle
  set: (patch: Partial<CardStyle>) => void
  /** 화면의 값만 처음으로 되돌린다 — **저장해 둔 것은 건드리지 않는다.** */
  reset: () => void
  /** 지금 값을 담아 둔다. 실패하면 `false`(사진이 크면 한도를 넘는다). */
  save: () => boolean
}

const CardStyleContext = createContext<Ctx | null>(null)

/**
 * 카드와 편집기가 **같은 값을 본다**. 둘이 화면에서 떨어져 있어서(카드는 선
 * 위, 편집기는 선 아래) 상태를 한쪽이 들고 있을 수가 없다.
 */
export function CardStyleProvider({ children }: { children: React.ReactNode }) {
  const [style, setStyle] = useState<CardStyle>(DEFAULT_CARD_STYLE)

  /* 🔴 담아 둔 값을 **그릴 때 읽지 않는다.** 서버에는 없는 값이라 서버가 그린
     첫 화면과 브라우저가 그린 것이 갈려 하이드레이션이 깨진다. */
  useEffect(() => {
    const saved = loadCardStyle(DEFAULT_CARD_STYLE)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- 위 주석 참고.
    if (saved) setStyle(saved)
  }, [])

  const value = useMemo<Ctx>(
    () => ({
      style,
      set: (patch) => setStyle((prev) => ({ ...prev, ...patch })),
      reset: () => setStyle(DEFAULT_CARD_STYLE),
      save: () => saveCardStyle(style),
    }),
    [style],
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
      set: () => {},
      reset: () => {},
      save: () => false,
    }
  )
}
