import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().getMyCard(token)))
}

/**
 * 카드를 만든다 — `POST /api/v1/me/card` (api-contract.md 3장, 미결 jin-7).
 *
 * 🔴 **화면을 열 때 자동으로 부르지 않는다.** 공개 링크가 생기는 것은
 * 사용자의 행위여야 해서 계약이 `GET` 과 일부러 나눠 두었다 — 프리페치나
 * 봇이 카드를 만들면 되돌리기 어렵다.
 *
 * 멱등이라 이미 있으면 있는 카드가 그대로 온다. 그래서 201 을 고정으로
 * 쓰지 않고 200 으로 돌려준다 — 만들었는지 이미 있었는지는 화면이 굳이
 * 갈라 다룰 일이 없다.
 */
export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => NextResponse.json(await getBackend().createMyCard(token)))
}
