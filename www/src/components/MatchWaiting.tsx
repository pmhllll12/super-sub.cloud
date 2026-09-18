'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import MiniPitch from '@/components/MiniPitch'
import MatchReview from '@/components/MatchReview'
import WhoCard from '@/components/WhoCard'
import type { MatchTeam, MyTeamSummary, PitchPlayer } from '@/lib/teamMatch'
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
   *
   * 🔴 **서버로 나가는 일이라 실패할 수 있다**(2026-09-17, 미결 `paik` 34번).
   * 던지면 **판이 안 닫히고 그 이유를 그대로 적는다** — 지원자가 있으면
   * `409`, 주장이 아니면 `403`, 지난 경기면 `422` 다. 화면이 미리 막지
   * 않는다: 지원이 몇인지도 상대 팀 주장이 누구인지도 **서버만 안다.**
   */
  onCancel?: () => Promise<void>
}) {
  /**
   * 내려가는 중인가 — 🔴 **아직 DOM 에 있어야 한다.** 누르자마자 지우면
   * 내려가는 것을 아무도 못 본다(추천 판이 같은 이유로 같은 것을 한다).
   */
  const [leaving, setLeaving] = useState(false)
  /**
   * 🔴 **경기 시각이 지났으면 「경기 끝내기」다**(사용자 요청, 2026-09-17).
   * 이미 한 경기를 「취소」하는 것은 말이 안 되고, 그 자리에서 리뷰로 넘어간다.
   *
   * ⚠️ **그릴 때 시계를 읽지 않는다** — 서버가 그린 것과 달라져 hydration 이
   * 깨진다. 붙은 뒤에 한 번 재고, 그 뒤로는 1분마다 다시 본다(경기 시각을
   * 걸쳐 두고 화면을 열어 둔 사람에게도 바뀌어야 한다).
   */
  const [over, setOver] = useState(false)
  useEffect(() => {
    const at = new Date(them.playedAt).getTime()
    if (Number.isNaN(at)) return
    let id = 0
    /* 🔴 **그 시각에 정확히 바뀐다.** 주기적으로 훑으면 최대 그 주기만큼
       늦게 바뀐다 — 경기 시각을 코앞에 두고 화면을 열어 둔 사람에게는 그게
       「안 바뀐다」로 보인다. 남은 시간만큼만 재고, 멀면 잘라서 다시 잰다
       (`setTimeout` 은 아주 긴 값에서 제대로 안 돈다). */
    const tick = () => {
      const left = at - Date.now()
      if (left <= 0) {
        setOver(true)
        return
      }
      setOver(false)
      id = window.setTimeout(tick, Math.min(left, 60_000))
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    tick()
    return () => clearTimeout(id)
  }, [them.playedAt])

  /** 리뷰 창을 열어 둔 상태. 🔴 닫으면 대기 화면까지 함께 내려간다. */
  const [reviewing, setReviewing] = useState(false)
  /**
   * 판에서 **누른 사람** — 간단한 프로필을 옆에 띄운다(사용자 요청,
   * 2026-09-18). 🔴 두 판 어느 쪽이든 한 번에 하나만 연다.
   */
  const [picked, setPicked] = useState<PitchPlayer | null>(null)

  /**
   * 「경기 취소」를 눌러 **한 번 더 묻는 중**인가.
   *
   * 🔴 **곧바로 취소하지 않는다.** 되돌릴 수 없는 일이라 그 자리에서 다시
   * 묻는다 — `window.confirm` 은 안 쓴다(이 사이트는 제 판을 그려 왔고,
   * 그쪽은 시험에서도 못 누른다. 영상 지우기가 같은 방식이다).
   */
  const [confirming, setConfirming] = useState(false)
  /** 취소를 보내는 중 — 두 번 눌리지 않게 한다. */
  const [cancelling, setCancelling] = useState(false)
  /** 서버가 준 이유. 있으면 판은 그대로 서 있다. */
  const [cancelError, setCancelError] = useState<string | null>(null)
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
        <MiniPitch
          team={us.name}
          players={us.squad}
          side="us"
          myCard={myCard}
          /* 🔴 **리뷰 중에는 못 누른다.** 그때 판은 「평가할 사람 고르기」로
             뜻이 바뀌어서, 같은 카드가 두 가지 일을 하면 어느 쪽이 될지
             알 수 없다(낭독기에서도 같은 이름의 단추가 둘이 된다). */
          onPick={reviewing ? undefined : setPicked}
        />

        <div className="ss-mw-mid">
          <p className="ss-mw-when">{whenText(them.playedAt)}</p>
          <p className="ss-mw-where">{them.place}</p>
          <p className="ss-mw-vs">
            <span>{us.name}</span>
            <em>VS</em>
            <span>{them.name}</span>
          </p>
          {/* 🔴 **「데모입니다」를 걷었다**(2026-09-17, 사용자 지적). 가짜
              `applyToTeam` 이 1.4초 뒤 수락을 흉내내던 시절의 문장이고, 그때는
              숨기지 않는 것이 옳았다. 지금은 수락이 **진짜로 서버에 나가고
              경기가 실제로 잡힌다** — 그대로 두면 그 문장이 거짓이 된다.
              🔴 조건 없이 박혀 있어서 `USE_MOCK` 으로도 안 꺼졌다(화면에 박힌
              mock 이다) — 실제 도메인에서도 떴다. */}

          {/* 🔴 **취소는 닫기(×)와 다른 일이다.** ×는 이 판을 접는 것이고,
              이것은 **잡힌 경기를 무르는 것**이다 — 그래서 자리도 뜻도 가른다. */}
          {/* 무를 길이 없으면 단추도 안 그린다 — 눌러도 아무 일이 없으면 안 된다. */}
          {/* 🔴 **실패하면 판은 그대로 서 있고 이유만 붙는다** — 지원자가 있어
              못 무르는 경우(409)가 있다. 문구는 서버가 준 것을 그대로 쓴다. */}
          {cancelError && (
            <p role="alert" className="ss-mw-error">
              {cancelError}
            </p>
          )}

          <div className="ss-mw-actions" hidden={!onCancel}>
            {confirming ? (
              <>
                <button
                  type="button"
                  className="ss-mw-cancel"
                  data-danger="true"
                  disabled={cancelling}
                  onClick={() => {
                    if (!onCancel) return leave(onClose)
                    setCancelling(true)
                    setCancelError(null)
                    /* 🔴 **보내고 나서 내려간다.** 먼저 내려보내면 실패해도
                       판이 사라져서, 안 물러진 경기를 물러진 것으로 읽는다. */
                    /* `Promise.resolve` 로 감싼다 — 부모가 async 가 아니어도
                       (시험의 대역이 그렇다) 같은 길로 흐른다. */
                    void Promise.resolve(onCancel())
                      /* 성공했으면 **여느 닫기와 같은 길로** 내려간다 —
                         다 내려간 뒤에 부모가 판을 거둔다. */
                      .then(() => leave(onClose))
                      .catch((err: unknown) =>
                        setCancelError(
                          err instanceof Error ? err.message : '경기를 무르지 못했습니다.',
                        ),
                      )
                      .finally(() => setCancelling(false))
                  }}
                >
                  {cancelling ? '무르는 중…' : '정말 취소합니다'}
                </button>
                <button
                  type="button"
                  className="ss-mw-keep"
                  disabled={cancelling}
                  onClick={() => {
                    setConfirming(false)
                    setCancelError(null)
                  }}
                >
                  되돌리기
                </button>
              </>
            ) : over ? (
              /* 🔴 **끝난 경기는 취소가 아니라 마무리다.** 누르면 리뷰로 간다. */
              <button
                type="button"
                className="ss-mw-cancel"
                data-done="true"
                onClick={() => setReviewing(true)}
              >
                경기 끝내기
              </button>
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

        <MiniPitch
          team={them.name}
          players={them.squad}
          side="them"
          onPick={reviewing ? undefined : setPicked}
        />
      </div>

      {/* 🔴 **경기 화면 위에 뜬다** — 닫아도 경기 화면은 그대로다(사용자 조건:
          「경기매칭된 상태는 유지 되어야해」). 그래서 새 경로로 보내지 않는다. */}
      {picked && (
        <WhoCard
          /* 🔴 **사람이 바뀌면 다시 붙인다** — 안 그러면 앞사람 값이 잠깐
             보인 뒤 바뀐다. 통을 비우는 일을 여기 한 줄로 끝낸다. */
          key={picked.cardSlug ?? picked.nickname}
          slug={picked.cardSlug ?? null}
          fallbackName={picked.nickname}
          onClose={() => setPicked(null)}
        />
      )}

      {/* 🔴 **닫으면 둘 다 내려간다**(사용자 설계) — 리뷰 창이 먼저 사라지고,
          이어서 대기 화면이 여느 닫기와 같은 길로 내려가 홈만 남는다. */}
      {reviewing && (
        <MatchReview
          us={us}
          them={{ name: them.name, squad: them.squad }}
          onClose={() => {
            setReviewing(false)
            leave(onClose)
          }}
        />
      )}
    </div>,
    document.body,
  )
}
