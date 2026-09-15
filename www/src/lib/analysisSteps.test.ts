import fs from 'node:fs'
import path from 'node:path'
import { ANALYSIS_STEPS } from './analysisSteps'

/**
 * 🔴 **정본은 `agent/scripts/analyze_s3.py` 다.** 화면의 단계는 그 스크립트가
 * 실제로 도는 순서의 사본이라, 스크립트 순서가 바뀌면 화면이 모르고 거짓 순서를
 * 보여 준다. 그래서 실제 파일에서 단계 표식이 찍히는 순서를 읽어 대조한다
 * (`rubricFocus.test.ts` 와 같은 방식).
 *
 * ⚠️ `agent/` 가 없는 환경(www 만 떼어 배포)에서는 건너뛴다.
 */
const SCRIPT = path.resolve(__dirname, '../../../agent/scripts/analyze_s3.py')
const has = fs.existsSync(SCRIPT)

/** 화면 칸 → 그 단계가 끝날 때 스크립트가 찍는 표식. 첫 칸(업로드)은 스크립트 밖이다. */
const MARKER: Record<string, string> = {
  fetch: 'print(f"[입력]',
  measure: 'print(f"[측정]',
  judge: 'print(f"[판정]',
  save: 'print(f"\\n저장:',
}

describe.runIf(has)('분석 진행 단계 — analyze_s3.py 와 어긋나지 않는다', () => {
  it('화면 단계가 analyze_s3.py 가 실제로 도는 순서와 같다', () => {
    const text = fs.readFileSync(SCRIPT, 'utf8')
    const keys = ANALYSIS_STEPS.map((s) => s.key).filter((k) => k !== 'register')
    const at = keys.map((k) => {
      const marker = MARKER[k]
      expect(marker, `${k} 의 표식이 없다`).toBeDefined()
      const i = text.indexOf(marker)
      expect(i, `${marker} 가 스크립트에 없다`).toBeGreaterThan(-1)
      return i
    })
    expect(at).toEqual([...at].sort((a, b) => a - b))
  })
})

describe('분석 진행 단계', () => {
  it('없는 단계 이름(전처리 · 근거 검증)을 쓰지 않는다', () => {
    const labels = ANALYSIS_STEPS.map((s) => s.label)
    expect(labels).not.toContain('전처리')
    expect(labels).not.toContain('근거 검증')
  })

  // 🔴 첫 칸은 업로드가, 마지막 칸은 서버 응답이 넘긴다 — 시간으로 넘기면 거짓이다.
  it('첫 칸과 마지막 칸은 시간으로 넘기지 않는다', () => {
    expect(ANALYSIS_STEPS[0].estimateMs).toBeNull()
    expect(ANALYSIS_STEPS.at(-1)!.estimateMs).toBeNull()
    for (const s of ANALYSIS_STEPS.slice(1, -1)) expect(s.estimateMs).toBeGreaterThan(0)
  })
})
