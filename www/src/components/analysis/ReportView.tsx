/**
 * 분석 리포트를 그리는 **한 벌**.
 *
 * 🔴 분석 화면(`AnalysisStage`)과 내 프로필(`MyVideos`)이 **같은 것을 부른다.**
 * 두 벌로 두면 한쪽만 늙는다 — 업로드를 `lib/uploadClip.ts` 로 뺀 것과 같은
 * 판단이다.
 *
 * 🔴 **정정 (CCC 32)**: 여기가 앞서 "수치를 그리지 않는다"고 적었던 것은
 * `player_card` 화면(부록 D.5 — `PlayerCardView.test.tsx` 가 그쪽을 지킨다)과
 * 헷갈린 것이었다. **이 리포트 화면은 총점·오버롤 등급·레이더를 그린다** —
 * 계약이 막은 것은 `summary` 문장 안에 숫자를 넣는 것뿐이다. 카드 화면으로는
 * 여전히 이 값들을 옮기지 않는다.
 */
import { useId } from 'react'
import type { SavedReport } from '@/lib/savedReports'

/**
 * 축의 색 — **차례가 고정**이고 돌려 쓰지 않는다(`globals.css` 의
 * `--ss-axis-*`). 여섯을 넘는 루브릭이 오면 색을 새로 만드는 것이 아니라
 * 그 판을 다시 설계해야 한다 — 지어낸 색은 앞엣것과 구별된다는 보장이 없다.
 *
 * ⚠️ 그래서 여기서 **나머지 연산으로 돌리지 않는다.** 넘치는 축은 마지막
 * 색을 쓰되(아래 `axisColor`) 번호가 그 둘을 가른다 — 색만으로 말하지 않는
 * 것이 이 화면의 원칙이라 그래도 읽을 수 있다.
 *
 * ## 여섯이면 지금은 충분하다 — 다만 영원히는 아니다 (2026-09-11 실측)
 *
 * `agent/rubrics/*.yaml` 의 `criteria:` 블록을 세어 본 값이다.
 *
 * | 루브릭 | 항목 |
 * |---|---|
 * | 농구 레이업 | 4 |
 * | 야구 타격 · 야구 투구 · 농구 점프슛 · 축구 인사이드 패스 | 5 |
 * | **축구 인스텝 슛** | **6** ← 지금 쓰는 종목, 상한 |
 *
 * 🔴 **축구 인스텝 슛에는 `deferred:` 로 빠진 항목이 둘 더 있다**(임팩트 지점 ·
 * 스윙 가속 타이밍). **공 검출기가 붙으면 활성화되고, 그러면 8축이 된다.**
 * 그때 색 둘을 더 뽑아야 하는데 — 🔴 **지금 미리 만들어 두면 안 된다.**
 * 여덟이 색각 이상에서 서로 구별되는지는 **여덟을 다 놓고 재야** 알 수 있고,
 * 둘을 얹으면 기존 여섯의 간격도 다시 재야 한다. 그때 `dataviz` 검사를
 * 여덟으로 다시 돌릴 것.
 *
 * ⚠️ `- id:` 를 그냥 세면 7~10 이 나온다 — `deferred:` 절과 `bands:` 안의
 * 예시까지 걸린다. `criteria:` 블록 **안만** 세는 것이 맞다.
 */
const AXIS_COLORS = 6

function axisColor(i: number): string {
  return `var(--ss-axis-${Math.min(i + 1, AXIS_COLORS)})`
}

/**
 * 번호 원의 **속** — 축 색 위에 검정을 겹쳐 어둡게 깐다.
 *
 * 🔴 꽉 채우면 안 된다. 여섯 색은 밝기가 제각각이라(초록은 어둡고 노랑은
 * 밝다) 꽉 채우면 흰 숫자가 밝은 색 위에서 안 읽힌다 — 어둡게 깔면 **어느
 * 색이 와도** 읽히고 색은 여전히 보인다.
 */
function axisFill(i: number): string {
  return `color-mix(in srgb, ${axisColor(i)} 30%, #000)`
}

/**
 * 값 글자에 쓰는 축 색 — **흰 쪽으로 올린 것**이다.
 *
 * 🔴 계열 색을 작은 글자에 그대로 쓰면 대비가 무너진다(어두운 축 색일수록
 * 심하다). 사용자가 「값도 그 색으로」라고 요청한 자리라 색은 살리되,
 * 읽히게 밝은 쪽으로 섞는다 — 이 파일이 민트를 흰 바탕에 올렸다 데인 것과
 * 같은 종류의 문제다.
 */
function axisInk(i: number): string {
  return `color-mix(in srgb, ${axisColor(i)} 62%, var(--ss-fg))`
}

export type ReportBody = Omit<SavedReport, 'savedAt'>

