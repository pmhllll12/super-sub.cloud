'use client'

import { useState } from 'react'

/** 거름망 한 축. 무엇으로 거르는지는 **쓰는 쪽**이 정한다. */
export type FilterField = {
  /** 어느 축인지 가리는 이름 — 열려 있는 축을 기억할 때 쓴다. */
  key: string
  /** 접힌 단추에 보이는 이름(아직 안 골랐을 때). */
  label: string
  /** 고른 것을 사람이 읽는 말로. 있으면 이름 대신 이것이 보인다. */
  value?: string | null
  /** 고를 것들. `custom` 이 있으면 안 쓴다. */
  options?: { value: string; label: string }[]
  /** 지금 고른 값(알약을 켜는 데 쓴다). */
  picked?: string | null
  /** 고르면 부른다. 같은 것을 다시 고르면 `null` 이 온다(= 전체). */
  onPick?: (v: string | null) => void
  /** 고르는 것이 아니라 **직접 적는** 축(가격)에 쓴다. */
  custom?: React.ReactNode
}

/**
 * 목록 위의 **거름망 한 줄** — 코치 목록과 상품 목록이 같이 쓴다.
 *
 * 참고한 짜임(사용자 제시): 왼쪽에 `Filters :`, 그 옆으로 접힌 단추가 늘어서고,
 * 오른쪽 끝에 정렬.
 *
 * 🔴 고를 것을 **떠 있는 목록으로 띄우지 않는다**(사용자 요청). 브라우저가
 * 그리는 목록(`select`)은 OS 모양 그대로라 이 화면과 따로 놀았다. 대신 **줄 바로
 * 아래가 열리면서** 아래 실선이 그만큼 부드럽게 내려가고, 그 자리에 이 화면이
 * 이미 쓰는 알약(`.ss-shot-sport`)이 놓인다 — 열린 것이 어디에 딸린 것인지가
 * 자리로 읽히고, 조작도 새로 배울 것이 없다.
 *
 * 🔴 한 번에 하나만 열린다. 둘 이상 열리면 아래로 계속 밀려 목록이 화면 밖으로
 * 나간다.
 */
export function FilterBar({
  fields,
  /** 오른쪽 끝 — 정렬처럼 거르는 것이 아닌 조작. */
  end,
}: {
  fields: FilterField[]
  end?: React.ReactNode
}) {
  const [openKey, setOpenKey] = useState<string | null>(null)
  const open = fields.find((f) => f.key === openKey) ?? null

  return (
    <div className="ss-filterbar-wrap">
      <div className="ss-filterbar">
        {/* 참고한 짜임 그대로 `Filters :` 다(사용자 요청) — 쌍점 앞을 띄운다. */}
        <span className="ss-filterbar-title">Filters :</span>

        {fields.map((f) => (
          <button
            key={f.key}
            type="button"
            className="ss-filterfield-input"
            data-on={Boolean(f.value)}
            aria-expanded={openKey === f.key}
            // 같은 것을 다시 누르면 접힌다 — 여는 것과 닫는 것이 한 자리다.
            onClick={() => setOpenKey(openKey === f.key ? null : f.key)}
          >
            {f.value ?? f.label}
            <span className="ss-filterfield-caret" aria-hidden="true" />
          </button>
        ))}

        {end ? <div className="ss-filterbar-end">{end}</div> : null}
      </div>

      {/* 🔴 열리고 닫히는 자리. 높이를 **격자 칸(0fr ↔ 1fr)** 으로 여닫는다 —
          `max-height` 로 하면 넉넉한 값을 미리 찍어 둬야 하고, 그 값이 실제
          높이와 다른 만큼 여는 동안 빨라졌다 느려진다. 격자는 내용이 얼마든
          알아서 맞는다. */}
      <div className="ss-filterdrawer" data-open={open !== null}>
        <div className="ss-filterdrawer-inner">
          <div className="ss-filterdrawer-body">
            {open?.custom ?? (
              <div className="ss-filterdrawer-options" role="group" aria-label={open?.label}>
                {open?.options?.map((o) => (
                  <button
                    key={o.value}
                    type="button"
                    className="ss-shot-sport"
                    aria-pressed={open.picked === o.value}
                    // 같은 것을 다시 누르면 풀린다 — 안 고른 상태가 "전체" 다.
                    onClick={() => open.onPick?.(open.picked === o.value ? null : o.value)}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/** 오른쪽 끝의 정렬. 거르는 것이 아니라 **줄 세우는 것**이라 모양을 달리한다. */
export function SortSelect<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
}) {
  return (
    <span className="ss-filterfield ss-sortfield">
      <span className="material-symbols-outlined" aria-hidden="true">
        swap_vert
      </span>
      <select
        className="ss-filterfield-input"
        aria-label="정렬"
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            정렬: {o.label}
          </option>
        ))}
      </select>
    </span>
  )
}
