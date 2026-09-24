import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/clip_file.dart';
import '../data/models/video_report.dart';
import '../data/pick_clip.dart';
import '../data/video_providers.dart';
import 'analyze_steps.dart';
import 'my_videos_controller.dart';

/// 「영상 분석」 화면의 상태 — 🔴 **고르기부터 리포트까지 한 줄기다.**
///
/// ⚠️ **`AsyncValue` 로 두지 않는다.** 이 흐름에는 「아직」이 여럿이고
/// (올리는 중 · 분석 중 · 반려 · 실패) 그 넷이 **화면에서 서로 다른 그림**이다.
/// 로딩·오류 둘로 뭉치면 반려 사유와 실패 사유가 같은 자리에 떨어진다.
sealed class AnalyzeState {
  const AnalyzeState();
}

/// 아직 아무것도 안 골랐다 — 큰 제목과 고르는 자리가 보이는 상태.
class AnalyzeIdle extends AnalyzeState {
  const AnalyzeIdle({this.notice});

  /// 고르다 만 것이 아니라 **막힌 것**일 때의 사유(형식·용량).
  final String? notice;
}

/// 골랐고 아직 안 보냈다 — 미리보기와 「분석 시작하기」가 보이는 상태.
class AnalyzePicked extends AnalyzeState {
  const AnalyzePicked(this.clip);
  final PickedClip clip;
}

/// 올리는 중 · 분석 중. [step] 은 [kAnalyzeSteps] 의 자리다.
class AnalyzeRunning extends AnalyzeState {
  const AnalyzeRunning({
    required this.clip,
    required this.step,
    this.videoId,
    this.asked = 0,
    this.lastAnswer,
  });

  final PickedClip clip;
  final int step;

  /// 등록이 끝나야 생긴다 — 그 전에는 `null`.
  final String? videoId;

  /* 🔴 **여기 둘은 화면에 드러내는 증거다** (2026-09-25). 「리포트가 아예 안
     나온다」는 말을 들었을 때, 화면이 **몇 번 물었고 서버가 뭐라 했는지**를
     안 보여 주면 폴링이 도는지 멈췄는지조차 못 가른다 — 폰 로그를 못 볼 때가
     많아서 더 그렇다. 작게, 흐리게 둔다. */
  final int asked;
  final String? lastAnswer;
}

/// 🔴 **규격 반려** — 분석 작업이 아예 안 만들어진 상태다(계약은 `201`).
/// 실패와 다르다: 사람이 다른 영상을 고르면 된다.
class AnalyzeRejected extends AnalyzeState {
  const AnalyzeRejected({required this.clip, required this.reason});
  final PickedClip clip;
  final String reason;
}

class AnalyzeDone extends AnalyzeState {
  const AnalyzeDone({
    required this.clip,
    required this.videoId,
    required this.report,
    required this.analysisVideoId,
    this.keep = KeepState.none,
    this.keepNotice,
    this.borrowed = false,
  });

  final PickedClip clip;

  /// 🔴 **저장을 거는 id** — 방금 올린 이 클립이다(계약 2150절: 중복 클립도
  /// `kept:false` 로 시작하고 **자기 id** 로 `keep` 을 부른다).
  final String videoId;

  /// 🔴 **분석 결과가 달린 id** — 중복이면 **원본**이고, 아니면 [videoId] 와
  /// 같다.
  ///
  /// 🔴 **둘을 섞지 말 것** (2026-09-25 에 실제로 섞었다). 리포트는 원본에서
  /// 가져왔는데 **관절만 새 클립 id 로 물어서** 영영 안 떴다 — 그 클립엔 분석
  /// 작업이 없어 `REPORT_NOT_READY` 만 온다. 오류가 안 나고 **그냥 안 그려져서**
  /// 눈으로만 알 수 있었다.
  final String analysisVideoId;

  final VideoReport report;

  /// 프로필에 저장했는가 — 🔴 **안 하면 서버가 지운다**(아래 [KeepState]).
  final KeepState keep;

