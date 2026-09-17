'use client'

import { useEffect, useState } from 'react'
import InviteSquad from '@/components/InviteSquad'
import type { InboxInvitation, InboxItem, InboxMatch } from '@/lib/useNotifyInbox'

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
  onAcceptInvitation,
  onRejectInvitation,
}: {
  items: InboxItem[]
  onAcceptMatch: (item: InboxMatch) => Promise<unknown>
  onRejectMatch: (item: InboxMatch) => Promise<unknown>
  onAcceptContact: (item: Extract<InboxItem, { kind: 'contact' }>) => Promise<unknown>
  onAcceptInvitation?: (item: InboxInvitation) => Promise<unknown>
  onRejectInvitation?: (item: InboxInvitation) => Promise<unknown>
}) {
  /** 지금 처리 중인 줄 — 두 번 눌러 두 번 보내는 것을 막는다. */
  const [busy, setBusy] = useState<string | null>(null)
  /** 판을 펼쳐 둔 초대 — 한 번에 하나만 편다(판이 커서 둘이 겹치면 읽기 나쁘다). */
  const [peek, setPeek] = useState<string | null>(null)

  /**
   * 🔴 **판을 열면 뒤의 판들을 흐린다**(사용자 요청, 2026-09-17). 초대 판은
   * 알림에서 왼쪽으로 나오는데 그 자리에 「AI 추천」·「지인 찾기」 판이 **겹쳐
   * 있을 때가 있다.**
   *
   * 그 둘은 헤더가 아니라 **페이지 쪽 조각**이라 props 로 넘길 길이 없다 —
   * 문서 뿌리에 표식만 걸고 흐리는 것은 CSS 가 맡는다(`globals.css` 의
   * 「겹친 판 흐리기」). 부모를 거쳐 신호를 내리려면 `SquadPanel` 까지
   * 줄줄이 고쳐야 하고, 그건 이 한 가지 때문에 치르기엔 큰 값이다.
   *
   * 🔴 **정리에서 반드시 걷는다** — 안 걷으면 알림 판이 닫힌 뒤에도 화면이
   * 흐린 채로 남는다.
   */
  useEffect(() => {
    if (!peek) return
    const root = document.documentElement
    root.dataset.ssPeek = 'true'
    return () => {
      delete root.dataset.ssPeek
    }
  }, [peek])

  /**
   * 알림 판이 열려 있는 **그 자체**의 표식. 이 조각은 판이 열렸을 때만
   * 붙으므로, 붙어 있는 동안이 곧 열려 있는 동안이다.
   *
   * 🔴 **초대 판과 범위가 다르다**(사용자 요청, 2026-09-17) — 알림 판만
   * 열렸을 때는 그 아래 깔린 **「지인 찾기」만** 물리고, 초대 판까지 열면
   * 그 판이 덮는 **둘 다** 물린다.
   */
  useEffect(() => {
    const root = document.documentElement
    root.dataset.ssNotify = 'true'
    return () => {
      delete root.dataset.ssNotify
    }
  }, [])

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
          ) : item.kind === 'invitation' ? (
            <li key={item.id} className="ss-notify-row ss-notify-row--invite">
              <span className="ss-notify-text">
                {/* 🔴 팀 이름을 모르면 **지어내지 않는다** — 옛 응답이면 null 이다. */}
                <span className="ss-notify-name">{item.teamName ?? '어느 팀'}</span>
                <span className="ss-notify-note">
                  {item.teamRegion ? `${item.teamRegion} · ` : ''}
                  팀에 초대했습니다
                </span>
                {/* 🔴 **자리를 안 정한 초대가 정상이다** — 그때는 이 줄이 없다.
                    이름은 서버가 준 `position_label` 이고, 약칭으로 지어내지
                    않는다(종목마다 같은 약칭이 다른 뜻이다). */}
                {item.posLabel ? (
                  <span className="ss-notify-note ss-notify-pos">
                    {item.posLabel}
                    {item.posCode ? `(${item.posCode})` : ''}로 부릅니다
                  </span>
                ) : null}
                {/* 스쿼드를 아직 안 만든 팀이면 슬러그가 없다 — 그것도 정상이다. */}
                {item.squadSlug === null ? (
                  <span className="ss-notify-note">아직 판이 없습니다</span>
                ) : null}
              </span>
              <span className="ss-notify-acts">
                {item.squadSlug !== null ? (
                  <button
                    type="button"
                    className="ss-notify-act ss-notify-act--ghost"
                    aria-expanded={peek === item.id}
                    onClick={() => setPeek(peek === item.id ? null : item.id)}
                  >
                    {peek === item.id ? '스쿼드 닫기' : '스쿼드'}
                  </button>
                ) : null}
                <button
                  type="button"
                  className="ss-notify-act"
                  disabled={busy === item.id}
                  onClick={() => void run(item.id, async () => onAcceptInvitation?.(item))}
                >
                  수락하기
                </button>
                <button
                  type="button"
                  className="ss-notify-act ss-notify-act--ghost"
                  disabled={busy === item.id}
                  onClick={() => void run(item.id, async () => onRejectInvitation?.(item))}
                >
                  거절
                </button>
              </span>
              {/* 🔴 **펼친 줄에서만 그린다** — 목록을 그릴 때 줄마다 판을 읽으면
                  열지도 않은 판을 초대 수만큼 부르게 된다. */}
              {peek === item.id && item.squadSlug !== null ? (
                <InviteSquad slug={item.squadSlug} teamName={item.teamName ?? "초대한 팀"} posCode={item.posCode} />
              ) : null}
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
