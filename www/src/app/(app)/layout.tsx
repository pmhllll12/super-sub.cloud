import FloatingNavBar from '@/components/ui/FloatingNavBar'

// 로그인한 화면 전용 셸. 이 그룹 밖(c/, login/, signup/, page.tsx)은 바를 띄우지 않는다.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="mx-auto max-w-[1120px] px-6 pb-32">{children}</div>
      <FloatingNavBar />
    </>
  )
}
