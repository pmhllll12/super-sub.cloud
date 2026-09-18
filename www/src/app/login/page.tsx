'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import { useRateLimitLock } from '@/lib/api/rateLimit'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'
import AuthShell from '@/components/auth/AuthShell'
import {
  judgeEmail,
  judgeNickname,
  judgeSeat,
  judgeSeats,
  setJudgeSeat,
  readJudgeSeat,
} from '@/lib/judgeSeat'

const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'
const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

/**
 * **심사위원용 계정** (사용자 요청, 2026-09-17) — 심사 때 아무것도 치지 않고
 * 바로 둘러볼 수 있게 한다.
 *
 * 🔴 **세션을 가짜로 심지 않는다.** 그렇게 하면 `/home` 은 열려도 **그 뒤
 * 모든 호출이 401** 이다 — 세션 쿠키에 담기는 것이 백엔드 **접근 토큰**이라,
 * 토큰 없이 들어가면 카드도 스쿼드도 알림도 안 뜨는 빈 화면만 본다.
 * 그리고 우회 경로를 공개 사이트에 두면 그 길로 아무나 남의 데이터에 닿는다.
 *
 * 🔴 **대신 계정을 단추가 알아서 챙긴다** — 로그인해 보고, 없으면 그 자리에서
 * 가입시킨 뒤 다시 로그인한다. 심사위원은 **누르기만** 하면 되고, 진짜
 * 계정이라 **안이 전부 돌아간다.** 실서버에 누가 미리 만들어 둘 필요도 없다.
 */
/**
 * 🔴 **계정을 여러 개 두고 브라우저마다 하나를 쓴다**(2026-09-18, 사용자 요청).
 * 전에는 상수 하나라 심사위원 전원이 **같은 계정**에 들어왔고, 판·알림·초대를
 * 공유해서 서로의 화면을 건드렸다. 고르는 규칙은 `lib/judgeSeat.ts`.
 */
