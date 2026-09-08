import fs from 'node:fs'
import path from 'node:path'
import { FOCUS } from './rubricFocus'

/**
 * 🔴 **정본은 `agent/rubrics/*.yaml` 이다.** `rubricFocus.ts` 는 그 사본이고,
 * 사본은 조용히 갈린다 — 정상호 님이 루브릭에 항목을 더하거나 draft 를
 * 승격시켜도 화면은 모른다. 그러면 화면이 고른 것과 서버가 채점한 것이
 * 서로를 못 가리킨다.
 *
 * 그래서 **실제 파일을 읽어 대조한다.** 파서를 들이지 않고 필요한 줄만 본다 —
 * 이 대조에 필요한 것은 `status` · `motion_ko` · `criteria[].id`·`name` 뿐이고,
 * YAML 라이브러리를 www 에 들이면 그것만으로 의존성이 하나 는다.
 *
 * ⚠️ 이 시험은 **저장소 안의 다른 사람 폴더**를 읽는다. 그 폴더가 없는
 * 환경(www 만 떼어 배포하는 경우)에서는 건너뛴다 — 없다고 실패시키면
 * 그 환경에서 CI 가 통째로 막힌다.
 */
const RUBRICS = path.resolve(__dirname, '../../../agent/rubrics')
const has = fs.existsSync(RUBRICS)

/** 루브릭 한 장에서 이 대조에 필요한 것만 꺼낸다. */
function readRubric(file: string) {
  const text = fs.readFileSync(path.join(RUBRICS, file), 'utf8')
  const one = (key: string) => text.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'))?.[1].trim()
  // `criteria:` 부터 다음 최상위 키 전까지 — `deferred:` 는 여기서 끊긴다.
  const block = text.match(/^criteria:$([\s\S]*?)^(?=\S)/m)?.[1] ?? ''
  const items: { id: string; name: string }[] = []
  for (const m of block.matchAll(/^\s+- id:\s*(\S+)\s*$\n\s+name:\s*(.+)$/gm)) {
    items.push({ id: m[1], name: m[2].trim() })
  }
  return { status: one('status'), motion: one('motion_ko'), items }
}

describe.runIf(has)('무엇을 볼지 — 루브릭과 어긋나지 않는다', () => {
  it.each(Object.entries(FOCUS))('%s 의 항목이 루브릭 그대로다', (_sport, focus) => {
    const rubric = readRubric(`${focus.rubric}.yaml`)

    // 🔴 열린 것만 싣는다 — 루브릭이 스스로 적어 둔 규칙이다.
    expect(rubric.status).toBe('active')
    expect(focus.motion).toBe(rubric.motion)

    // 🔴 id 도 이름도 **글자까지** 같아야 한다. 갈리면 화면이 고른 것과 서버가
    //    채점한 것이 서로를 못 가리킨다.
    expect(focus.items).toEqual(rubric.items.map((i) => ({ id: i.id, label: i.name })))
  })

  // 🔴 draft 가 승격되면 그 종목의 열린 동작이 둘이 된다 — 그때는 이 사본만
  //    고쳐서는 안 되고 화면이 동작부터 고르게 해야 한다(미결 jin 17번).
  it('종목마다 열린 루브릭이 정확히 하나다', () => {
    const open = new Map<string, string[]>()
    for (const f of fs.readdirSync(RUBRICS).filter((f) => f.endsWith('.yaml'))) {
      const text = fs.readFileSync(path.join(RUBRICS, f), 'utf8')
      if (!/^status:\s*active\s*$/m.test(text)) continue
      const sport = text.match(/^sport:\s*(\S+)$/m)![1]
      open.set(sport, [...(open.get(sport) ?? []), f])
    }
    for (const [sport, files] of open) {
      expect(files, `${sport} 의 열린 루브릭`).toHaveLength(1)
    }
    // 화면이 아는 종목 셋이 다 열려 있어야 한다.
    expect([...open.keys()].sort()).toEqual(['baseball', 'basketball', 'football'])
  })
})
