'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { apiErrorMessage, apiPatch } from '@/lib/api/client'

/**
 * 신원 바의 이름 자리 — **평소에는 이름만 있고, 눌러야 입력칸이 된다.**
 *
 * 참고한 장인 프로필에는 편집 UI 가 아예 없다. 프로필은 '보여주는 화면'인데
 * 입력칸과 저장 단추가 늘 떠 있으면 설정 화면처럼 읽힌다. 그래서 이름 옆에
 * 작은 '편집'만 두고, 누른 사람에게만 폼을 연다.
 *
 * 🔴 **이름(h1)을 이 컴포넌트가 그린다.** 페이지가 이름을 그리고 여기서
 * 편집만 맡으면, 편집 중에 이름과 입력칸이 같이 뜬다 — 같은 자리를 두 상태가
 * 번갈아 쓰므로 그리는 쪽도 하나여야 한다.
 *
 * 저장 뒤 `router.refresh()` 로 서버 컴포넌트를 다시 받는다. 낙관적으로
 * 화면만 바꾸지 않는 이유는 서버가 값을 정규화하기 때문이다(공백을 깎는다).
 */
export default function NicknameForm({ nickname }: { nickname: string }) {
  const router = useRouter()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(nickname)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  function open() {
    setSaved(false)
    setEditing(true)
  }

  function cancel() {
    setValue(nickname) // 고치다 만 값을 다음에 열 때 물려주지 않는다
    setError(null)
    setEditing(false)
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiPatch('/api/me', { nickname: value })
      // 🔴 알림을 지우지 않는다. 폼이 닫히면서 이름이 바뀌는 것이 곧
      // 피드백일 것 같지만, 새 이름은 router.refresh() 가 서버에서
      // 받아온 뒤에야 온다 — 그 사이 옛 이름이 그대로 보여서 저장이
      // 안 된 것처럼 읽힌다. 이 한 줄이 그 간극을 메운다.
      setSaved(true)
      timer.current = setTimeout(() => setSaved(false), 3000)
      setEditing(false)
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (!editing) {
    return (
      <div className="ss-profile-name-row">
        <h1 className="ss-profile-name">{nickname}</h1>
        {/* 🔴 글자를 뺐다(사용자 요청) — 대신 이름을 `aria-label` 로 남긴다.
            아이콘만 있는 단추는 읽어 주는 기계에서 "버튼"으로만 들려서,
            빼 버리면 무엇을 누르는지 알 길이 없다. */}
        <button
          type="button"
          className="ss-profile-edit ss-profile-edit-icon"
          onClick={open}
          aria-label="닉네임 편집"
        >
          <span className="material-symbols-outlined" aria-hidden="true">
            edit
          </span>
        </button>
        {saved && (
          <p role="status" className="ss-profile-name-saved">
            저장했습니다.
          </p>
        )}
      </div>
    )
  }

  return (
    <form onSubmit={onSubmit} className="ss-profile-name-row">
      <input
        aria-label="닉네임"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        minLength={1}
        maxLength={20}
        autoFocus
        className="ss-profile-name-input"
      />
      <button type="submit" className="ss-profile-edit" disabled={busy}>
        저장
      </button>
      <button type="button" className="ss-profile-edit" onClick={cancel} disabled={busy}>
        취소
      </button>
      {error && (
        <p role="alert" className="ss-profile-name-error">
          {error}
        </p>
      )}
    </form>
  )
}