  /// 저장이 막힌 사유(갈래마다 3개 상한 등).
  final String? keepNotice;

  /// 🔴 **전에 낸 결과를 빌려온 것인가**(같은 영상 재업로드, 계약 2129절).
  /// 화면이 이걸 안 알리면 **방금 분석한 줄 안다** — 2초 만에 리포트가 뜨는
  /// 것이 오히려 수상해 보인다(2026-09-25 사용자 요청).
  final bool borrowed;

  AnalyzeDone with_({KeepState? keep, String? keepNotice}) => AnalyzeDone(
        clip: clip,
        videoId: videoId,
        analysisVideoId: analysisVideoId,
        report: report,
        keep: keep ?? this.keep,
        keepNotice: keepNotice,
        borrowed: borrowed,
      );
}

/// 🔴 **분석한 클립은 저장해야 남는다.** `analyze: true` 로 등록한 클립은
/// `kept: false` 로 시작해서 **본인 목록에도 안 뜨고**, 화면을 벗어나면 서버의
/// TTL 백스톱이 지운다(계약 3-6절). 저장 단추가 그 유일한 출구다.
enum KeepState { none, saving, saved, failed }

/// 🔴 **분석 실패 — 다시 물어도 안 바뀐다.** 재시도 단추를 주지 않는다.
class AnalyzeFailed extends AnalyzeState {
  const AnalyzeFailed({required this.clip, required this.reason});
  final PickedClip clip;
  final String reason;
}

/// 올리다 터진 것 · 네트워크 — 다시 해 볼 수 있다.
class AnalyzeError extends AnalyzeState {
  const AnalyzeError({required this.clip, required this.message});
  final PickedClip? clip;
  final String message;
}

/// 🔴 **종목을 묻지 않는다** — `my_videos_screen.dart` 와 같은 값이다.
/// 되살리려면 **고르는 자리를 같이** 되살려야 한다(안 그러면 다른 종목이
/// 축구 루브릭으로 조용히 채점된다).
const String kAnalyzeSportCode = 'football';

/// 고르기 → 올리기(분석 요청) → 진행 → 리포트.
///
/// 🔴 **여기가 앱에서 처음으로 `analyze: true` 를 보내는 자리다.** 지금까지
/// 앱이 올린 것은 전부 「업로드 영상」이었다(`analyze` 를 아무도 안 넘겼다).
class AnalyzeController extends Notifier<AnalyzeState> {
  /// 칸을 시간으로 넘기는 시계 — 🔴 **추정이다**([kAnalyzeSteps] 머리말).
  Timer? _stepTimer;

  /// 끝났는지 묻는 시계 — 🔴 **이것만이 끝을 정한다.**
  Timer? _poll;

  /// 화면 밖에서 만든 것을 끼워 넣을 자리 — 시험이 쓴다.
  ClipPicker _picker = ClipPicker();

  @override
  AnalyzeState build() {
    ref.onDispose(_stopTimers);
    return const AnalyzeIdle();
  }

  /// 🔴 시험이 진짜 앨범을 못 여니 갈아 끼운다.
  // ignore: use_setters_to_change_properties
  void usePicker(ClipPicker picker) => _picker = picker;

  void _stopTimers() {
    _stepTimer?.cancel();
    _poll?.cancel();
    _stepTimer = null;
    _poll = null;
  }

  /// 앨범이나 카메라에서 고른다.
  ///
  /// 🔴 **고르다 만 것은 오류가 아니다** — 아무 일도 안 일어난다.
  Future<void> pick({required bool camera}) async {
    _stopTimers();
    final PickedClip? picked;
    try {
      picked = camera
          ? await _picker.fromCamera()
          : await _picker.fromGallery();
    } catch (e) {
      state = AnalyzeIdle(notice: '영상을 고르지 못했습니다: $e');
      return;
    }
    if (picked == null) return;

    /* 🔴 **형식·용량만 여기서 막는다** — 그 둘은 `upload-url` 이 422 로 튕겨
       **아무 데도 안 남는다.** 길이·해상도는 반대로 서버가 반려 사유로
       남겨야 하는 것이라(SFR-001) 가로채지 않는다. */
    final bad = checkClip(picked.file);
    if (bad != null) {
      state = AnalyzeIdle(notice: bad);
      return;
    }
    state = AnalyzePicked(picked);
  }

