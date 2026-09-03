import { notFound } from 'next/navigation'
import PageEnter from '@/components/PageEnter'
import { TransitionLink } from '@/lib/pageTransition'
import { findCoach } from '@/lib/market'
import CoachDetail from '../CoachDetail'

/**
 * 코치 상세 **화면**. 알맹이는 `CoachDetail` 한 벌이고(레슨 · 상점 입구의 오른쪽
 * 판도 같은 것을 그린다) 여기서는 **제 주소로 열릴 때의 머리글**만 준다.
 */
export default async function CoachPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const coach = findCoach(id)
  if (!coach) notFound()

  return (
    <PageEnter className="ss-market ss-coach">
      <CoachDetail
        coach={coach}
        back={
          <TransitionLink href="/market/coaches" className="ss-market-back ss-rise">
            ← 코치
          </TransitionLink>
        }
      />
    </PageEnter>
  )
}
