/**
 * 분석 리포트를 그리는 **한 벌**.
 *
 * 🔴 분석 화면(`AnalysisStage`)과 내 프로필(`MyVideos`)이 **같은 것을 부른다.**
 * 두 벌로 두면 한쪽만 늙는다 — 업로드를 `lib/uploadClip.ts` 로 뺀 것과 같은
 * 판단이다.
 *
 * 🔴 **수치를 그리지 않는다.** 계약 3장 4 · 부록 D.5 의 원칙이고, 화면 쪽
 * 검사는 `PlayerCardView.test.tsx` 가 들고 있다.
 */
import type { SavedReport } from '@/lib/savedReports'

export type ReportBody = Omit<SavedReport, 'savedAt'>

export default function ReportView({ report }: { report: ReportBody }) {
  return (
    <div className="ss-report">
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
