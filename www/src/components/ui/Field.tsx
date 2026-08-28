'use client'

import { useId, useState } from 'react'

export default function Field({
  label,
  type = 'text',
  value,
  onChange,
  required,
  minLength,
  maxLength,
  hint,
  revealable,
}: {
  label: string
  type?: string
  value: string
  onChange: (v: string) => void
  required?: boolean
  minLength?: number
  maxLength?: number
  hint?: string
  /** type="password" 전용 — 눈 아이콘으로 입력값을 잠깐 볼 수 있게 한다. */
  revealable?: boolean
}) {
  const [visible, setVisible] = useState(false)
  const canToggle = revealable && type === 'password'
  const inputType = canToggle ? (visible ? 'text' : 'password') : type
  const inputId = useId()

  // <label> 이 input 을 감싸면, 토글 버튼을 그 안에 얹는 순간 버튼의
  // aria-label 이 input 의 접근성 이름에 섞여 "비밀번호 비밀번호 보기"처럼
  // 되어 버린다(실제 브라우저 접근성 트리 기준 — jsdom 테스트에선 안
  // 드러난다). 그래서 label 을 htmlFor 로 명시적으로만 연결하고, 입력칸과
  // 버튼은 label 밖의 별도 컨테이너에 둔다.
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="ss-field-label text-sm">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={inputType}
          value={value}
          required={required}
          minLength={minLength}
          maxLength={maxLength}
          onChange={(e) => onChange(e.target.value)}
          className={`ss-field-input w-full px-4 py-3 outline-none ${canToggle ? 'pr-12' : ''}`}
          style={{
            borderRadius: 'var(--ss-field-radius)',
            border: '1px solid color-mix(in srgb, var(--ss-fg) 35%, transparent)',
          }}
        />
        {canToggle && (
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? '비밀번호 숨기기' : '비밀번호 보기'}
            className="absolute inset-y-0 right-0 flex items-center px-3"
            style={{ color: 'color-mix(in srgb, var(--ss-fg) 60%, transparent)' }}
          >
            <span className="material-symbols-outlined text-xl" aria-hidden="true">
              {visible ? 'visibility_off' : 'visibility'}
            </span>
          </button>
        )}
      </div>
      {hint && <span className="ss-field-hint text-xs">{hint}</span>}
    </div>
  )
}
