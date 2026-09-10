'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import MiniPitch from '@/components/MiniPitch'
import type { MatchTeam, MyTeamSummary } from '@/lib/teamMatch'
import type { PublicPlayerCard } from '@/server/backend'

/**
 * **경기가 잡혔다** — 상대 팀장이 수락한 뒤 뜨는 전체 화면 팝업(사용자 요청,
 * 2026-09-10).
 *
 * 경기장 사진 위에 가운데는 **언제 · 어디서 · 누구와**, 양옆은 **두 팀의
 * 스쿼드 판**이 선다. × 를 누르면 닫히고 홈이 그대로 남는다.
 *
 * 🔴 **화면을 떠나지 않는다**(사용자 결정) — 새 경로로 보내면 홈을 떠나고,
 * 돌아올 길과 뒤로 가기까지 설계해야 한다. 팝업이면 닫는 것이 곧 되돌리기다.
 *
 * 🔴 **`document.body` 로 내보낸다(portal).** 이 조각은 스쿼드 판 안에서
 * 그려지는데, 그 위의 `.ss-home-stage` 가 `z-index: 10` 으로 **쌓임 맥락**을
 * 만든다 — 그 안에서 z 를 아무리 올려도 헤더(`z-20`)와 로그아웃 줄
 * (`z-index: 20`)을 못 넘는다. 실제로 그 둘이 팝업 위로 비쳐 나왔다
 * (사용자 지적, 2026-09-10). 맥락 밖으로 나가야 화면을 온전히 덮는다.
 *
 * 🔴 **덮는 것이 이 판의 일이다** — 「경기가 잡혔다」만 보여 주는 자리라
 * 홈의 메뉴 · 로그아웃이 같이 보이면 무엇을 보는 화면인지 흐려진다.
 */

/**
 * 내려가는 데 걸리는 시간 — 🔴 **globals.css 의 `ss-mw-out` 과 같아야 한다.**
 * 짧으면 다 내려가기 전에 사라지고, 길면 이미 없어진 자리를 붙들고 있는다.
 */
const EXIT_MS = 620

