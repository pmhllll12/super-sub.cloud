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

      <ul className="ss-report-traits">
        {report.traits.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>

      {/* 받은 호칭만 그린다. 못 받은 것을 미달 표식으로 남기지 않는다. */}
      {report.titles.length > 0 && (
        <ul className="ss-report-titles" aria-label="받은 호칭">
          {report.titles.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}

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
