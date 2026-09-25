import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/video/data/clip_file.dart';
import 'package:super_sub/features/video/data/models/my_video.dart';
import 'package:super_sub/features/video/data/models/video_report.dart';
import 'package:super_sub/features/video/data/pick_clip.dart';
import 'package:super_sub/features/video/data/video_providers.dart';
import 'package:super_sub/features/video/data/video_repository_mock.dart';
import 'package:super_sub/features/video/presentation/analyze_controller.dart';
import 'package:super_sub/features/video/presentation/analyze_steps.dart';
import 'package:super_sub/features/video/presentation/screens/analyze_screen.dart';
import 'package:super_sub/features/video/presentation/widgets/report_view.dart';
import 'package:flutter/material.dart';

/* 「영상 분석」의 한 줄기 — 고르기 → 올리기 → 진행 → 리포트.

   🔴 **가장 중요한 것은 `analyze: true` 가 실제로 나가는지다.** 2026-09-24
   까지 앱은 `analyze` 를 아무도 안 넘겨서 **올린 것이 전부 「업로드 영상」**
   이었다(분석 작업이 아예 안 만들어졌다). 그 회귀는 화면만 봐서는 안 보인다 —
   업로드는 성공하고 리포트만 영영 안 나온다.

   시계: 폴링(4초)과 칸 넘김(최대 33초)이 있어 `testWidgets` 의 가짜 시계로
   돌린다. 🔴 `pumpAndSettle` 은 쓰지 않는다 — 진행 칸에 무한 애니메이션
   (동그라미)이 있어 10분 타임아웃까지 간다. */

/// 올린 것을 **받아 적는** 저장소.
class _Spy extends MockVideoRepository {
  _Spy(super.db, {required super.userId});

  /// 🔴 마지막 업로드에 실린 `analyze` — `null` 이면 아직 안 불렸다.
  bool? sawAnalyze;
  String? sawSport;

  bool passed = true;
  String? rejectReason;

  /// 서버가 「같은 영상」으로 보고 결과를 빌려줄 때 싣는 셋.
  String? dupOf;
  String? dupStatus;
  String? dupReason;

  /// 차례로 돌려줄 리포트 답. 다 쓰면 마지막 것을 되풀이한다.
  List<ReportResult> answers = const [ReportNotReady()];
  int asked = 0;

  @override
  Future<MyVideo> uploadClip({
    required ClipFile file,
    required ClipMeta meta,
    required String sportCode,
    bool analyze = false,
  }) async {
    sawAnalyze = analyze;
    sawSport = sportCode;
    return MyVideo(
      id: 'v-new',
      sportCode: sportCode,
      storageKey: 'videos/x.mp4',
      durationMs: meta.durationMs,
      createdAt: DateTime(2026, 9, 24),
      passed: passed,
      rejectReason: rejectReason,
      duplicateOfVideoId: dupOf,
      duplicateStatus: dupStatus,
      duplicateFailureReason: dupReason,
    );
  }

  /// keep 을 부른 영상 id 들.
  final List<String> kept = [];

  /// 저장이 막히는 경우 — 사유를 여기에 두면 던진다.
  String? keepThrows;

  @override
  Future<MyVideo> keepVideo(String videoId) async {
    if (keepThrows != null) throw Exception(keepThrows);
    kept.add(videoId);
    return MyVideo(
      id: videoId,
      sportCode: kAnalyzeSportCode,
      storageKey: 'reports/$videoId/source.mp4',
      durationMs: 12000,
      createdAt: DateTime(2026, 9, 24),
      passed: true,
    );
  }

  /// 리포트를 물을 때마다 던지게 하려면 사유를 여기에 둔다.
  String? reportThrows;

  @override
  Future<ReportResult> report(String videoId) async {
    asked += 1;
    if (reportThrows != null) throw Exception(reportThrows);
    final i = asked - 1 < answers.length ? asked - 1 : answers.length - 1;
    return answers[i];
  }
}

/// 진짜 앨범을 못 여니 고른 척한다.
class _FakePicker implements ClipPicker {
  _FakePicker(this.clip);

  final PickedClip? clip;
  bool? cameraAsked;

  @override
  Future<PickedClip?> fromCamera() async {
    cameraAsked = true;
    return clip;
  }

