import { redirect } from 'next/navigation'

// '내 선수 카드'를 '내 프로필'에 합쳤다 — 카드는 이제 /me 안에 있다.
// 옛 링크 · 북마크가 안 깨지게 이 자리는 보내는 스텁으로 남긴다(/home 과 같은 방식).
export default function MyCardPage() {
  redirect('/me')
}
