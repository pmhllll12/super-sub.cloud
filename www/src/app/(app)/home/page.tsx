import { redirect } from 'next/navigation'

// `/` 가 홈이 됐다(랜딩과 런처를 하나로 합쳤다). 이 자리는 기존 링크가
// 깨지지 않도록만 남겨 둔다 — 로그인/구글 로그인 화면이 로그인 성공 뒤
// `router.push('/home')` 을 부르고(다른 에이전트가 그 화면들을 작업
// 중이라 여기서 손댈 수 없다), 북마크·공유된 옛 링크도 있을 수 있다.
// 로그인 여부와 무관하게 그냥 `/` 로 보낸다 — `/` 자체가 로그인 여부에
// 맞는 모습을 알아서 그린다.
export default function LegacyHomeRedirect() {
  redirect('/')
}