  /// **프로필에 저장한다** — 영상과 리포트를 함께 남긴다.
  ///
  /// 🔴 **리포트가 나온 뒤에만 부를 수 있다.** 실패·반려로 끝났으면 남길 것이
  /// 없다(서버도 그 자리에서 줄 리포트가 없다).
  Future<void> keep() async {
    final s = state;
    if (s is! AnalyzeDone || s.keep == KeepState.saving) return;
    // 이미 저장했으면 다시 안 부른다(계약상 멱등이지만 왕복이 아깝다).
    if (s.keep == KeepState.saved) return;

    state = s.with_(keep: KeepState.saving);
    try {
      await ref.read(videoRepositoryProvider).keepVideo(s.videoId);
    } catch (e) {
      /* 🔴 **사유를 그대로 보여 준다** — 「갈래마다 3개」 상한이 여기서 막는
         대표적인 자리다(`422 VIDEO_LIMIT_EXCEEDED`). 기본 문구로 덮으면 왜
         저장이 안 되는지 알 수가 없다. */
      state = s.with_(keep: KeepState.failed, keepNotice: '$e');
      return;
    }
    /* 🔴 **목록을 다시 받게 한다** — 저장한 것이 「내 영상」에 바로 보여야
       한다. 안 그러면 프로필에 갔을 때 없는 것처럼 보인다. */
    ref.invalidate(myVideosProvider);
    state = s.with_(keep: KeepState.saved);
  }

  /// **분석을 그만둔다** (2026-09-25 사용자 요청). 🔴 **서버 작업까지 멈추지는
  /// 못한다** — 계약에 작업 취소 경로가 없다. 화면이 그만 기다리는 것뿐이고,
  /// 올라간 클립은 저장을 안 했으니 서버의 TTL 백스톱이 지운다.
  void cancel() {
    final s = state;
    if (s is! AnalyzeRunning) return;
    _stopTimers();
    // 고른 영상은 그대로 두고 「시작 전」으로 돌린다 — 다시 걸 수 있다.
    state = AnalyzePicked(s.clip);
  }

  /// 처음으로 돌아간다 — 다른 영상을 고르려고.
  void reset() {
    _stopTimers();
    state = const AnalyzeIdle();
  }

  /// 올리고 분석을 건다.
  Future<void> start() async {
    final s = state;
    if (s is! AnalyzePicked) return;
    final clip = s.clip;
    state = AnalyzeRunning(clip: clip, step: 0);

    final MyVideoLike saved;
    try {
      final row = await ref.read(videoRepositoryProvider).uploadClip(
            file: clip.file,
            meta: clip.meta,
            sportCode: kAnalyzeSportCode,
            // 🔴 **이 한 줄이 분석 작업을 만든다.**
            analyze: true,
          );
      saved = (
        id: row.id,
        passed: row.passed,
        reason: row.rejectReason,
        dupOf: row.duplicateOfVideoId,
        dupStatus: row.duplicateStatus,
        dupReason: row.duplicateFailureReason,
      );
    } catch (e) {
      state = AnalyzeError(clip: clip, message: '올리지 못했습니다: $e');
      return;
    }

    /* 🔴 **반려는 예외가 아니다**(계약은 `201`). 상태 코드가 아니라 `passed`
       로 가른다 — 예외로 만들면 **그 사유가 화면까지 못 온다.** */
    if (!saved.passed) {
      state = AnalyzeRejected(
        clip: clip,
        // 🔴 서버가 실은 사람이 읽을 사유를 **기본 문구로 덮지 않는다.**
        reason: saved.reason ?? '규격을 통과하지 못했습니다.',
      );
      return;
    }

    /* 🔴 **같은 영상을 다시 올리면 서버가 작업을 안 만든다** (계약 2129절,
       2026-09-25 사용자가 짚었다: 「똑같은 영상은 리포트 작성 안되게 되어있나」).

       분석이 결정론적이라 같은 결과가 나오는데 GPU·S3 만 쓰기 때문이다. 대신
       **이미 끝난 원본의 결과**를 등록 응답에 실어 준다.

       🔴 **여기서 안 받으면 영영 못 받는다.** 이 클립 자신은 `analysis_job_id`
       가 `null` 이라, 아래 폴링은 **끝나지 않는 「아직」**을 무한히 받는다 —
       2026-09-25 에 실제로 그 버그가 났다(「27번 물었습니다 · 아직」).
       ⛔ 이 분기를 지우지 말 것. */
    if (saved.dupOf != null) {
      await _useDuplicate(clip, saved);
      return;
    }

    /* 🔴 **첫 칸을 넘기는 것은 시간이 아니라 「실제로 올라간 것」이다.**
       웹도 같다 — 업로드가 끝나야 1번 칸이 켜진다. */
    state = AnalyzeRunning(clip: clip, step: 1, videoId: saved.id);
    _armStep();
    _armPoll(saved.id);
  }

