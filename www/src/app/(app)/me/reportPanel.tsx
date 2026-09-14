'use client'

import { createContext, useContext } from 'react'

/**
 * 「해당 영상 리포트 보기」가 켜져 있는가.
 *
 * 🔴 **왜 맥락으로 올렸나** — 리포트를 여는 단추는 오른쪽 칸(`MyVideos`)에
 * 있는데, 켜지면 **왼쪽 칸이 통째로 밀려나야** 한다(사용자 요청). 왼쪽 칸은
 * 서버가 그린 것이라 그 둘의 공통 조상(`ProfileStage`)이 값을 쥐어야 한다 —
 * 편집 모드(`data-editing`)가 이미 같은 구조다.
 *
 * ⚠️ 무대 밖에서 부르면 아무 일도 안 한다(기본값). 리포트 판이 없는 화면
 * (분석 화면 · 시험)에서도 `MyVideos` 를 그릴 수 있어야 해서다.
 */
export type ReportPanel = { open: boolean; setOpen: (v: boolean) => void }

export const ReportPanelContext = createContext<ReportPanel>({
  open: false,
  setOpen: () => {},
})

export function useReportPanel(): ReportPanel {
  return useContext(ReportPanelContext)
}