  @override
  Future<PickedClip?> fromGallery() async {
    cameraAsked = false;
    return clip;
  }
}

PickedClip _clip({String name = 'kick.mp4', int bytes = 1000}) => PickedClip(
  path: '/tmp/$name',
  meta: const ClipMeta(durationMs: 12000, width: 1920, height: 1080),
  file: ClipFile(
    name: name,
    contentType: contentTypeOf(name),
    sizeBytes: bytes,
    openRead: Stream<List<int>>.empty,
  ),
);

({ProviderContainer container, _Spy spy, AnalyzeController c}) _setUp(
  WidgetTester tester, {
  PickedClip? picked,
}) {
  final db = MockDb();
  final spy = _Spy(db, userId: MockDb.playerId);
  final container = ProviderContainer(
    overrides: [videoRepositoryProvider.overrideWithValue(spy)],
  );
  addTearDown(container.dispose);
  final c = container.read(analyzeControllerProvider.notifier);
  c.usePicker(_FakePicker(picked ?? _clip()));
  return (container: container, spy: spy, c: c);
}

/// 리포트가 나온 자리까지 데려간다 — 저장 시험 셋이 나눠 쓴다.
Future<({ProviderContainer container, _Spy spy, AnalyzeController c})>
    _reachDone(WidgetTester tester) async {
  final s = _setUp(tester);
  s.spy.answers = [
    ReportReady(
      VideoReport(
        summary: '좋은 슛입니다.',
        points: const [],
        scenes: const [],
        radar: const [],
        savedAt: '2026-09-24',
      ),
    ),
  ];
  await s.c.pick(camera: false);
  await s.c.start();
  // 남은 칸을 채우는 시간을 흘린다.
  await tester.pump(kFinishStep * (kAnalyzeSteps.length + 1));
  expect(s.container.read(analyzeControllerProvider), isA<AnalyzeDone>());
  return s;
}

