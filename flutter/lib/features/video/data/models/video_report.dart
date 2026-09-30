/// 분석 리포트 — **화면이 쓰는 모양**이다(웹 `lib/savedReports.ts` 의
/// `SavedReport` 와 같은 자리).
///
/// 🔴 **모양을 바꾸는 일은 여기서만 한다.** 서버가 주는 것은 항목 배열
/// (`breakdown[]`)이고 화면이 그리는 것은 칭호+문장 짝 목록이다. 부르는 쪽은
/// 아래 것들만 알고 그 사이는 모른다.
///
/// 🔴 **이 값들을 카드 화면으로 옮기지 않는다**(부록 D.5 — 카드에 수치를 안
/// 그린다). 계약 3장 4 가 막은 것은 [summary] 문장 **안에** 숫자를 넣는 것이지
/// 오버롤이나 축 값 자체가 아니다.
class VideoReport {
  const VideoReport({
    required this.summary,
    required this.points,
    required this.scenes,
    required this.radar,
    required this.savedAt,
    this.totalScore,
    this.overallGrade,
  });

  /// 서버 응답 → 화면 모양.
  ///
  /// 🔴 **`skipped` 항목은 뺀다.** `grade: null` 과 짝이라 「평가 대상이
  /// 아니었다」는 뜻이고, 0 으로도 빈 문장으로도 그리면 **못한 것으로 읽힌다.**
  ///
  /// 🔴 **호칭은 `title_earned` 가 참인 것만 그린다**(CCC 47). `title` 은
  /// **모든 등급에 있다** — 0등급도 「무너지는 축」 같은 문구를 받는다. 유무로
  /// 선을 그으면 **못한 항목에 호칭을 달게 된다.** `title_earned` 가 `null`
  /// 이면 옛 리포트거나 제외된 항목이다 — 거짓으로 지어내지 않고 아무것도
  /// 안 그린다. 호칭이 없어도 그 항목의 문장은 **버리지 않는다.**
  factory VideoReport.fromJson(Map<String, dynamic> json) {
    final breakdown = (json['breakdown'] as List<dynamic>? ?? [])
        .cast<Map<String, dynamic>>()
        .where((b) => b['skipped'] != true)
        .toList();

    return VideoReport(
      summary: json['summary'] as String? ?? '',
      points: [
        for (final b in breakdown)
          if ((b['evidence'] as String?)?.isNotEmpty ?? false)
            ReportPoint(
              title: b['title_earned'] == true ? b['title'] as String? : null,
              evidence: b['evidence'] as String,
            ),
      ],
      scenes: [
        for (final s in (json['scenes'] as List<dynamic>? ?? [])
            .cast<Map<String, dynamic>>())
          ReportScene(
            at: atText((s['at_seconds'] as num?)?.toDouble() ?? 0),
            what: s['label'] as String? ?? '',
          ),
      ],
      radar: [
        for (final b in breakdown)
          if (b['stat'] != null)
            RadarAxis(
              name: b['name'] as String? ?? '',
              stat: (b['stat'] as num).toDouble(),
            ),
      ],
      totalScore: (json['total_score'] as num?)?.toDouble(),
      overallGrade: json['overall_grade'] as String?,
      savedAt: (json['analyzed_at'] as String? ?? '').split('T').first,
    );
  }

  final String summary;

  /// 항목별 **칭호+문장 짝**(`ho` 24번). 🔴 **따로 떼지 않는다** — 칭호 없이
  /// 문장만 있으면 선수는 그것이 칭찬인지 지적인지 모른다.
  final List<ReportPoint> points;

  /// 판단의 근거가 된 장면. 시각은 수치가 아니라 **찾아가는 자리**다.
  final List<ReportScene> scenes;

  /// 레이더 축 — 항목마다 이름 + `stat`(0~100). `skipped` 거나 `stat` 이
  /// 없는 항목은 뺀다(0 으로 그리면 「그 항목을 못했다」로 잘못 읽힌다).
  ///
  /// 🔴 **총점은 이 값들의 평균이 아니다** — 등급의 가중합이다.
  final List<RadarAxis> radar;

  /// 오버롤 — **영상 하나(= 분석 1회)의 값**이다(`ho` 28번). 여러 영상을 합친
  /// 것이 아니다. 옛 리포트(이 필드가 생기기 전 적재분)는 `null` 이라 그때는
  /// 오버롤 표시를 건너뛴다.
  final double? totalScore;
  final String? overallGrade;

  /// 분석한 날(`YYYY-MM-DD`). 언제 본 리포트인지는 알아야 한다.
  final String savedAt;
}

class ReportPoint {
  const ReportPoint({required this.title, required this.evidence});

  /// `null` 이면 **받은 호칭이 아니라는 뜻**이고, 그때도 문장은 그대로 그린다.
  final String? title;
  final String evidence;
}

class ReportScene {
  const ReportScene({required this.at, required this.what});

  /// `0:07` 꼴.
  final String at;
  final String what;
}

class RadarAxis {
  const RadarAxis({required this.name, required this.stat});

  final String name;
  final double stat;
}

/// `7.5` → `0:07`. 🔴 초는 **버림**이다 — 그 시각 *이후*를 가리켜야 장면이
/// 지나 있지 않다.
String atText(double seconds) {
  final total = seconds < 0 ? 0 : seconds.floor();
  return '${total ~/ 60}:${(total % 60).toString().padLeft(2, '0')}';
}

/// 리포트를 읽은 결과.
///
/// 🔴 **「아직」과 「없다」와 「실패」와 「고장」을 가른다.** 뭉치면 분석 중인
/// 클립이 결과 없는 클립처럼, 또는 **영영 안 될 실패가 마치 곧 될 것처럼**
/// 보인다 — 웹에서 사용자가 「다시 확인」을 무한 반복하는 것을 실제로 겪었다.
///
/// 🔴 **그래서 이 메서드만 `null` 이나 예외가 아니라 갈래를 돌려준다.** 계약이
/// 404 를 세 뜻으로 쓰기 때문이다(`REPORT_NOT_READY` · `ANALYSIS_FAILED` ·
/// `VIDEO_NOT_FOUND`).
sealed class ReportResult {
  const ReportResult();
}

class ReportReady extends ReportResult {
  const ReportReady(this.report);
  final VideoReport report;
}

/// 영상은 있는데 아직 적재 전 — 분석 중이다. **다시 물어보면 바뀔 수 있다.**
class ReportNotReady extends ReportResult {
  const ReportNotReady();
}

/// 분석이 실패로 끝났다 — **다시 물어봐도 절대 안 바뀐다.**
///
/// [reason] 은 서버가 실은 사람이 읽을 사유다(계약이 `ANALYSIS_FAILED` 에
/// 항상 싣는다). 🔴 기본 문구로 덮지 않는다.
class ReportFailed extends ReportResult {
  const ReportFailed(this.reason);
  final String reason;
}

/// 없는 영상이거나 남의 영상.
class ReportMissing extends ReportResult {
  const ReportMissing();
}

class ReportError extends ReportResult {
  const ReportError(this.message);
  final String message;
}