const JUDGE_PASSWORD = 'supersub-judge-2026'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  /* 🔴 **429 뒤에는 다시 안 보낸다**(계약 1번). 기다릴 시간은 서버가 준
     `Retry-After` 다 — 자체 타이머를 두지 않는다. */
  const limit = useRateLimitLock()
  /**
   * 이 브라우저에 배정된 심사위원 번호.
   *
   * 🔴 **그릴 때 저장소를 읽지 않는다**(하이드레이션) — 서버가 그린 HTML 에는
   * 이 브라우저의 값이 있을 수 없다. 붙은 뒤에 읽는다.
   * 🔴 **여기서 고르지는 않는다** — 로그인 화면을 열어 보기만 한 사람에게
   * 번호를 물리면, 실제로 쓰는 사람보다 먼저 자리를 차지한다.
   */
  const [seat, setSeat] = useState<number | null>(null)
  useEffect(() => {
    setSeat(readJudgeSeat())
  }, [])

  /**
   * 심사위원용 — **로그인하고, 계정이 없으면 만들어서 다시 로그인한다.**
   *
   * 🔴 `onSubmit` 과 **같은 경로·같은 처리**를 쓴다(429 잠금 · 에러 문구).
   * 따로 만들면 한쪽만 고쳐져 두 길의 동작이 갈린다.
   * ⚠️ 가입이 `409 EMAIL_ALREADY_EXISTS` 여도 **실패가 아니다** — 그 사이
   * 다른 심사위원이 먼저 눌렀다는 뜻이라, 그대로 로그인으로 넘어간다.
   */
  async function onJudge() {
    if (limit.locked) return
    setError(null)
    setBusy(true)
    /* 🔴 **이 브라우저에 배정된 번호**로 들어간다 — 없으면 그 자리에서
       무작위로 하나 골라 기억한다(`judgeSeat`). */
    const n = seat ?? judgeSeat()
    setSeat(n)
    const email = judgeEmail(n)
    try {
      try {
        await apiPost('/api/auth/login', { email, password: JUDGE_PASSWORD })
      } catch {
        /* 계정이 아직 없다 — 만들고 다시 들어간다. 가입이 이미 있다고
           튕기는 것도 여기서 삼킨다(먼저 누른 사람이 있었을 뿐이다). */
        await apiPost('/api/auth/signup', {
          email,
          password: JUDGE_PASSWORD,
          nickname: judgeNickname(n),
        }).catch(() => null)
        await apiPost('/api/auth/login', { email, password: JUDGE_PASSWORD })
      }
      router.push('/home')
      router.refresh()
    } catch (err) {
      if (!limit.lockFrom(err)) setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    // 잠긴 동안 눌러도 나가지 않는다 — 단추를 막아 두지만 Enter 로도 들어온다.
    if (limit.locked) return
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/login', { email, password })
      router.push('/home')
      router.refresh()
    } catch (err) {
      // 429 는 잠금이 제 문구(남은 초)를 내므로 에러 줄을 겹쳐 쓰지 않는다.
      if (!limit.lockFrom(err)) setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      formTitle="다시 만나서 반가워요"
      formDescription="이메일과 비밀번호를 입력해 로그인하세요."
      footer={
        <>
          <p className="max-w-sm text-xs" style={{ color: FAINT }}>
            계속 진행하면 이용약관과 개인정보처리방침에 동의하는 것으로 간주됩니다.
          </p>
          <p className="text-sm" style={{ color: MUTED }}>
            계정이 없으신가요?{' '}
            <Link href="/signup" style={{ color: 'var(--ss-accent)' }}>
              회원가입
            </Link>
          </p>
          {/* 🔴 **회원가입 아래, 다른 것은 건드리지 않는다**(사용자 요청).
              아래에 더하는 것이라 위 요소들의 자리·크기가 안 바뀐다. */}
          <PillButton
            variant="white"
            disabled={busy || limit.locked}
            onClick={() => void onJudge()}
            className="w-full"
          >
            심사위원용 로그인{seat ? ` (${seat}번)` : ''}
          </PillButton>
          {/* 🔴 **번호를 직접 고른다**(사용자 요청, 2026-09-18). 전에는
              「바꾸기」가 **무작위로 다른 번호**를 집어서, 원하는 자리를
              고를 수가 없었다. 무작위는 이제 **처음 배정**에만 남는다 —
              아무도 안 고르고 그냥 누르면 서로 다른 자리로 흩어지게 하려는 것이다.

              🔴 **번호를 보여 주는 것이 이 방식의 안전장치다** — 둘이 같은
              번호를 쓰면 판·알림을 공유한다. 보여 줘야 부딪힌 것을 알아채고
              한쪽이 옮긴다. */}
          <label className="flex items-center gap-2 text-xs" style={{ color: MUTED }}>
            심사위원 번호
            <select
              className="rounded border bg-transparent px-2 py-1"
              style={{ color: 'var(--ss-fg)', borderColor: MUTED }}
              value={seat ?? ''}
              onChange={(e) => {
                const picked = setJudgeSeat(Number(e.target.value))
                if (picked !== null) setSeat(picked)
              }}
            >
              {seat === null && <option value="">자동</option>}
              {judgeSeats().map((n) => (
                <option key={n} value={n} style={{ color: '#000' }}>
                  {n}번
                </option>
              ))}
            </select>
          </label>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex w-full flex-col gap-4">
        <Field label="이메일" type="email" value={email} onChange={setEmail} required />
        <Field
          label="비밀번호"
          type="password"
          value={password}
          onChange={setPassword}
          required
          minLength={8}
          revealable
        />
        {(error || limit.note) && (
          <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
            {limit.note ?? error}
          </p>
        )}
        <PillButton type="submit" disabled={busy || limit.locked} className="mt-2 w-full">
          로그인
        </PillButton>
        {/* 🔴 구글 버튼은 **감추거나 덮지 않는다**(§6 — 가리면 구글이 클릭을
            통째로 무시한다). 잠금은 버튼이 아니라 **보내는 쪽**에서 건다. */}
        <GoogleSignInButton onError={setError} limit={limit} />
      </form>
    </AuthShell>
  )
}
