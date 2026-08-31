/**
 * 선수 카드 뒤에 깔리는 검은 붓자국 — 참고 디자인(NFL 카드)에서 인물 뒤를
 * 대각선으로 지나가는 그 자국이다.
 *
 * 🔴 **Math.random() 을 쓰지 않는다.** 이 카드는 서버에서 한 번 그려지고
 * 브라우저에서 다시 그려지는데, 매번 다른 수가 나오면 두 결과가 달라
 * 하이드레이션이 깨진다(React 가 콘솔에 경고를 쏟고 화면이 한 번 튄다).
 * 대신 카드의 public_slug 를 씨앗으로 삼는다 — **사람마다 다르고, 같은
 * 사람에게는 늘 같은** 모양이 나온다. 새로고침해도 안 바뀐다.
 *
 * 붓 한 자국은 몸통 하나 + 그 옆을 스치는 가는 결 몇 개로 만든다. 몸통만
 * 그리면 그냥 기울어진 막대로 보인다 — 끝이 가늘어지는 것(taper)과 결이
 * 있어야 붓으로 읽힌다.
 */

/** 문자열 → 32비트 정수. 씨앗을 만드는 용도라 암호학적 성질은 필요 없다. */
function hash(text: string): number {
  let h = 2166136261
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

/** mulberry32 — 씨앗 하나로 늘 같은 수열을 뱉는 작은 난수기. */
function rng(seed: number): () => number {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * 붓자국 하나의 윤곽. 길이 `len`, 가운데 두께 `thick` 인 가로 막대를
 * 위·아래 가장자리를 흔들어 가며 그린다. 양 끝은 가늘어진다 — 붓이
 * 닿고 떨어지는 자리다.
 */
function strokePath(len: number, thick: number, next: () => number): string {
  const STEPS = 14
  const top: string[] = []
  const bottom: string[] = []
  for (let i = 0; i <= STEPS; i += 1) {
    const t = i / STEPS
    const x = t * len
    // 양 끝으로 갈수록 0에 가까워지는 두께. 시작 쪽을 더 뾰족하게 둔다.
    const taper = Math.sin(Math.PI * t) ** 0.55 * (0.72 + 0.28 * t)
    const half = (thick / 2) * taper
    const wobble = (next() - 0.5) * thick * 0.16
    top.push(`${x.toFixed(2)},${(-half + wobble).toFixed(2)}`)
    bottom.push(`${x.toFixed(2)},${(half + wobble * 0.6).toFixed(2)}`)
  }
  return `M${top.join(' L')} L${bottom.reverse().join(' L')} Z`
}

export default function PlayerCardBrush({ seed }: { seed: string }) {
  const next = rng(hash(seed))
  const COUNT = 3

  const strokes = Array.from({ length: COUNT }, (_, i) => {
    // 왼쪽 아래에서 오른쪽 위로 지나간다(참고 디자인과 같은 방향).
    // 값 범위는 viewBox(100×140) 기준이다.
    //
    // 🔴 **자국의 위쪽 끝이 카드 절반(y=70)을 넘으면 안 된다.** 그 위는
    // 워드마크와 별명의 자리다. 눈대중으로 줄이다 두 번 덮었어서, 이제
    // 범위를 계산해서 잡는다: 올라가는 높이 = len × sin(angle) 이므로
    // 최악의 경우(len 80, angle 38°)에도 80×0.616 ≈ 49 만 오른다.
    // 시작 y 를 122 아래로 두면 위쪽 끝은 73 언저리에 머문다.
    const angle = -(28 + next() * 10)
    const len = 55 + next() * 25
    const thick = 3.5 + next() * 3.5
    const x = -8 + next() * 24 + i * 10
    const y = 122 + next() * 12
    return {
      key: i,
      transform: `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${angle.toFixed(1)})`,
      body: strokePath(len, thick, next),
      // 몸통 옆을 스치는 가는 결. 몸통보다 길게 빼야 끌린 자국으로 보인다.
      bristles: Array.from({ length: 2 + Math.floor(next() * 2) }, () => ({
        dy: (next() - 0.5) * thick * 1.7,
        path: strokePath(len * (0.7 + next() * 0.45), 0.9 + next() * 1.1, next),
      })),
    }
  })

  return (
    <svg
      className="ss-pcard-brush"
      viewBox="0 0 100 140"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
    >
      {strokes.map((s) => (
        <g key={s.key} transform={s.transform}>
          <path d={s.body} />
          {s.bristles.map((b, i) => (
            <path key={i} d={b.path} transform={`translate(0 ${b.dy.toFixed(2)})`} opacity="0.75" />
          ))}
        </g>
      ))}
    </svg>
  )
}
