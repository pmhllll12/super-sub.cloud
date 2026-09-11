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
import type { SavedReport } from '@/lib/savedReports'

export type ReportBody = Omit<SavedReport, 'savedAt'>

/**
 * 오버롤 레이더 — 항목마다 `stat`(0~100)을 축 삼아 다각형을 그린다.
 *
 * 🔴 축 개수는 루브릭이 정한다(4~6, 못 박지 않는다). 라벨을 SVG 안에 같이
 * 두면 한국어 길이가 제각각이라 겹친다 — 아래 범례로 따로 그린다.
 */
function ReportRadar({ axes }: { axes: { name: string; stat: number }[] }) {
  const n = axes.length
  if (n < 3) return null // 다각형이 안 되는 축 개수 — 그리지 않는다.

  const size = 200
  const center = size / 2
  const maxRadius = center - 24

  const pointAt = (i: number, radius: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2 // 12시 방향부터 시계 방향
    return { x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle) }
  }

  const polygon = axes
    .map((a, i) => {
      const p = pointAt(i, (Math.max(0, Math.min(100, a.stat)) / 100) * maxRadius)
      return `${p.x},${p.y}`
    })
    .join(' ')

  return (
    <div className="ss-report-radar">
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-hidden="true">
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
        <polygon points={polygon} className="ss-report-radar-shape" />
      </svg>
      <ul className="ss-report-radar-legend">
        {axes.map((a) => (
          <li key={a.name}>
            <span>{a.name}</span>
            <b>{Math.round(a.stat)}</b>
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
