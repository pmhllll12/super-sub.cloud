import { requireUser } from '@/server/currentUser'
import AnalysisStage from '@/components/analysis/AnalysisStage'

// 화면 한 장을 통째로 쓰는 연출이라 배경까지 `AnalysisStage` 가 들고 있다 —
// 왼쪽 판이 들어올 때 배경 사진을 그만큼 옮겨야 해서 한 덩어리여야 한다.
export default async function AnalysisPage() {
  await requireUser()
  return <AnalysisStage />
}
