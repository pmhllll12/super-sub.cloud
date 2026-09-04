'use client'

import { useRef, useState } from 'react'

/**
 * 흐름 B(모집 등록 돕기) 챗봇 — "용병 찾기" 알약을 누르면 열린다(미결 `min` 7번).
 *
 * 대화 이력은 서버에 저장하지 않는다 — 이 컴포넌트가 `history`(Gemini의
 * `Content[]` 그대로, 불투명한 값)를 들고 있다가 매 요청마다 돌려준다. 새로고침하면
 * 사라진다(설계 문서의 "열린 질문 3번" 결정 그대로).
 *
 * 🔴 **등록 API(`POST /api/teams/{id}/matches`)는 챗봇을 거치지 않고 이 컴포넌트가
 * 직접 부른다.** `/api/chat`이 돌려주는 `proposal`은 확인 카드일 뿐, LLM이 쓰기를
 * 실행하지 않는다 — 사용자가 [등록] 버튼을 눌러야 실제로 등록된다.
 */

type DisplayMessage = { role: 'user' | 'assistant' | 'system'; text: string }

type Proposal = {
  team_id: string
  team_name: string
  played_at: string
  place: string
  needs: { position_code: string; position_label: string; head_count: number }[]
}

type ChatResponse = {
  history: unknown
  reply: string
  proposal: Proposal | null
}

type ApiErrorBody = { error?: { code?: string; message?: string } }

/** 설계 문서의 에러 매핑 표 — 코드별 대화 복구 문구. */
function registerErrorText(code: string | undefined, fallback: string): string {
  switch (code) {
    case 'FORBIDDEN':
      return '이 팀은 주장만 등록할 수 있어요.'
    case 'TEAM_NOT_FOUND':
      return '그 팀을 더 이상 찾을 수 없어요. 팀을 다시 골라 주세요.'
    case 'PAST_MATCH':
      return '그 시간은 이미 지났어요, 다른 시간을 알려주세요.'
    default:
      return fallback || '등록하지 못했어요. 다시 시도해 주세요.'
  }
}

function formatPlayedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      month: 'numeric',
      day: 'numeric',
      weekday: 'short',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export default function MatchBot({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [messages, setMessages] = useState<DisplayMessage[]>([
    { role: 'assistant', text: '안녕하세요! 어느 팀에 어떤 경기를 등록할지 말씀해 주세요.' },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [proposal, setProposal] = useState<Proposal | null>(null)
  const [registering, setRegistering] = useState(false)
  const [registerError, setRegisterError] = useState<string | null>(null)
  const historyRef = useRef<unknown>([])

  if (!open) return null

  async function send() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setSending(true)
    setMessages((prev) => [...prev, { role: 'user', text }])
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: historyRef.current }),
      })
      const body = (await res.json()) as ChatResponse | ApiErrorBody
      if (!res.ok) {
        const err = body as ApiErrorBody
        setMessages((prev) => [
          ...prev,
          { role: 'system', text: err.error?.message ?? '잠시 문제가 있었어요. 다시 시도해 주세요.' },
        ])
        return
      }
      const ok = body as ChatResponse
      historyRef.current = ok.history
      if (ok.reply) setMessages((prev) => [...prev, { role: 'assistant', text: ok.reply }])
      setProposal(ok.proposal)
      setRegisterError(null)
    } catch {
      setMessages((prev) => [...prev, { role: 'system', text: '네트워크 오류로 보내지 못했어요.' }])
    } finally {
      setSending(false)
    }
  }

  async function register() {
    if (!proposal || registering) return
    setRegistering(true)
    setRegisterError(null)
    try {
      const res = await fetch(`/api/teams/${encodeURIComponent(proposal.team_id)}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          played_at: proposal.played_at,
          place: proposal.place,
          needs: proposal.needs.map((n) => ({
            position_code: n.position_code,
            head_count: n.head_count,
          })),
        }),
      })
      const body = (await res.json()) as ApiErrorBody
      if (!res.ok) {
        setRegisterError(registerErrorText(body.error?.code, body.error?.message ?? ''))
        return
      }
      setMessages((prev) => [...prev, { role: 'system', text: '경기 등록이 완료됐어요!' }])
      setProposal(null)
    } catch {
      setRegisterError('네트워크 오류로 등록하지 못했어요.')
    } finally {
      setRegistering(false)
    }
  }

  return (
    <aside
      className="ss-matchbot"
      role="complementary"
      aria-label={'용병 찾기'}
      // 🔴 흐림은 인라인으로만 준다 — globals.css에 두면 Lightning CSS를
      // 지나며 통째로 사라진다(SquadFriends·ProfileStage와 같은 이유).
      style={{ backdropFilter: 'blur(20px) saturate(1.4)', WebkitBackdropFilter: 'blur(20px) saturate(1.4)' }}
    >
      <header className="ss-matchbot-head">
        <h3>용병 찾기</h3>
        <button
          type="button"
          aria-label="용병 찾기 닫기"
          className="ss-matchbot-close material-symbols-outlined"
          onClick={onClose}
        >
          close
        </button>
      </header>

      <div className="ss-matchbot-list" role="log" aria-live="polite">
        {messages.map((m, i) => (
          <p key={i} className="ss-matchbot-msg" data-role={m.role}>
            {m.text}
          </p>
        ))}
      </div>

      {proposal && (
        <div className="ss-matchbot-card">
          <p>
            <strong>{proposal.team_name}</strong> · {formatPlayedAt(proposal.played_at)}
          </p>
          <p>{proposal.place}</p>
          <p>
            {proposal.needs.map((n) => `${n.position_label} ${n.head_count}명`).join(' · ')}
          </p>
          {registerError && <p className="ss-matchbot-error">{registerError}</p>}
          <button type="button" onClick={register} disabled={registering}>
            {registering ? '등록 중…' : '등록'}
          </button>
        </div>
      )}

      <form
        className="ss-matchbot-input"
        onSubmit={(e) => {
          e.preventDefault()
          void send()
        }}
      >
        <input
          type="text"
          aria-label="메시지"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
          placeholder="이번 주 토요일 저녁에 골키퍼 1명 필요해요"
        />
        <button type="submit" disabled={sending || !input.trim()}>
          보내기
        </button>
      </form>
    </aside>
  )
}
