'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import PillButton from '@/components/ui/PillButton'

export default function AdminVideoSearchForm({ defaultValue }: { defaultValue: string }) {
  const router = useRouter()
  const [user, setUser] = useState(defaultValue)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!user.trim()) return
    router.push(`/admin/videos?user=${encodeURIComponent(user.trim())}`)
  }

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input
        value={user}
        onChange={(e) => setUser(e.target.value)}
        placeholder="사용자 id 또는 이메일"
        className="ss-field-input px-4 py-2 text-sm outline-none"
        style={{
          borderRadius: 'var(--ss-field-radius)',
          border: '1px solid color-mix(in srgb, var(--ss-fg) 35%, transparent)',
        }}
      />
      <PillButton type="submit" variant="ghost">
        조회
      </PillButton>
    </form>
  )
}