/**
 * 오버롤 레이더 — 항목마다 `stat`(0~100)을 축 삼아 다각형을 그린다.
 *
 * 🔴 축 개수는 루브릭이 정한다(4~6, 못 박지 않는다). **이름을 축 끝에 놓지
 * 않는다** — 한국어 이름은 길이가 제각각이라 6축에서 서로 파고든다.
 *
 * 🔴 대신 **번호로 잇는다**(2026-09-11, 사용자 요청). 그전에는 축 끝이
 * 비어 있어서 어느 꼭짓점이 어느 이름인지 알 길이 없었다 — 범례에 이름이
 * 다 적혀 있어도 **그림과 이어지지 않으면 읽히지 않는다.** 번호는 한 글자라
 * 길이가 일정해서 **겹침이 구조적으로 안 생긴다**(이름을 놓으면 각도마다
 * 정렬을 달리해 가며 관리해야 하는 문제가, 여기서는 아예 없다).
 */
function ReportRadar({ axes }: { axes: { name: string; stat: number }[] }) {
  /* 🔴 **그러데이션 id 는 화면에서 단 하나여야 한다.** 분석 화면과 내
     프로필이 같은 컴포넌트를 쓰므로 붙박이 id 를 주면 둘이 겹쳐, 나중에
     그려진 쪽의 색이 먼저 것에도 먹는다. */
  const uid = useId().replace(/:/g, '')
  const n = axes.length
  if (n < 3) return null // 다각형이 안 되는 축 개수 — 그리지 않는다.

  const size = 200
  const center = size / 2
  /* 🔴 번호 원이 축 끝 **바깥**에 앉으므로 그만큼 그림을 안으로 들인다.
     안 그러면 12시·6시 번호가 viewBox 밖으로 잘린다(`overflow` 는 SVG 기본이
     hidden 이라 조용히 사라진다). 24 → 34 는 원 반지름 9 + 사이 1 이다. */
  const maxRadius = center - 34
  /** 번호 원의 중심 — 축 끝에서 한 뼘 더 바깥. */
  const numRadius = maxRadius + 11

  const pointAt = (i: number, radius: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2 // 12시 방향부터 시계 방향
    return { x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle) }
  }

  /** 값이 앉는 꼭짓점들. 변의 그러데이션도 이 좌표에서 만든다. */
  const verts = axes.map((a, i) =>
    pointAt(i, (Math.max(0, Math.min(100, a.stat)) / 100) * maxRadius),
  )
  const polygon = verts.map((p) => `${p.x},${p.y}`).join(' ')

  /* 🔴 **상자를 그려진 것에 맞춰 자른다.** 정사각으로 두면 축 개수가 홀수일
     때 아래가 빈다 — 삼각형은 위로 뾰족하고 아래는 평평한 밑변이라, 원에
     내접시켜도 잉크가 위로 쏠린다(3축에서 아래 52단위가 늘 비었다). 상자만
     가운데 있고 그림은 안 그런 상태라, 위아래 가로선과의 간격이 어긋나
     보였다(사용자 지적).

     ⚠️ 바깥 끝은 **번호 원**이다 — 축선(`maxRadius`)보다 바깥에 앉는다.
     테두리 반 칸까지 넣어 `PAD` 로 둔다. */
  const PAD = 10
  const numPoints = axes.map((_, i) => pointAt(i, numRadius))
  const minX = Math.min(...numPoints.map((p) => p.x)) - PAD
  const maxX = Math.max(...numPoints.map((p) => p.x)) + PAD
  const minY = Math.min(...numPoints.map((p) => p.y)) - PAD
  const maxY = Math.max(...numPoints.map((p) => p.y)) + PAD
  const boxW = maxX - minX
  const boxH = maxY - minY

  return (
    <div className="ss-report-radar">
      {/* 🔴 그림을 **제 칸의 가운데**에 둔다(사용자 요청). 감싸는 상자 없이
          두면 `justify-content: center` 가 그림+범례를 **한 덩어리로** 가운데
          두어서, 그림만 보면 오른쪽으로 치우친다. */}
      <div className="ss-report-radar-chart">
      {/* 🔴 `width`·`height` 를 viewBox 와 **같은 비**로 준다 — 정사각으로
          두면 잘라 낸 만큼 그림이 늘어난다. */}
      <svg
        viewBox={`${minX} ${minY} ${boxW} ${boxH}`}
        width={boxW}
        height={boxH}
        role="img"
        aria-hidden="true"
      >
        {/* 기준선 — 축마다 중심에서 바깥까지. 참고용이라 값은 없다. */}
        {axes.map((_, i) => {
          const edge = pointAt(i, maxRadius)
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={edge.x}
              y2={edge.y}
              className="ss-report-radar-axis"
            />
          )
        })}
        {/* 🔴 **채움과 변을 나눴다.** 변마다 색이 갈리므로 `polygon` 의
            `stroke` 하나로는 못 그린다 — 채움만 남기고 변은 따로 얹는다.
            채움은 **중립**이다: 여섯 색이 도는 판에서 채움까지 색을 가지면
            어느 색이 어느 축인지가 흐려진다. */}
        <polygon points={polygon} className="ss-report-radar-shape" />

        <defs>
          {verts.map((p, i) => {
            const q = verts[(i + 1) % n]
            return (
              /* 🔴 `userSpaceOnUse` — 기본값(`objectBoundingBox`)은 그 선의
                 **상자**를 기준으로 삼아서, 가로세로 어느 한쪽이 0 인 변
                 (똑바로 선 변)에서 그러데이션이 통째로 사라진다. */
              <linearGradient
                key={i}
                id={`${uid}-e${i}`}
                gradientUnits="userSpaceOnUse"
                x1={p.x}
                y1={p.y}
                x2={q.x}
                y2={q.y}
              >
                <stop offset="0%" stopColor={axisColor(i)} />
                <stop offset="100%" stopColor={axisColor((i + 1) % n)} />
              </linearGradient>
            )
          })}
        </defs>

        {verts.map((p, i) => {
          const q = verts[(i + 1) % n]
          return (
            <line
              key={i}
              x1={p.x}
              y1={p.y}
              x2={q.x}
              y2={q.y}
              className="ss-report-radar-edge"
              stroke={`url(#${uid}-e${i})`}
            />
          )
        })}

        {/* 🔴 번호는 **다각형 위에** 그린다 — 먼저 그리면 채움에 덮인다.
            그리고 원을 깔고 그 위에 글자를 얹는다: 축선이 번호를 가로지르면
            한 자리 숫자도 안 읽힌다. */}
        {axes.map((_, i) => {
          const p = pointAt(i, numRadius)
          return (
            <g key={i}>
              {/* 🔴 **색은 고리가 입고 글자는 흰색이다.** 값·라벨에 계열 색을
                  입히면 작은 글자에서 대비가 무너진다 — 색은 그 옆의 표식이
                  들고 글자는 글자 색을 그대로 쓴다. */}
              <circle
                cx={p.x}
                cy={p.y}
                r="9"
                className="ss-report-radar-numdot"
                stroke={axisColor(i)}
                fill={axisFill(i)}
              />
              <text
                x={p.x}
                y={p.y}
                className="ss-report-radar-num"
                textAnchor="middle"
                dominantBaseline="central"
              >
                {i + 1}
              </text>
            </g>
          )
        })}
      </svg>
      </div>
      <ul className="ss-report-radar-legend">
        {axes.map((a, i) => (
          <li key={a.name}>
            {/* 🔴 그림의 번호와 **같은 글자**다. 정렬하거나 뒤섞으면 짝이
                깨진다 — 시험이 순서를 붙든다. */}
            <span
              className="ss-report-radar-num"
              style={
                { borderColor: axisColor(i), background: axisFill(i) } as React.CSSProperties
              }
            >
              {i + 1}
            </span>
            <span className="ss-report-radar-name">{a.name}</span>
            {/* 🔴 값도 그 축의 색을 입는다(사용자 요청) — 다만 **흰 쪽으로
                올린 값**이다(`axisInk`). 계열 색을 작은 글자에 그대로 쓰면
                어두운 축에서 안 읽힌다. */}
            <b style={{ color: axisInk(i) } as React.CSSProperties}>{Math.round(a.stat)}</b>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ReportView({ report }: { report: ReportBody }) {
  return (
    <div className="ss-report">
      {/* 오버롤 — 옛 리포트(이 필드가 생기기 전 적재분)는 total_score·grade
          가 null 이라 건너뛴다. "이 선수의" 가 아니라 이 클립의 오버롤이다. */}
      {report.overallGrade !== null && (
        <div className="ss-report-overall">
          <span className="ss-report-grade-chip">{report.overallGrade}</span>
          {report.totalScore !== null && (
            <span className="ss-report-total-score">{Math.round(report.totalScore)}점</span>
          )}
        </div>
      )}

      <p className="ss-report-summary">{report.summary}</p>

      {/* 🔴 칭호와 문장을 항목마다 짝으로 그린다(`ho` 24번) — 따로 떼면
          선수가 그 문장을 칭찬인지 지적인지 모른다. 칭호가 없는 항목도
          있다(호칭은 서버가 채운 것만이다) — 그때는 문장만 그린다. */}
      <ul className="ss-report-points">
        {report.points.map((p, i) => (
          <li key={i} className="ss-report-point">
            {p.title && <span className="ss-report-point-title">{p.title}</span>}
            <p className="ss-report-point-evidence">{p.evidence}</p>
          </li>
        ))}
      </ul>

      {report.radar.length > 0 && <ReportRadar axes={report.radar} />}

      <h3>이렇게 본 장면</h3>
      <ul className="ss-report-scenes">
        {report.scenes.map((s) => (
          <li key={s.at}>
            <b>{s.at}</b>
            {s.what}
          </li>
        ))}
      </ul>
    </div>
  )
}
