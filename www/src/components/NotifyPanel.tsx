'use client'

import { useState } from 'react'
import type { InboxItem, InboxMatch } from '@/lib/useNotifyInbox'

/**
 * 「알림」 글자 아래로 떠오르는 판 — **가리키기만 하면 나온다**(사용자 요청,
 * 2026-09-16). 누르고 들어가는 별도 화면을 만들지 않는다.
 *
 * 🔴 **여기서 바로 수락한다.** 알림을 "가서 보라"는 안내로 두면 화면이 하나
 * 더 필요해지고, 그 화면이 하는 일은 결국 이 줄 하나다 — 상대 팀 정보와
 * 수락 단추가 **같은 줄**에 있어야 한다는 것이 요청의 핵심이다.
 *
 * ⚠️ 목적지 카드(`DestinationCard`)가 서던 자리에 대신 선다. 그래서 자리를
 * 정하는 것은 `.ss-home-nav-card` 그대로이고, 이 파일은 **안쪽만** 그린다.
 */
export default function NotifyPanel({
  items,
  onAcceptMatch,
  onRejectMatch,
  onAcceptContact,
}: {
  items: InboxItem[]
  onAcceptMatch: (item: InboxMatch) => Promise<unknown>
  onRejectMatch: (item: InboxMatch) => Promise<unknown>
  onAcceptContact: (item: Extract<InboxItem, { kind: 'contact' }>) => Promise<unknown>
}) {
  /** 지금 처리 중인 줄 — 두 번 눌러 두 번 보내는 것을 막는다. */
  const [busy, setBusy] = useState<string | null>(null)

  async function run(id: string, fn: () => Promise<unknown>) {
    if (busy) return
    setBusy(id)
    try {
      await fn()
    } finally {
      setBusy(null)
    }
  }

  if (items.length === 0) {
    return (
      <div className="ss-notify" role="status">
        <p className="ss-notify-empty">새 알림이 없습니다</p>
      </div>
    )
  }

  return (
    <div className="ss-notify">
      <ul className="ss-notify-list">
        {items.map((item) =>
          item.kind === 'team-match' ? (
            <li key={item.id} className="ss-notify-row">
              <span className="ss-notify-text">
                {/* 🔴 이름을 못 찾으면 **지어내지 않는다** — 계약이 팀 이름을
                    안 줘서 진짜 백엔드에서는 자주 이쪽이다. */}
                <span className="ss-notify-name">{item.name ?? '상대 팀'}</span>
                <span className="ss-notify-note">
                  {item.region ? `${item.region} · ` : ''}
                  {formatWhen(item.playedAt)} · {item.place}
                </span>
              </span>
              <span className="ss-notify-acts">
                <button
                  type="button"
                  className="ss-notify-act"
                  disabled={busy === item.id}
                  onClick={() => void run(item.id, () => onAcceptMatch(item))}
                >
                  수락하기
                </button>
                <button
                  type="button"
                  className="ss-notify-act ss-notify-act--ghost"
                  disabled={busy === item.id}
                  onClick={() => void run(item.id, () => onRejectMatch(item))}
                >
                  거절
                </button>
              </span>
            </li>
          ) : (
            <li key={item.id} className="ss-notify-row">
              <span className="ss-notify-text">
                <span className="ss-notify-name">지인 신청</span>
                <span className="ss-notify-note">{item.note ?? '수락하면 서로 지인이 됩니다'}</span>
              </span>
              <span className="ss-notify-acts">
                <button
                  type="button"
                  className="ss-notify-act"
                  disabled={busy === item.id}
                  onClick={() => void run(item.id, () => onAcceptContact(item))}
                >
                  수락하기
                </button>
              </span>
            </li>
          ),
        )}
      </ul>
    </div>
  )
}

/**
 * 언제 하는 경기인가 — 목록에서는 요일 · 시각이면 충분하다.
 *
 * 🔴 **못 읽는 값을 그대로 쓰지 않는다.** 서버 시각 형식이 달라지면
 * `Invalid Date` 가 화면에 찍힌다 — 그럴 바에 원문을 보여 준다.
 */
function formatWhen(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${day} ${p(d.getHours())}:${p(d.getMinutes())}`
}
