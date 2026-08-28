import FloatingNavBar from '@/components/ui/FloatingNavBar'

// 로그인 전용 화면(analysis/, me/) 셸 — 이 그룹의 페이지는 모두 requireUser()
// 로 이미 로그인이 보장돼 있으니 바를 무조건 띄운다. `/`(홈)는 이 그룹 밖에
// 있다 — 로그인 여부와 무관하게 열리는 화면이라 로그인했을 때만 바를
// 띄워야 해서, 그 판단은 page.tsx 가 직접 한다(같은 모양의 래퍼를 거기서도
// 따로 그린다).
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="mx-auto max-w-[1120px] px-6 pb-32">{children}</div>
      <FloatingNavBar />
    </>
  )
}
