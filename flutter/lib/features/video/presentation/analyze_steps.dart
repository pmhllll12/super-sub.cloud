/// 분석 화면의 **진행 단계** — 웹 `www/src/lib/analysisSteps.ts` 를 그대로 옮긴 것.
///
/// 🔴 **정본은 `agent/scripts/analyze_s3.py` 다.** 워커가 그 스크립트를 돌리고,
/// 스크립트는 `[입력]` → `[측정]` → `[판정]` → 미리보기 · `저장:` 순서로 간다.
/// ⛔ **제안서에 있던 「전처리」·「근거 검증」을 되살리지 말 것** — 그런 단계가
/// 실제로 없다(웹이 그 이름을 먼저 놓았다가 걷어냈다).
///
/// 🔴 **어느 칸이 켜지는지는 추정이다.** 워커가 단계별로 보고하는 경로가 없어서
/// (`agent/scripts/worker.py` 는 끝났을 때만 보고한다) 화면은 지금 어느 단계인지
/// **모른다.** 칸은 [AnalyzeStep.estimate] 로 넘어가고, **진짜인 것은 첫 칸
/// (업로드가 끝났다)과 끝(서버가 준 리포트·실패)뿐**이다.
///
/// ⚠️ **웹과 한 벌이다.** 문구나 순서를 여기서만 고치면 두 화면이 다른 말을
/// 한다 — 고칠 일이 있으면 `analysisSteps.ts` 도 같이 본다.
library;

class AnalyzeStep {
  const AnalyzeStep({
    required this.label,
    required this.note,
    required this.estimate,
  });

  final String label;
  final String note;

  /// 이 칸에 머무는 시간. 🔴 **`null` 이면 시간으로 안 넘긴다** — 첫 칸은
  /// 업로드가 끝나야, 마지막 칸은 서버가 끝났다고 해야 넘어간다.
  final Duration? estimate;
}

/// ⚠️ 시간 출처: EC2 GPU 에서 `analyze_s3.py` 한 바퀴의 `timing`
/// (`fetch_s 1.04 · measure_s 32.78 · judge_s 16.75`). **영상 한 편의 값**이라
/// 실서버 리포트의 `timing` 이 쌓이면 평균으로 바꾼다.
const List<AnalyzeStep> kAnalyzeSteps = [
  AnalyzeStep(
    label: '영상 등록',
    note: '클립을 올리고 분석 작업을 만듭니다',
    estimate: null,
  ),
  AnalyzeStep(
    label: '영상 받기',
    note: '분석 서버가 올린 영상을 내려받습니다',
    estimate: Duration(seconds: 1),
  ),
  AnalyzeStep(
    label: '자세 측정',
    note: '사람과 관절을 찾고, 축구 영상인지 확인합니다',
    estimate: Duration(seconds: 33),
  ),
  AnalyzeStep(
    label: '판정 · 근거',
    note: '루브릭으로 항목을 판정하고 근거 문장을 씁니다',
    estimate: Duration(seconds: 17),
  ),
  AnalyzeStep(
    label: '미리보기 · 저장',
    note: '장면 미리보기를 만들고 리포트를 올립니다',
    estimate: null,
  ),
];

/// 서버가 추정보다 **먼저** 끝났을 때 남은 칸을 채우는 간격.
///
/// 🔴 **칸을 건너뛰고 곧장 리포트를 띄우지 않는다** — 중간 칸이 켜진 채 리포트가
/// 뜨면 「측정하다 말았다」로 읽힌다.
/// 🔴 **실패에는 쓰지 않는다** — 종목 불일치는 측정에서 멈춘 것이라 끝까지
/// 채우면 거짓이 된다. 실패는 곧바로 사유를 보여 준다.
const Duration kFinishStep = Duration(milliseconds: 250);

/// 리포트를 다시 물어보는 간격 — 웹과 같은 4초.
///
/// 🔴 **끝났는지는 이 폴링만이 정한다.** 위 추정은 칸을 넘길 뿐이다.
const Duration kPollEvery = Duration(seconds: 4);
