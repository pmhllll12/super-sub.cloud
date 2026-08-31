import { NextResponse, type NextRequest } from 'next/server'
import { getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

export async function GET(req: NextRequest) {
  return withAuth(req, async (token) => {
    const { searchParams } = new URL(req.url)
    const q = searchParams.get('q') ?? undefined
    const page = Number(searchParams.get('page') ?? '1')
    const size = Number(searchParams.get('size') ?? '20')
    return NextResponse.json(await getBackend().listUsers(token, { q, page, size }))
  })
}