  /// 중복이라 **빌려온 결과**를 그대로 보여 준다.
  ///
  /// 🔴 **저장은 새 클립 id 로 건다** — 계약이 「중복으로 처리된 클립도
  /// `kept: false` 로 시작한다」고 정했다(2150절). 원본 id 로 걸면 엉뚱한 줄을
  /// 저장하고 이 클립은 TTL 로 사라진다.
  Future<void> _useDuplicate(PickedClip clip, MyVideoLike saved) async {
    // 원본이 실패로 끝났으면 다시 돌려도 같은 결과다 — 그 사유를 그대로 준다.
    if (saved.dupStatus == 'failed') {
      state = AnalyzeFailed(
        clip: clip,
        reason: saved.dupReason ?? '전에 올린 같은 영상이 분석에 실패했습니다.',
      );
      return;
    }
    final ReportResult result;
    try {
      result = await ref.read(videoRepositoryProvider).report(saved.dupOf!);
    } catch (e) {
      state = AnalyzeError(clip: clip, message: '전에 낸 결과를 못 읽었습니다: $e');
      return;
    }
    switch (result) {
      case ReportReady(:final report):
        state = AnalyzeDone(
          clip: clip,
          videoId: saved.id,
          // 🔴 관절·리포트는 **원본**에 달려 있다 — 위 머리말.
          analysisVideoId: saved.dupOf!,
          report: report,
          borrowed: true,
        );
      case ReportFailed(:final reason):
        state = AnalyzeFailed(clip: clip, reason: reason);
      /* ⚠️ **원본이 아직 도는 중일 수 있다** — 「분석이 끝난 것」만 중복으로
         본다지만, 그 사이 상태가 바뀌었을 수 있다. 그때는 평소대로 기다린다. */
      case ReportNotReady():
      case ReportMissing():
      case ReportError():
        state = AnalyzeRunning(clip: clip, step: 1, videoId: saved.dupOf);
        _armStep();
        _armPoll(saved.dupOf!);
    }
  }

  /// 지금 칸의 추정 시간이 지나면 다음 칸으로 — **마지막 칸에서는 안 넘긴다.**
  void _armStep() {
    _stepTimer?.cancel();
    final s = state;
    if (s is! AnalyzeRunning) return;
    final wait = kAnalyzeSteps[s.step].estimate;
    if (wait == null) return;
    _stepTimer = Timer(wait, () {
      final now = state;
      if (now is! AnalyzeRunning) return;
      if (now.step >= kAnalyzeSteps.length - 1) return;
      state = AnalyzeRunning(
        clip: now.clip,
        step: now.step + 1,
        videoId: now.videoId,
      );
      _armStep();
    });
  }

  void _armPoll(String videoId) {
    _poll?.cancel();
    _poll = Timer.periodic(kPollEvery, (_) => _ask(videoId));
    // 첫 물음은 기다리지 않는다 — 아주 짧은 영상은 벌써 끝나 있을 수 있다.
    unawaited(_ask(videoId));
  }

