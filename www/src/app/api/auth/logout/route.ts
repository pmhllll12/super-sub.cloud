import { NextResponse } from 'next/server'
import { clearSession } from '@/server/session'

export async function POST() {
  return clearSession(NextResponse.json({ ok: true }))
}