void main() {
  /* 🔴 **화면이 흰 판용 리포트를 실제로 고르는가.**
     `report_view_test.dart` 는 위젯을 **직접** 띄우므로 이 배선을 못 잡는다 —
     화면에서 `onPaper: true` 를 지워도 그쪽은 그대로 통과한다(확인했다).
     리포트가 흰 판에 흰 글자로 그려지면 **아무 데서도 안 터지고 그냥 안
     보인다.** 그래서 여기서 배선을 못 박는다. */
  testWidgets('분석 화면은 리포트를 흰 판용으로 그린다', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    final s = await _reachDone(tester);
    await tester.pumpWidget(UncontrolledProviderScope(
      container: s.container,
      child: const MaterialApp(home: AnalyzeScreen()),
    ));
    await tester.pump();

    final view = tester.widget<ReportView>(find.byType(ReportView));
    expect(view.onPaper, isTrue, reason: '흰 판 위라 글자가 어두워야 한다');

    /* 🔴 **비교가 뒤에서 미리 받는다**(2026-09-25) — 리포트가 뜨는 순간
       선수 목록·관절을 당겨 둔다. 목 저장소는 일부러 느려서(300ms) 그 타이머가
       남고, 안 흘려 보내면 「위젯 트리를 버렸는데 타이머가 남았다」로 깨진다.
       ⚠️ **미리 받기를 껐다고 보지 말 것** — 흘려 보내는 것뿐이다. */
    await tester.pump(const Duration(seconds: 2));
  });

  testWidgets('고르면 미리보기 상태가 된다', (tester) async {
    final s = _setUp(tester);
    expect(s.container.read(analyzeControllerProvider), isA<AnalyzeIdle>());

    await s.c.pick(camera: false);
    expect(s.container.read(analyzeControllerProvider), isA<AnalyzePicked>());
  });

  testWidgets('고르다 말면 아무 일도 안 일어난다', (tester) async {
    final s = _setUp(tester);
    s.c.usePicker(_FakePicker(null));

    await s.c.pick(camera: false);
    /* 🔴 **오류가 아니다.** 되돌아온 자리가 「문제가 있었습니다」면 취소할
       때마다 빨간 판이 뜬다. */
    expect(s.container.read(analyzeControllerProvider), isA<AnalyzeIdle>());
    expect(
      (s.container.read(analyzeControllerProvider) as AnalyzeIdle).notice,
      isNull,
    );
  });

  testWidgets('받지 않는 형식은 올리기 전에 막고 사유를 남긴다', (tester) async {
    final s = _setUp(tester, picked: _clip(name: 'kick.avi'));

    await s.c.pick(camera: false);
    final state = s.container.read(analyzeControllerProvider);
    expect(state, isA<AnalyzeIdle>());
    expect((state as AnalyzeIdle).notice, contains('형식'));
    /* 🔴 **형식·용량만 여기서 막는다** — 그 둘은 `upload-url` 이 422 로 튕겨
       아무 데도 안 남는다. 길이·해상도는 서버가 반려 사유로 남겨야 한다. */
    expect(s.spy.sawAnalyze, isNull, reason: '올리지 않았어야 한다');
  });

  /* 🔴 **이 저장소에서 가장 값진 단언이다.** 앱은 2026-09-24 까지 `analyze` 를
     한 번도 안 실어서 올린 것이 전부 「업로드 영상」이었다 — 분석 작업 자체가
     안 만들어졌고, 화면은 그냥 리포트를 영영 못 받았다. */
  testWidgets('분석을 걸면 analyze: true 가 실제로 나간다', (tester) async {
    final s = _setUp(tester);
    await s.c.pick(camera: false);
    await s.c.start();

    expect(s.spy.sawAnalyze, isTrue, reason: 'analyze 가 실려야 한다');
    expect(s.spy.sawSport, kAnalyzeSportCode);

    /* 🔴 **시계를 멈추고 끝낸다.** 분석이 도는 채로 시험이 끝나면
       「타이머가 남았다」로 깨지는데 **화면 잘못이 아니다** — 실제로는 화면을
       떠날 때 `ref.onDispose` 가 같은 일을 한다. */
    s.c.reset();
  });

  testWidgets('카메라와 앨범이 서로 다른 길로 간다', (tester) async {
    final s = _setUp(tester);
    final picker = _FakePicker(_clip());
    s.c.usePicker(picker);

    await s.c.pick(camera: true);
    expect(picker.cameraAsked, isTrue);
    await s.c.pick(camera: false);
    expect(picker.cameraAsked, isFalse);
  });

  /* 🔴 **규격 반려는 예외가 아니다**(계약은 `201`). 서버가 실은 사유가
     화면까지 와야 한다 — 기본 문구로 덮으면 왜 막혔는지 알 수가 없다. */
  testWidgets('반려되면 서버가 준 사유를 그대로 들고 멈춘다', (tester) async {
    final s = _setUp(tester);
    s.spy.passed = false;
    s.spy.rejectReason = '영상이 너무 짧습니다 (최소 3초).';

    await s.c.pick(camera: false);
    await s.c.start();

    final state = s.container.read(analyzeControllerProvider);
    expect(state, isA<AnalyzeRejected>());
    expect((state as AnalyzeRejected).reason, '영상이 너무 짧습니다 (최소 3초).');
  });

  testWidgets('아직이면 계속 묻고, 끝나면 리포트로 간다', (tester) async {
    final s = _setUp(tester);
    s.spy.answers = [
      const ReportNotReady(),
      const ReportNotReady(),
      ReportReady(
        VideoReport(
          summary: '좋은 슛입니다.',
          points: const [],
          scenes: const [],
          radar: const [],
          savedAt: '2026-09-24',
        ),
      ),
    ];

    await s.c.pick(camera: false);
    await s.c.start();
    // 올리자마자 한 번 묻는다 — 아주 짧은 영상은 벌써 끝나 있을 수 있다.
    expect(s.spy.asked, greaterThan(0));
    expect(s.container.read(analyzeControllerProvider), isA<AnalyzeRunning>());

    // 4초짜리 폴링을 두 번 흘린다.
    await tester.pump(kPollEvery);
    await tester.pump(kPollEvery);
    // 남은 칸을 250ms 씩 채우고 끝난다.
    await tester.pump(kFinishStep * (kAnalyzeSteps.length + 1));

    expect(s.container.read(analyzeControllerProvider), isA<AnalyzeDone>());
  });

  /* 🔴 **분석 실패는 남은 칸을 채우지 않는다.** 종목 불일치는 측정에서 멈춘
     것이라 끝까지 채우면 거짓이 된다 — 곧바로 사유를 보여 준다. */
  testWidgets('분석 실패는 사유를 그대로 들고 즉시 멈춘다', (tester) async {
    final s = _setUp(tester);
    s.spy.answers = const [ReportFailed('축구 영상으로 보이지 않습니다.')];

    await s.c.pick(camera: false);
    await s.c.start();
    await tester.pump(kPollEvery);

    final state = s.container.read(analyzeControllerProvider);
    expect(state, isA<AnalyzeFailed>());
    expect((state as AnalyzeFailed).reason, '축구 영상으로 보이지 않습니다.');
  });

  /* 🔴 **같은 영상을 다시 올리면 서버가 작업을 안 만든다**(계약 2129절) — 대신
     **이미 끝난 원본의 결과**를 등록 응답에 실어 준다. 그 셋은 **그 한 번만**
     온다.

     🔴 **이걸 안 받으면 영영 안 끝난다.** 2026-09-25 에 실제로 그 버그가 났다 —
     클립 자신은 작업이 없어서 폴링이 **끝나지 않는 「아직」**을 무한히 받았다
     (화면에 「27번 물었습니다 · 아직」). 사용자가 「똑같은 영상은 리포트 작성
     안되게 되어있나」로 짚어 줘서 찾았다. ⛔ 이 시험을 지우지 말 것. */
  testWidgets('같은 영상이면 빌려온 리포트를 그 자리에서 보여 준다', (tester) async {
    final s = _setUp(tester);
    s.spy.dupOf = 'v-earlier';
    s.spy.dupStatus = 'succeeded';
    s.spy.answers = [
      ReportReady(
        VideoReport(
          summary: '전에 낸 그 결과입니다.',
          points: const [],
          scenes: const [],
          radar: const [],
          savedAt: '2026-09-24',
        ),
      ),
    ];

    await s.c.pick(camera: false);
    await s.c.start();

    final st = s.container.read(analyzeControllerProvider);
    expect(st, isA<AnalyzeDone>(), reason: '기다리지 않고 바로 끝난다');
    expect((st as AnalyzeDone).report.summary, '전에 낸 그 결과입니다.');
    /* 🔴 **저장은 새 클립 id 로 건다**(계약 2150절: 중복 클립도 `kept:false` 로
       시작한다). 원본 id 로 걸면 엉뚱한 줄을 저장하고 이 클립은 TTL 로 사라진다. */
    expect(st.videoId, 'v-new');
    /* 🔴 **빌려온 것이라고 표시가 남아야 한다** — 화면이 「이미 리포트를 만든
       영상입니다」를 먼저 읽히고 본문을 뒤따라 띄운다(2026-09-25 사용자 요청).
       이 값이 없으면 **방금 분석한 줄 안다.** */
    expect(st.borrowed, isTrue);
    /* 🔴 **저장용 id 와 「분석이 달린 id」는 다르다.** 리포트·관절은 **원본**에
       달려 있고 저장은 **새 클립**에 건다 — 2026-09-25 에 이걸 섞어서 관절이
       영영 안 떴다(오류 없이 그냥 안 그려진다). */
    expect(st.analysisVideoId, 'v-earlier');
  });

  testWidgets('전에 올린 같은 영상이 실패했으면 그 사유를 그대로 준다', (tester) async {
    final s = _setUp(tester);
    s.spy.dupOf = 'v-earlier';
    s.spy.dupStatus = 'failed';
    s.spy.dupReason = '사람이 화면에서 너무 작습니다.';

    await s.c.pick(camera: false);
    await s.c.start();

    final st = s.container.read(analyzeControllerProvider);
    expect(st, isA<AnalyzeFailed>());
    expect((st as AnalyzeFailed).reason, '사람이 화면에서 너무 작습니다.');
    // 🔴 실패한 원본에는 리포트를 물으러 가지 않는다 — 물을 것이 없다.
    expect(s.spy.asked, 0);
  });

  /* 🔴 **분석 중에 그만둘 수 있다** (2026-09-25 사용자 요청). 고른 영상은
     그대로 두고 「시작 전」으로 돌아간다 — 다시 걸 수 있어야 한다.
     ⚠️ **서버 작업까지 멈추지는 못한다**(계약에 취소 경로가 없다). 저장을
     안 했으니 올라간 클립은 서버의 TTL 백스톱이 지운다. */
  testWidgets('분석을 취소하면 고른 영상은 남고 시계가 멈춘다', (tester) async {
    final s = _setUp(tester);
    await s.c.pick(camera: false);
    await s.c.start();
    expect(s.container.read(analyzeControllerProvider), isA<AnalyzeRunning>());
    final askedBefore = s.spy.asked;

    s.c.cancel();

    expect(s.container.read(analyzeControllerProvider), isA<AnalyzePicked>());
    // 시계가 멎었으니 더 묻지 않는다.
    await tester.pump(kPollEvery * 3);
    expect(s.spy.asked, askedBefore, reason: '취소 뒤에는 안 묻는다');
  });

  /* 🔴 **못 물었으면 그 사유가 화면까지 온다** (2026-09-25). 전에는 조용히
     삼켜서, `report()` 가 매번 던지면 화면이 영영 「분석하고 있습니다」에
     머물고 **아무도 왜인지 몰랐다** — 「리포트가 아예 안 나온다」가 그 모습이다. */
  testWidgets('묻다가 터지면 사유가 상태에 남는다', (tester) async {
    final s = _setUp(tester);
    s.spy.reportThrows = '401 토큰이 만료됐습니다';

    await s.c.pick(camera: false);
    await s.c.start();
    /* ⚠️ **한 박자 흘려야 한다.** 첫 물음은 `unawaited` 로 나가므로
       `start()` 가 돌아온 시점엔 아직 답이 안 왔다 — 안 흘리면 `asked` 가 0 이다. */
    await tester.pump();

    final st = s.container.read(analyzeControllerProvider) as AnalyzeRunning;
    expect(st.asked, greaterThan(0));
    expect(st.lastAnswer, contains('401'));
    s.c.reset();
  });

  /* 🔴 **저장하지 않으면 분석 결과가 사라진다.** `analyze: true` 로 등록한
     클립은 `kept: false` 로 시작해서 본인 목록에도 안 뜨고, 화면을 벗어나면
     서버의 TTL 백스톱이 지운다(계약 3-6절). **저장 단추가 유일한 출구다.** */
  testWidgets('저장하면 그 영상 id 로 keep 을 부른다', (tester) async {
    final s = await _reachDone(tester);
    expect(s.spy.kept, isEmpty, reason: '저절로 저장되지는 않는다');

    await s.c.keep();

    expect(s.spy.kept, ['v-new']);
    final state = s.container.read(analyzeControllerProvider) as AnalyzeDone;
    expect(state.keep, KeepState.saved);
  });

  testWidgets('이미 저장했으면 다시 안 부른다', (tester) async {
    final s = await _reachDone(tester);
    await s.c.keep();
    await s.c.keep();
    // 계약상 멱등이지만 왕복이 아깝다 — 화면이 두 번 눌려도 한 번만 나간다.
    expect(s.spy.kept, ['v-new']);
  });

  /* 🔴 **막힌 사유를 그대로 보여 준다** — 「갈래마다 3개」 상한이 여기서 막는
     대표적인 자리다. 기본 문구로 덮으면 왜 저장이 안 되는지 알 수가 없다. */
  testWidgets('저장이 막히면 사유가 남는다', (tester) async {
    final s = await _reachDone(tester);
    s.spy.keepThrows = '분석 영상이 이미 3개입니다.';

    await s.c.keep();

    final state = s.container.read(analyzeControllerProvider) as AnalyzeDone;
    expect(state.keep, KeepState.failed);
    expect(state.keepNotice, contains('3개'));
  });

  /* 🔴 **한 번 못 물은 것으로 끝내지 않는다** — 네트워크가 잠깐 끊긴 것과
     「분석이 실패했다」는 다르다. */
  testWidgets('묻다가 터져도 계속 묻는다', (tester) async {
    final s = _setUp(tester);
    s.spy.answers = const [ReportError('네트워크'), ReportNotReady()];

    await s.c.pick(camera: false);
    await s.c.start();
    await tester.pump(kPollEvery);

    expect(s.container.read(analyzeControllerProvider), isA<AnalyzeRunning>());
    expect(s.spy.asked, greaterThan(1));
    s.c.reset(); // 위와 같은 까닭 — 도는 시계를 두고 끝내지 않는다.
  });
}