  Future<void> _ask(String videoId) async {
    final ReportResult result;
    try {
      result = await ref.read(videoRepositoryProvider).report(videoId);
    } catch (e) {
      /* 🔴 **한 번 못 물은 것으로 끝내지 않는다** — 다음 차례에 다시 묻는다.

         ⚠️ **그런데 조용히 삼키면 안 된다** (2026-09-25). 전에는 여기서 그냥
         `return` 했는데, `report()` 가 **매번 던지는** 경우(401 · 파싱 실패)
         화면은 영영 「분석하고 있습니다」에 머물고 **아무도 왜인지 모른다** —
         「리포트가 아예 안 나온다」로 보인다. 사유를 화면에 흘려 둔다. */
      final s = state;
      if (s is AnalyzeRunning) {
        state = AnalyzeRunning(
          clip: s.clip,
          step: s.step,
          videoId: s.videoId,
          asked: s.asked + 1,
          lastAnswer: '못 물었습니다 — $e',
        );
      }
      return;
    }
    final s = state;
    if (s is! AnalyzeRunning) return;

    /// 지금 상태에 「몇 번 물었나 · 마지막 답」을 얹은 것.
    AnalyzeRunning noted(String answer) => AnalyzeRunning(
          clip: s.clip,
          step: s.step,
          videoId: s.videoId,
          asked: s.asked + 1,
          lastAnswer: answer,
        );

    switch (result) {
      /* 🔴 **아직**. 계속 묻는다 — 웹과 같은 규칙이다. `ReportError` 도
         여기 든다(고장은 일시적일 수 있다). */
      case ReportNotReady():
        state = noted('아직');
        return;
      case ReportError():
        state = noted('고장 — 다시 묻는 중');
        return;
      case ReportReady(:final report):
        _stopTimers();
        await _fillRemainingSteps(s);
        final now = state;
        state = AnalyzeDone(
          clip: now is AnalyzeRunning ? now.clip : s.clip,
          videoId: videoId,
          analysisVideoId: videoId,
          report: report,
        );
      case ReportFailed(:final reason):
        /* 🔴 **남은 칸을 채우지 않는다.** 종목 불일치는 측정에서 멈춘 것이라
           끝까지 채우면 거짓이 된다 — 곧바로 사유를 보여 준다. */
        _stopTimers();
        state = AnalyzeFailed(clip: s.clip, reason: reason);
      case ReportMissing():
        _stopTimers();
        state = AnalyzeFailed(clip: s.clip, reason: '그 영상을 찾을 수 없습니다.');
    }
  }

  /// 서버가 추정보다 먼저 끝났을 때 — 🔴 **칸을 건너뛰고 곧장 리포트를 띄우지
  /// 않는다.** 중간 칸이 켜진 채 리포트가 뜨면 「측정하다 말았다」로 읽힌다.
  Future<void> _fillRemainingSteps(AnalyzeRunning from) async {
    for (var i = from.step + 1; i < kAnalyzeSteps.length; i += 1) {
      final now = state;
      if (now is! AnalyzeRunning) return;
      state = AnalyzeRunning(clip: now.clip, step: i, videoId: now.videoId);
      await Future<void>.delayed(kFinishStep);
    }
  }
}

/// 업로드 응답에서 **화면이 쓰는 것**만 뽑은 것.
///
/// 🔴 **중복 세 칸을 빠뜨리지 말 것.** 이 셋은 **등록 응답 한 번에만 실린다**
/// (계약 2143절) — 놓치면 다시 볼 방법이 없다. 2026-09-25 에 실제로 빠뜨려서
/// 「리포트가 영영 안 나오는」 버그가 났다.
typedef MyVideoLike = ({
  String id,
  bool passed,
  String? reason,
  String? dupOf,
  String? dupStatus,
  String? dupReason,
});

final analyzeControllerProvider =
    NotifierProvider<AnalyzeController, AnalyzeState>(AnalyzeController.new);
