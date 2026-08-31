'use client'

import { useEffect, useRef, useState } from 'react'

/**
 * 분석 에이전트와 나누는 대화 — 앱의 `chat_pane.dart` 를 옮긴 것이다.
 *
 * ⚠️ **답은 아직 규칙 몇 개로 낸다.** 계약(api-contract.md)에 대화
 * 엔드포인트가 없다 — RAG 검증이 붙어야 나오는 값이다. 엔드포인트가 생기면
 * 이 상수를 지우고 `/api/*` 를 부르면 된다(브라우저는 FastAPI 를 직접 모른다).
 *
 * 🔴 **가짜여도 진짜처럼 굴어야 한다.** 앱 mock 의 주석 그대로다 — 지연을
 * 넣지 않으면 "기다리는 동안의 표시"를 아예 안 만들게 되고, API 를 붙이는 날
 * 대화창을 다시 짠다.
 */
const REPLY_DELAY_MS = 700

const RULES: { keys: string[]; text: string }[] = [
  {
    keys: ['안녕', '하이', 'hello'],
    text: '안녕하세요. 올리신 영상을 보고 실력과 성향을 정리해 드립니다. 무엇이 궁금하신가요?',
  },
  {
    keys: ['실력', '점수', '평가', '어때', '몇 점'],
    text: '실력은 하나의 점수로 내지 않습니다. 수준 · 역할 · 성향 세 축을 따로 보여 드리는 것이 이 앱의 방식입니다.',
  },
  {
    keys: ['포지션', '자리'],
    text: '영상에서 뽑은 활동 범위와 스프린트 구간을 보면 측면 쪽 움직임이 많습니다. 지표가 쌓이면 종목별 포지션 정의에 맞춰 다시 짚어 드리겠습니다.',
  },
  {
    keys: ['근거', '어떻게', '왜'],
    text: '판단마다 그렇게 본 장면을 함께 답합니다. 근거를 못 찾은 판단은 내놓지 않습니다 — 그게 이 에이전트의 검증 방식입니다.',
  },
  {
    keys: ['호칭', '카드'],
    text: '호칭은 기준을 넘긴 것만 드립니다. 못 받은 호칭은 아예 보여 드리지 않습니다 — 못 넘긴 표시가 남으면 그게 낙인이 되니까요.',
  },
  {
    keys: ['영상', '업로드', '올리'],
    text: '왼쪽 판에 영상을 끌어다 놓거나 눌러서 고르시면 됩니다. 한 번 분석에 크레딧 1개가 듭니다.',
  },
]

const FALLBACK =
  '아직 그 질문에는 답할 근거가 부족합니다. 영상을 올리시면 그 장면을 짚어 가며 말씀드리겠습니다.'

function answer(question: string): string {
  const q = question.toLowerCase()
  return RULES.find((r) => r.keys.some((k) => q.includes(k)))?.text ?? FALLBACK
}

type Message = { id: number; mine: boolean; text: string }

export default function AnalysisChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [waiting, setWaiting] = useState(false)
  const [draft, setDraft] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const seq = useRef(0)
  const timer = useRef(0)

  useEffect(() => () => clearTimeout(timer.current), [])

  // 말이 붙으면 맨 아래로 내린다. 새 말이 화면 밖에 쌓이면 답이 온 줄 모른다.
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, waiting])

  function send() {
    const text = draft.trim()
    if (!text || waiting) return
    setDraft('')
    setMessages((prev) => [...prev, { id: seq.current++, mine: true, text }])
    setWaiting(true)
    timer.current = window.setTimeout(() => {
      setMessages((prev) => [...prev, { id: seq.current++, mine: false, text: answer(text) }])
      setWaiting(false)
    }, REPLY_DELAY_MS)
  }

  return (
    <div className="ss-chat">
      <div className="ss-chat-log" ref={listRef} role="log" aria-live="polite" aria-label="대화">
        {messages.length === 0 && !waiting ? (
          <p className="ss-chat-empty">
            영상에 대해 궁금한 것을 물어보세요.
            <br />
            판단의 근거가 된 장면까지 함께 답합니다.
          </p>
        ) : (
          messages.map((m) => (
            <p key={m.id} className="ss-chat-bubble" data-mine={m.mine ? 'true' : undefined}>
              {m.text}
            </p>
          ))
        )}
        {waiting && (
          /* 기다리는 동안의 표시 — 점 셋. 없으면 답이 오기 전까지 아무 일도
             안 일어난 것처럼 보인다. */
          <p className="ss-chat-bubble ss-chat-typing" aria-label="답하는 중">
            <span />
            <span />
            <span />
          </p>
        )}
      </div>

      <form
        className="ss-chat-form"
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
      >
        {/* 🔴 라벨은 htmlFor + id 로 명시적으로 잇는다 — 안쪽에 버튼이 있는
            입력칸은 암묵적 <label> 래핑에서 접근성 이름이 섞인다(Field.tsx). */}
        <label htmlFor="ss-chat-input" className="sr-only">
          질문
        </label>
        <input
          id="ss-chat-input"
          className="ss-chat-input"
          placeholder="무엇이 궁금하신가요"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          autoComplete="off"
        />
        <button
          type="submit"
          className="ss-chat-send material-symbols-outlined"
          aria-label="보내기"
          disabled={!draft.trim() || waiting}
        >
          arrow_upward
        </button>
      </form>
    </div>
  )
}
