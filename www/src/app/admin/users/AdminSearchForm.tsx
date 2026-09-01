'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import PillButton from '@/components/ui/PillButton'

export default function AdminSearchForm({ defaultValue }: { defaultValue: string }) {
  const router = useRouter()
  const [q, setQ] = useState(defaultValue)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const params = new URLSearchParams()
    if (q.trim()) params.set('q', q.trim())
    router.push(`/admin/users${params.toString() ? `?${params}` : ''}`)
  }

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="이메일 또는 닉네임 검색"
        className="ss-field-input px-4 py-2 text-sm outline-none"
        style={{
          borderRadius: 'var(--ss-field-radius)',
          border: '1px solid color-mix(in srgb, var(--ss-fg) 35%, transparent)',
        }}
      />
      <PillButton type="submit" variant="ghost">
        검색
      </PillButton>
    </form>
  )
}
