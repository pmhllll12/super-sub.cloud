/**
 * 분석 화면의 **진행 단계** — 실제 분석이 도는 순서 그대로다(2026-09-15, 사용자 요청).
 *
 * 🔴 **정본은 `agent/scripts/analyze_s3.py` 다.** 워커가 그 스크립트를 돌리고,
 * 스크립트는 `[입력]` → `[측정]` → `[판정]` → 미리보기 · `저장:` 순서로 간다.
 * 전에 있던 「전처리」·「근거 검증」은 **그런 단계가 따로 없었다** — 제안서 이름을
 * 자리에 먼저 놓은 것이었다. `analysisSteps.test.ts` 가 그 순서를 실제 파일과 대조한다.
 *
 * 🔴 **어느 칸이 켜지는지는 추정이다.** 워커가 단계별로 보고하는 경로가 없어서
 * (`agent/scripts/worker.py` 는 끝났을 때만 보고한다) 화면은 지금 어느 단계인지
 * 모른다. 그래서 칸은 **평소 걸리는 시간**(`estimateMs`)으로 넘어가고, 진짜인 것은
 * 첫 칸(업로드)과 끝(서버가 준 리포트 · 실패)뿐이다 — 끝은 `AnalysisStage` 의
 * 폴링이 정한다.
 *
 * `estimateMs` 출처: EC2 GPU 에서 `analyze_s3.py` 한 바퀴의 `timing`
 * (`_posts/2026-09-03-ec2-gpu-검증-한-바퀴-돌았습니다`):
 * `fetch_s 1.04 · measure_s 32.78 · judge_s 16.75 · preview_s 13.36`.
 * ⚠️ 영상 한 편의 값이다 — 실서버 리포트의 `timing` 이 쌓이면 평균으로 바꾼다.
 */
export type AnalysisStep = {
  key: string
  label: string
  note: string
  /**
   * 이 칸에 머무는 시간. `null` 이면 **시간으로 넘기지 않는다** —
   * 첫 칸은 업로드가 끝나야, 마지막 칸은 서버가 끝났다고 해야 넘어간다.
   */
  estimateMs: number | null
}

export const ANALYSIS_STEPS: readonly AnalysisStep[] = [
  {
    key: 'register',
    label: '영상 등록',
    note: '클립을 올리고 분석 작업을 만듭니다',
    estimateMs: null,
  },
  {
    key: 'fetch',
    label: '영상 받기',
    note: '분석 서버가 올린 영상을 내려받습니다',
    estimateMs: 1_000,
  },
  {
    key: 'measure',
    label: '자세 측정',
    note: '사람과 관절을 찾고, 축구 영상인지 확인합니다',
    estimateMs: 33_000,
  },
  {
    key: 'judge',
    label: '판정 · 근거',
    note: '루브릭으로 항목을 판정하고 근거 문장을 씁니다',
    estimateMs: 17_000,
  },
  {
    key: 'save',
    label: '미리보기 · 저장',
    note: '장면 미리보기를 만들고 리포트를 올립니다',
    estimateMs: null,
  },
]

/**
 * 서버가 추정보다 **먼저** 끝났을 때 남은 칸을 채우는 간격.
 *
 * 🔴 칸을 건너뛰고 곧장 리포트를 띄우지 않는다 — 중간 칸이 켜진 채 리포트가
 * 뜨면 「측정하다 말았다」로 읽힌다. 짧게 하나씩 채운 뒤 넘어간다.
 * 🔴 **실패에는 쓰지 않는다** — 종목 불일치는 측정에서 멈춘 것이라 끝까지
 * 채우면 거짓이 된다. 실패는 곧바로 사유를 보여 준다.
 */
export const FINISH_STEP_MS = 250