/** `2026-09-20T10:00:00` → `9월 20일 토요일 10:00`. */
function whenText(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${day}요일 ${p(d.getHours())}:${p(d.getMinutes())}`
}

export default function MatchWaiting({
  us,
  them,
  myCard = null,
  onClose,
  onCancel,
}: {
  us: MyTeamSummary
  them: MatchTeam
  /** 내 선수 카드 — 우리 판의 내 자리에 진짜 카드를 그린다. */
  myCard?: PublicPlayerCard | null
  /** 판을 접는다 — **경기는 그대로다**(×·Esc). */
  onClose: () => void
  /**
   * 잡힌 경기를 **무른다** — 닫기와 다른 일이다.
   * 🔴 안 주면 취소 단추를 아예 안 그린다 — 눌러도 아무 일이 없으면 안 된다.
   */
  onCancel?: () => void
}) {
  /**
   * 내려가는 중인가 — 🔴 **아직 DOM 에 있어야 한다.** 누르자마자 지우면
   * 내려가는 것을 아무도 못 본다(추천 판이 같은 이유로 같은 것을 한다).
   */
  const [leaving, setLeaving] = useState(false)
  /**
   * 「경기 취소」를 눌러 **한 번 더 묻는 중**인가.
   *
   * 🔴 **곧바로 취소하지 않는다.** 되돌릴 수 없는 일이라 그 자리에서 다시
   * 묻는다 — `window.confirm` 은 안 쓴다(이 사이트는 제 판을 그려 왔고,
   * 그쪽은 시험에서도 못 누른다. 영상 지우기가 같은 방식이다).
   */
  const [confirming, setConfirming] = useState(false)
  const timer = useRef(0)

  /**
   * 내려보내고, **다 내려간 뒤에** 부모에게 알린다.
   *
   * 🔴 닫기와 취소가 같은 길로 나가되 **부르는 것이 다르다** — 취소는
   * 경기를 무르는 일이라 부모가 「내 경기」에서도 빼야 한다.
   */
  const leave = useCallback(
    (done: () => void) => {
      // 두 번 눌러도 한 번만 — 타이머가 겹치면 먼저 것이 지워지지 않는다.
      if (timer.current) return
      setLeaving(true)
      timer.current = window.setTimeout(done, EXIT_MS)
    },
    [],
  )
  const close = useCallback(() => leave(onClose), [leave, onClose])

  // 도중에 사라지면 타이머도 거둔다 — 없는 것에 대고 부르면 안 된다.
  useEffect(() => () => clearTimeout(timer.current), [])

  /* 🔴 **Esc 로도 닫힌다.** × 하나뿐이면 자판만 쓰는 사람이 화면에 갇힌다 —
     판의 추천 창이 같은 이유로 같은 것을 한다. */
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [close])

  // 화면에 그려질 때는 늘 브라우저다(누른 뒤에만 생긴다) — 그래도 지키고 본다.
  if (typeof document === 'undefined') return null

  return createPortal(
    /* 🔴 `role="dialog"` + `aria-modal` — 뒤의 홈이 그대로 살아 있으므로
       낭독기에 "지금은 이 판이 앞에 있다"를 알려야 한다. */
    <div
      className="ss-mw"
      data-leaving={leaving ? 'true' : undefined}
      role="dialog"
      aria-modal="true"
      aria-label="경기가 잡혔습니다"
    >
      {/* 사진은 배경이라 낭독기에서 숨긴다. 🔴 `<img>` 가 아니라 CSS 배경이다 —
          글자가 그 위에 얹히므로 어둡게 덮는 층이 함께 있어야 한다. */}
      <div className="ss-mw-bg" aria-hidden="true" />

      <button type="button" className="ss-mw-close" onClick={close} aria-label="닫기">
        <span className="material-symbols-outlined" aria-hidden="true">
          close
        </span>
      </button>

      <div className="ss-mw-body">
        <MiniPitch team={us.name} players={us.squad} side="us" myCard={myCard} />

        <div className="ss-mw-mid">
          <p className="ss-mw-when">{whenText(them.playedAt)}</p>
          <p className="ss-mw-where">{them.place}</p>
          <p className="ss-mw-vs">
            <span>{us.name}</span>
            <em>VS</em>
            <span>{them.name}</span>
          </p>
          {/* ⚠️ 지어낸 수락이라는 것을 숨기지 않는다 — 숨기면 진짜로 잡힌 줄 안다. */}
          <p className="ss-mw-note">데모입니다 — 상대의 수락을 흉내낸 것이고 실제로 잡히지 않습니다.</p>

          {/* 🔴 **취소는 닫기(×)와 다른 일이다.** ×는 이 판을 접는 것이고,
              이것은 **잡힌 경기를 무르는 것**이다 — 그래서 자리도 뜻도 가른다. */}
          {/* 무를 길이 없으면 단추도 안 그린다 — 눌러도 아무 일이 없으면 안 된다. */}
          <div className="ss-mw-actions" hidden={!onCancel}>
            {confirming ? (
              <>
                <button
                  type="button"
                  className="ss-mw-cancel"
                  data-danger="true"
                  onClick={() => leave(onCancel ?? onClose)}
                >
                  정말 취소합니다
                </button>
                <button
                  type="button"
                  className="ss-mw-keep"
                  onClick={() => setConfirming(false)}
                >
                  되돌리기
                </button>
              </>
            ) : (
              <button
                type="button"
                className="ss-mw-cancel"
                onClick={() => setConfirming(true)}
              >
                경기 취소
              </button>
            )}
          </div>
        </div>

        <MiniPitch team={them.name} players={them.squad} side="them" />
      </div>
    </div>,
    document.body,
  )
}
