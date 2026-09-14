import fs from 'node:fs'
import path from 'node:path'

/**
 * 🔴 **선택자와 `{` 사이에 주석이 끼면 안 된다.** CSS 는 그것을 오류로 안 보고
 * 다음 `{` 까지 선택자를 이어 붙인다 — 앞 규칙의 선택자가 **뒤 규칙에 붙고**,
 * 원래 규칙의 몸통은 범위 없이 떨어져 나간다. 콘솔에도 안 남는다.
 *
 * 이 파일에서 두 번 밟았다:
 *   · 2026-09-08 `.ss-profile-id-main,` 뒤에 절 주석 → 연출이 사흘 죽어 있었다
 *   · 2026-09-11 `.ss-shot[data-picked='true']` 뒤에 「선수와 비교하기」 절 주석 →
 *     영상 틀의 키 규칙이 기본 규칙(38vh)에 져서 **분석 화면 영상이 반으로 줄었다**
 *
 * 둘 다 절을 **선택자와 몸통 사이에** 끼워 넣다가 생겼다. 눈으로는 안 보이고
 * jsdom 은 CSS 를 안 그리므로 파일을 직접 읽어 잡는다.
 */
const CSS = fs.readFileSync(path.resolve(__dirname, 'globals.css'), 'utf8')

/**
 * 선택자를 쓰다 말고 **절이 시작된** 자리의 줄 번호.
 *
 * ⚠️ 목록 중간의 주석 자체는 괜찮다 — `.a,\n/* 왜 *\/\n.b {` 는 목록이 이어지므로
 * 뜻대로 된다(이 파일에 그렇게 쓴 곳이 넷 있다). 망가진 두 번은 모두 주석이
 * **절 머리**(`/* ──`)이거나 **뒤에 빈 줄**이 있었다 — 「여기서 끊긴다」고 쓴
 * 사람이 믿은 모양이다. 그 둘만 잡는다.
 */
function commentsInsideSelectors(css: string): number[] {
  const hits: number[] = []
  let pending = ''
  let line = 1
  for (let i = 0; i < css.length; i++) {
    const ch = css[i]
    if (ch === '/' && css[i + 1] === '*') {
      const end = css.indexOf('*/', i + 2)
      const stop = end === -1 ? css.length : end + 2
      const header = /^\/\*\s*──/.test(css.slice(i, i + 12))
      const blankAfter = /^[ \t]*\n[ \t]*\n/.test(css.slice(stop))
      if (pending.trim() !== '' && (header || blankAfter)) hits.push(line)
      line += (css.slice(i, stop).match(/\n/g) ?? []).length
      i = stop - 1
      continue
    }
    if (ch === '\n') line++
    if (ch === '{' || ch === '}' || ch === ';') pending = ''
    else pending += ch
  }
  return hits
}

describe('globals.css', () => {
  it('선택자와 { 사이에 주석이 끼어 있지 않다', () => {
    expect(commentsInsideSelectors(CSS)).toEqual([])
  })

  // 검사 자체가 판별이 되는지 — 실제로 밟았던 두 모양을 넣어 본다.
  it('검사가 실제로 밟았던 모양을 잡는다', () => {
    // 2026-09-11 — 선택자 뒤에 절 머리
    expect(commentsInsideSelectors('.a /* ── 절 */\n\n.b {\n  color: red;\n}')).toEqual([1])
    // 2026-09-08 — 목록 쉼표 뒤에 절 주석, 빈 줄
    expect(commentsInsideSelectors('.a,\n/* 절 */\n\n.b {\n}')).toEqual([2])
    // 뜻대로 되는 것은 안 잡는다 — 목록 중간의 설명 · 몸통 안의 주석
    expect(commentsInsideSelectors('.a,\n/* 왜 */\n.b {\n}')).toEqual([])
    expect(commentsInsideSelectors('/* ── 절 */\n\n.a {\n  /* 값 */\n  color: red;\n}')).toEqual([])
  })
})
