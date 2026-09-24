import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:video_player/video_player.dart';

import '../../../../core/design_scale.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../data/models/video_report.dart';
import '../../data/models/skeleton.dart';
import '../../data/pick_clip.dart';
import '../../data/video_providers.dart';
import '../widgets/skeleton_overlay.dart';
import '../analyze_controller.dart';
import '../analyze_steps.dart';
import '../widgets/report_view.dart';

/// **영상 분석** — 위는 영상, 아래는 글. 🔴 **두 칸이 끝까지 유지된다.**
///
/// 🔴 **단계마다 다른 화면으로 갈아 끼우지 않는다** (2026-09-24 사용자 정정:
/// 「따로따로가 아니라」). 처음엔 고르기·진행·리포트를 **서로 다른 화면**으로
/// 지었는데, 그러면 영상이 사라졌다 나타났다 한다. 지금은 **위 3분의 1이 늘
/// 영상 자리**이고(고르기 전에는 고르는 판, 고른 뒤에는 그 영상이 계속 돈다),
/// **아래 흰 판에 글이 이어진다**(제목 → 진행 → 리포트).
///
/// ⛔ **큰 「영상 분석」 제목을 화면 맨 위로 되돌리지 말 것** — 사용자가 그
/// 자리를 비우고 영상을 올리라고 정했다. 제목은 **흰 판 가운데**로 갔다.
///
/// ⚠️ **분석할 사람을 묶지 않는다.** 웹은 영상 위에 네모를 끌어 대상을 지정
/// 하지만 그것은 **브라우저에서 도는 ML**(MoveNet/tfjs)이라 앱으로 안 옮아
/// 온다. 앱은 서버에 맡긴다(계약상 `subject_box` 생략 = 자동).
/// 🔴 **`subject_box` 와 `subject_at_ms` 는 함께 보내거나 함께 생략한다** —
/// 한쪽만 오면 422 다. 지금은 **둘 다 생략**이다.
class AnalyzeScreen extends ConsumerWidget {
  const AnalyzeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(analyzeControllerProvider);
    return Scaffold(
      backgroundColor: _kBg,
      extendBody: true,
      bottomNavigationBar: FloatingNavBar(
        currentIndex: 1,
        onTap: (index) {
          if (index == 0) {
            context.go('/home');
          } else if (index == 3) {
            context.go('/profile');
          }
          /* 🔴 **1번은 이 화면 자신이다** — 아무것도 안 한다. `context.go` 를
             부르면 같은 화면을 다시 쌓아 **뒤로 가기가 한 번 더 필요해진다.** */
        },
      ),
      body: SafeArea(
        bottom: false,
        child: LayoutBuilder(
          // 🔴 **위 3분의 1은 늘 영상 자리다** (위 머리말).
          builder: (context, box) => Padding(
            /* 🔴 **흰 판이 하단 바 밑으로 안 들어간다** (2026-09-25 사용자 요청:
               「아래 흰판은 하단바랑 겹치지 않게 하단바 바로 위까지만」).
               `extendBody: true` 라 본문이 바 **뒤까지** 깔리는데, 흰 판은 그
               바가 떠 있는 자리라 겹치면 판이 바 밑으로 이어진 것처럼 보인다.
               ⚠️ 이만큼 밀면 아래에 검은 띠가 남는데, **그게 맞는 그림**이다. */
            padding: EdgeInsets.only(
              /* 🔴 **하단 바 윗변에서 딱 6 위다** (2026-09-25 사용자 지적:
                 「하단바랑 6픽셀 차이로 바로 위에」).

                 🔴 [FloatingNavBar.heightOf] 를 그대로 빼면 **너무 많이**
                 밀린다 — 그 값은 바가 **가리는 높이**(바 + 화면 아래 여백)라
                 바가 제 칸 안에서 [kBarTopGap] 만큼 내려 앉은 것까지 포함한다.
                 그 틈을 도로 더해야 **눈에 보이는 바의 윗변**이 기준이 된다. */
              bottom: context.d(kBottomBarHeight - kBarTopGap) + 6,
            ),
            child: Column(
              /* 🔴 **흰 판이 양옆을 꽉 채운다** (2026-09-25 사용자 지적:
                 「흰색판 양옆은 비우지 말고 꽉채워」).

                 🔴 [Column] 의 기본 `crossAxisAlignment` 는 **center** 라
                 자식에게 **느슨한** 가로 제약을 준다 — 그러면 [ColoredBox] 가
                 **제 내용 너비**로 줄어들어 양옆에 검은 여백이 생긴다.
                 `stretch` 가 그 자리를 꽉 채운다. ⛔ 지우지 말 것. */
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(
                  height: box.maxHeight / 3,
                  child: _Stage(state: state),
                ),
                Expanded(child: _Paper(state: state)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

const Color _kBg = Color(0xFF000000);
const Color _kOn = Color(0xFFFFFFFF);

/// 🔴 **글이 앉는 판**(2026-09-24 사용자 요청). 위 검은 칸과 맞물린다.
///
/// 🔴 **홈의 아래 판과 같은 면이다**([kSheetPaper], 2026-09-25 사용자 요청:
/// 「완전 흰색보다는 그 홈페이지에서 스쿼드판 있는 그 판의 살짝 어두운 흰색」).
/// 순백(`#F7F7F5`)이었는데 두 화면이 나란히 놓이면 **다른 판처럼** 보였다.
const Color _kPaper = kSheetPaper;
const Color _kOnPaper = Color(0xFF14161A);
const Color _kMuted = Color(0xFF6B7078);
const Color _kGood = Color(0xFF2E9E57);
const Color _kBad = Color(0xFFB42318);

/// 흰 판 **아래** 모서리 — 🔴 **살짝만**(사용자 요청). 위는 각지다.
const double _kPaperRadius = 16;

const double _kGutter = 20;

/// 위 칸 — 고르는 자리이거나, **계속 도는 영상**이다.
class _Stage extends ConsumerWidget {
  const _Stage({required this.state});

  final AnalyzeState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final clip = switch (state) {
      AnalyzePicked(:final clip) => clip,
      AnalyzeRunning(:final clip) => clip,
      AnalyzeRejected(:final clip) => clip,
      AnalyzeFailed(:final clip) => clip,
      AnalyzeDone(:final clip) => clip,
      AnalyzeError(:final clip) => clip,
      AnalyzeIdle() => null,
    };
    if (clip == null) return const _Picker();
    /* 🔴 **관절은 분석이 끝난 뒤에만 있다**(2026-09-25). 그 전에는 서버에 값이
       없다 — 분석 중에 물으면 `REPORT_NOT_READY` 만 온다. */
    /* 🔴 **저장용 id 가 아니라 「분석이 달린 id」다** — 중복이면 원본이다
       ([AnalyzeDone.analysisVideoId] 머리말). 섞으면 관절이 영영 안 뜬다. */
    final videoId =
        state is AnalyzeDone ? (state as AnalyzeDone).analysisVideoId : null;
    /* 🔴 **열쇠가 클립 경로다.** 단계가 바뀌어도(고름 → 분석 중 → 리포트)
       같은 위젯으로 남아 **재생이 안 끊긴다.** 열쇠가 없거나 자리가 바뀌면
       Flutter 가 갈아 끼워 영상이 처음부터 다시 열린다. */
    return _LocalPreview(
      key: ValueKey(clip.path),
      path: clip.path,
      videoId: videoId,
    );
  }
}

/// 비었을 때의 위 칸 — 🔴 **화면 위부터 3분의 1을 꽉 채운다**(사용자 요청).
class _Picker extends ConsumerWidget {
  const _Picker();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = ref.read(analyzeControllerProvider.notifier);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: _kGutter),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Symbols.upload, color: _kOn, size: 28, weight: 300),
          const SizedBox(height: 10),
          const Text(
            '영상을 고르세요',
            style: TextStyle(
              color: _kOn,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 5),
          /* ⚠️ **웹의 「영상을 여기에 놓으세요」를 그대로 쓰지 않는다** — 폰에는
             끌어다 놓을 것이 없다. 뒷줄(「한 번에 한 클립」)은 그대로 지킨다. */
          const Text(
            '한 번에 한 클립',
            style: TextStyle(color: Color(0x8CFFFFFF), fontSize: 12.5),
          ),
          const SizedBox(height: 18),
          /* 🔴 **카메라를 따로 잘 보이게 둔다**(2026-09-24 사용자 요청).
             웹에는 없는 자리다 — 폰에서만 되는 일이라 눈에 띄어야 한다. */
          Row(
            children: [
              Expanded(
                child: _Button(
                  buttonKey: const Key('analyze-pick-camera'),
                  icon: Symbols.photo_camera,
                  label: '바로 찍기',
                  filled: true,
                  onTap: () => c.pick(camera: true),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _Button(
                  buttonKey: const Key('analyze-pick-gallery'),
                  icon: Symbols.photo_library,
                  label: '앨범에서',
                  onTap: () => c.pick(camera: false),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// 아래 흰 판 — 🔴 **글이 여기서 이어진다.** 제목 → 진행 → 리포트.
class _Paper extends ConsumerWidget {
  const _Paper({required this.state});

  final AnalyzeState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = ref.read(analyzeControllerProvider.notifier);
    /* 🔴 **아래 모서리만 살짝 둥글다** (2026-09-25 사용자 요청). 위는 검은
       칸과 맞물리는 자리라 **각지게** 둔다 — 위까지 둥글리면 두 칸 사이에
       검은 초승달이 낀다.

       🔴 [ClipRRect] 다([DecoratedBox] 가 아니라) — 안에서 글이 구르므로,
       안 자르면 **둥근 모서리 위로 글자가 삐져나간다.** */
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(
        bottom: Radius.circular(_kPaperRadius),
      ),
      child: ColoredBox(
        color: _kPaper,
        /* 🔴 **단계가 갈릴 때 부드럽게 넘어간다** (2026-09-25 사용자 요청:
           「자연스럽고 부드럽게」). 안 두면 진행 칸에서 리포트로 **툭** 바뀐다. */
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 280),
          child: switch (state) {
        AnalyzeIdle(:final notice) => _Lead(notice: notice),
        AnalyzePicked(:final clip) =>
          _Confirm(clip: clip, onReset: c.reset, onStart: c.start),
        AnalyzeRunning(:final step, :final asked, :final lastAnswer) =>
          _Steps(step: step, asked: asked, lastAnswer: lastAnswer),
        AnalyzeRejected(:final reason) =>
          _Stopped(title: '규격을 통과하지 못했습니다', body: reason),
        AnalyzeFailed(:final reason) =>
          _Stopped(title: '분석에 실패했습니다', body: reason, retry: false),
        AnalyzeError(:final message) =>
          _Stopped(title: '문제가 있었습니다', body: message),
        AnalyzeDone(:final report, :final keep, :final keepNotice, :final borrowed) =>
          _Report(
            // 🔴 열쇠가 바뀌어야 [AnimatedSwitcher] 가 갈아 끼운다.
            key: ValueKey('done-$keep'),
            report: report,
            keep: keep,
            notice: keepNotice,
            borrowed: borrowed,
          ),
          },
        ),
      ),
    );
  }
}

/// 🔴 **큰 제목이 여기로 왔다** (2026-09-24 사용자 요청: 「흰색 판 가운데에
/// 써놓고」). 문구는 웹 `AnalysisStage.tsx` 원문 그대로다 — 두 화면이 다른
/// 말을 하면 같은 제품으로 안 읽힌다.
class _Lead extends StatelessWidget {
  const _Lead({this.notice});

  final String? notice;

  @override
  Widget build(BuildContext context) => _Sheet(
    children: [
      if (notice != null) ...[
        Text(
          notice!,
          key: const Key('analyze-notice'),
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: _kBad,
            fontSize: 13,
            height: 1.45,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 18),
      ],
      const Text(
        '영상 분석',
        textAlign: TextAlign.center,
        style: TextStyle(
          color: _kOnPaper,
          fontSize: 32,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.5,
        ),
      ),
      const SizedBox(height: 12),
      /* 🔴 **두 줄을 한 [Text] 의 줄바꿈으로 두지 않는다** — 웹이 `<br />` 로
         끊어 둔 것과 같은 자리에서 끊긴다. */
      const Text(
        '경기 영상을 올리면 수준 · 역할 · 성향 세 축으로 정리해 드립니다.',
        textAlign: TextAlign.center,
        style: TextStyle(color: _kMuted, fontSize: 13.5, height: 1.55),
      ),
      const Text(
        '하나의 점수로 매기지 않습니다.',
        textAlign: TextAlign.center,
        style: TextStyle(color: _kMuted, fontSize: 13.5, height: 1.55),
      ),
      const SizedBox(height: 26),
      /* 🔴 **셋 다 「…면 좋습니다」로 맞춘다**(웹 주석). 「해 주세요」로 쓰면
         *안 지키면 못 올린다*로 읽히는데, 실제로는 그런 영상도 받는다. */
      for (final (tip, why) in _kTips) ...[
        _Tip(tip: tip, why: why),
        const SizedBox(height: 9),
      ],
    ],
  );
}

/// 🔴 웹 `AnalysisStage.tsx` 의 팁 셋 — 문구를 바꾸지 말 것.
const List<(String, String)> _kTips = [
  ('카메라는 고정하면 좋습니다', '따라 움직이면 놓치기 쉽습니다'),
  ('온몸이 화면 안에 들어오면 좋습니다', '자세는 발끝까지 봅니다'),
  ('혼자 나올수록 좋습니다', '여럿이면 비슷한 옷과 헷갈립니다'),
];

/// 고른 뒤 — 위에서 영상이 도는 동안 여기서 묻는다.
class _Confirm extends StatelessWidget {
  const _Confirm({
    required this.clip,
    required this.onReset,
    required this.onStart,
  });

  final PickedClip clip;
  final VoidCallback onReset;
  final VoidCallback onStart;

  /// 🔴 **무거운 클립인가.** 자세 측정은 **프레임마다** 사람과 관절을 찾으므로
  /// 시간이 **해상도 × 길이**로 곱해진다 — 1분짜리 4K 는 짧은 720p 의 열 배가
  /// 넘게 걸린다. 그런데 화면이 그걸 안 알려 주면 **「고장났나」로 읽힌다**
  /// (2026-09-25 사용자: 「너무 오래 걸리고 되는지도 모르겠는데」).
  ///
  /// ⚠️ **막지 않는다.** 서버가 규격으로 받아 주는 클립이고, 여기서 가로막으면
  /// 반려 사유를 서버가 남기는 규칙(SFR-001)과 엇갈린다. **알리기만** 한다.
  bool get _heavy =>
      clip.meta.width * clip.meta.height > 1920 * 1080 ||
      clip.meta.durationMs > 30000;

  @override
  Widget build(BuildContext context) => _Sheet(
    children: [
      const Text(
        '이 영상으로 분석할까요?',
        style: TextStyle(
          color: _kOnPaper,
          fontSize: 19,
          fontWeight: FontWeight.w800,
        ),
      ),
      const SizedBox(height: 8),
      /* 🔴 **대상을 안 묻는다는 것을 알려 준다** — 웹은 「분석할 사람을 끌어서
         네모로 묶어 주세요」를 거치는데 앱은 그 단계가 없다(위 머리말). 말이
         없으면 「왜 안 물어보지」가 된다. */
      const Text(
        '분석할 사람을 AI 가 판단하여 고른 뒤 분석합니다.',
        textAlign: TextAlign.center,
        style: TextStyle(color: _kMuted, fontSize: 13, height: 1.5),
      ),
      const SizedBox(height: 14),
      /* 🔴 **고른 것의 크기를 드러낸다** — 위 [_heavy] 머리말. 못 재면(0) 그
         칸을 빼고 쓴다. `measureClip` 이 실패해도 던지지 않기 때문이다. */
      Text(
        key: const Key('analyze-clip-info'),
        [
          if (clip.meta.width > 0)
            '${clip.meta.width}×${clip.meta.height}',
          if (clip.meta.durationMs > 0)
            '${(clip.meta.durationMs / 1000).round()}초',
          '${(clip.file.sizeBytes / 1024 / 1024).toStringAsFixed(1)}MB',
        ].join(' · '),
        textAlign: TextAlign.center,
        style: const TextStyle(
          color: _kMuted,
          fontSize: 12,
          fontFeatures: [FontFeature.tabularFigures()],
        ),
      ),
      if (_heavy) ...[
        const SizedBox(height: 10),
        const Text(
          '큰 영상이라 몇 분 더 걸릴 수 있습니다.\n짧고 작은 클립일수록 빨리 끝납니다.',
          textAlign: TextAlign.center,
          style: TextStyle(color: _kBad, fontSize: 12, height: 1.45),
        ),
      ],
      const SizedBox(height: 22),
      Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _Button(
            buttonKey: const Key('analyze-again'),
            icon: Symbols.refresh,
            label: '다시 고르기',
            onPaper: true,
            onTap: onReset,
          ),
          const SizedBox(width: 10),
          _Button(
            buttonKey: const Key('analyze-start'),
            icon: Symbols.play_arrow,
            label: '분석 시작하기',
            filled: true,
            onPaper: true,
            onTap: onStart,
          ),
        ],
      ),
    ],
  );
}

class _Sheet extends StatelessWidget {
  const _Sheet({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
    padding: const EdgeInsets.fromLTRB(_kGutter, 26, _kGutter, 130),
    child: Column(children: children),
  );
}

class _Tip extends StatelessWidget {
  const _Tip({required this.tip, required this.why});

  final String tip;
  final String why;

  /// 🔴 **가운데로 모은다** (2026-09-25 사용자 요청). 왼쪽에 붙이면 위의
  /// 가운데 정렬된 제목·설명과 **축이 어긋나** 세 줄만 따로 노는 것처럼 보인다.
  /// ⚠️ 줄 **안**은 여전히 왼쪽 정렬이다 — 글자를 가운데 정렬하면 줄표(—)
  /// 앞뒤가 줄마다 다른 자리에 와서 읽기 나쁘다.
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    mainAxisAlignment: MainAxisAlignment.center,
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Padding(
        padding: EdgeInsets.only(top: 6, right: 8),
        child: _Dot(color: _kGood),
      ),
      Flexible(
        child: Text.rich(
          TextSpan(
            children: [
              TextSpan(
                text: tip,
                style: const TextStyle(
                  color: _kOnPaper,
                  fontWeight: FontWeight.w700,
                ),
              ),
              TextSpan(text: ' — $why', style: const TextStyle(color: _kMuted)),
            ],
          ),
          style: const TextStyle(fontSize: 12.5, height: 1.45),
        ),
      ),
    ],
  );
}

class _Dot extends StatelessWidget {
  const _Dot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    width: 4,
    height: 4,
    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
  );
}

class _Button extends StatelessWidget {
  const _Button({
    required this.buttonKey,
    required this.icon,
    required this.label,
    required this.onTap,
    this.filled = false,
    this.onPaper = false,
  });

  final Key buttonKey;
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool filled;

  /// 흰 판 위인가 — 🔴 **면과 글자가 통째로 뒤집힌다.**
  final bool onPaper;

  @override
  Widget build(BuildContext context) {
    final ink = onPaper ? _kOnPaper : _kOn;
    final over = onPaper ? _kPaper : _kBg;
    /* 🔴 **채운 단추의 면은 순백이 아니라 판과 같은 색이다** (2026-09-25 사용자
       요청: 「바로 찍기도 색상 똑같이」). 바로 아래 흰 판과 같은 면이라야 둘이
       한 재질로 읽힌다 — 순백이면 단추만 더 밝아 따로 논다.
       ⚠️ **테두리만 있는 단추(`filled: false`)는 그대로 순백 글자**다. 그쪽은
       면이 없어 검은 바탕 위에서 대비가 필요하다. */
    final face = onPaper ? ink : _kPaper;
    return GestureDetector(
      key: buttonKey,
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: 46,
        padding: const EdgeInsets.symmetric(horizontal: 18),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: filled ? face : Colors.transparent,
          border: Border.all(color: filled ? face : ink.withValues(alpha: 0.35)),
          borderRadius: BorderRadius.circular(23),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 18, color: filled ? over : ink),
            const SizedBox(width: 7),
            Text(
              label,
              style: TextStyle(
                color: filled ? over : ink,
                fontSize: 13.5,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 고른 클립을 **로컬 파일로** 계속 돌린다.
///
/// 🔴 **기존 `ClipPlayer` 를 못 쓴다** — 그쪽은 서버 주소 전용이고 높이가
/// 200 으로 박혀 있다.
/// 🔴 **다 쓰면 반드시 `dispose`** — 안드로이드는 동시 디코더가 몇 개 안 돼서
/// 쌓이면 **그다음부터 영상이 아예 안 열린다**(`pick_clip.dart` 가 같은 이유로
/// 재고 나서 곧바로 버린다).
class _LocalPreview extends ConsumerStatefulWidget {
  const _LocalPreview({super.key, required this.path, this.videoId});

  final String path;

  /// 🔴 **분석이 끝났을 때만 준다** — 그때만 서버에 관절이 있다.
  final String? videoId;

  @override
  ConsumerState<_LocalPreview> createState() => _LocalPreviewState();
}

class _LocalPreviewState extends ConsumerState<_LocalPreview> {
  VideoPlayerController? _c;

  @override
  void initState() {
    super.initState();
    _open();
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  Future<void> _open() async {
    final next = VideoPlayerController.file(File(widget.path));
    try {
      await next.initialize();
      await next.setLooping(true);
      // 🔴 분석하는 내내 도는 영상이라 **소리는 없다.**
      await next.setVolume(0);
      await next.play();
    } catch (_) {
      await next.dispose();
      return;
    }
    if (!mounted) {
      await next.dispose();
      return;
    }
    setState(() => _c = next);
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    if (c == null || !c.value.isInitialized) {
      /* 🔴 **작게**(2026-09-25 사용자 지적: 「도는 원 아직도 똑같이 큰데?」).
         진행 칸의 것만 줄였었는데 **영상 자리의 이것**이 기본 크기(~36)라
         그대로 컸다 — 스피너가 둘이라는 것을 놓쳤다. */
      return const Center(
        child: SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(
            strokeWidth: 1.8,
            color: Colors.white24,
          ),
        ),
      );
    }
    /* 🔴 **관절은 영상 그림과 같은 상자 안에 그린다.** 좌표가 0~1 이라
       레터박스를 포함한 칸에 그리면 **뼈대만 어긋나 떠 있다** — [AspectRatio]
       안에 함께 넣어야 정확히 겹친다. */
    final skel = widget.videoId == null
        ? null
        : ref.watch(skeletonProvider(widget.videoId!)).value;
    final ready = skel is SkeletonReady && skel.skeleton.known
        ? skel.skeleton
        : null;

    // 🔴 **자르지 않는다** — 고른 것이 그대로 보여야 무엇을 보내는지 안다.
    return Center(
      child: AspectRatio(
        aspectRatio: c.value.aspectRatio,
        child: Stack(
          fit: StackFit.expand,
          children: [
            VideoPlayer(c),
            /* 🔴 **재생 위치를 따라 다시 그린다.** 컨트롤러가 값을 바꿀 때마다
               울리는 [ValueListenableBuilder] 를 쓴다 — `setState` 를 타이머로
               돌리면 재생과 어긋난다. */
            if (ready != null)
              ValueListenableBuilder<VideoPlayerValue>(
                valueListenable: c,
                builder: (context, v, _) => SkeletonOverlay(
                  skeleton: ready,
                  position: v.position,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// 진행 체크리스트 — 🔴 **어느 칸이 켜지는지는 추정이다**([kAnalyzeSteps]).
///
/// 🔴 **가운데로 모았다** (2026-09-25 사용자 요청). 왼쪽 끝에 붙으면 오른쪽이
/// 통째로 비어 화면이 한쪽으로 쏠린다 — 덩이째 가운데에 두고 **줄 안만** 왼쪽
/// 정렬이다(칸 이름이 줄마다 다른 자리에서 시작하면 훑기 나쁘다).
class _Steps extends ConsumerWidget {
  const _Steps({required this.step, this.asked = 0, this.lastAnswer});

  final int step;

  /// 몇 번 물었나 · 서버가 마지막에 뭐라 했나 — [AnalyzeRunning] 머리말 참고.
  final int asked;
  final String? lastAnswer;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Stack(
    children: [
      ListView(
        padding: const EdgeInsets.fromLTRB(_kGutter, 26, _kGutter, 64),
        children: [
          const Text(
            '분석하고 있습니다',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: _kOnPaper,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            '1분 안팎 걸립니다.',
            textAlign: TextAlign.center,
            style: TextStyle(color: _kMuted, fontSize: 12.5),
          ),
          const SizedBox(height: 22),
          // 덩이째 가운데 — 줄 안은 왼쪽 정렬(위 머리말).
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final (i, s) in kAnalyzeSteps.indexed)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 15),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          /* 🔴 **동그라미를 줄였다**(14 → 11, 자리는 26 → 30)
                             — 사용자 지적: 「돌아가는 선은 살짝만 작게. 너무
                             커서 글자랑 겹치는 것 같다」. 자리를 함께 넓혀야
                             정말로 안 겹친다. */
                          width: 30,
                          child: i < step
                              ? const Icon(
                                  Icons.check,
                                  size: 16,
                                  color: _kGood,
                                )
                              : i == step
                              ? const Padding(
                                  padding: EdgeInsets.only(top: 2),
                                  child: SizedBox(
                                    // 🔴 14 → 11 → **8** (2026-09-25, 두 번째로
                                    //    더 줄이라는 요청). 획도 같이 얇게.
                                    width: 8,
                                    height: 8,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 1.3,
                                      color: _kOnPaper,
                                    ),
                                  ),
                                )
                              : const Padding(
                                  padding: EdgeInsets.only(top: 6),
                                  child: _Dot(color: Color(0xFFBFC4CB)),
                                ),
                        ),
                        Flexible(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                s.label,
                                style: TextStyle(
                                  color: i <= step
                                      ? _kOnPaper
                                      : const Color(0xFFA6ACB4),
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                s.note,
                                style: TextStyle(
                                  color: i <= step
                                      ? _kMuted
                                      : const Color(0xFFC2C7CE),
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          /* 🔴 **폴링이 도는지 드러낸다** (2026-09-25). 「리포트가 아예 안
             나온다」를 들었을 때 **몇 번 물었고 서버가 뭐라 했는지**가 화면에
             없으면 폴링이 도는지 멈췄는지조차 못 가른다. 작고 흐리게. */
          if (asked > 0) ...[
            const SizedBox(height: 6),
            Text(
              '$asked번 물었습니다 · ${lastAnswer ?? "…"}',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Color(0xFFA6ACB4), fontSize: 11),
            ),
          ],
        ],
      ),
      /* 🔴 **분석 취소는 오른쪽 아래 구석**(2026-09-25 사용자 요청). 흐름을
         막지 않게 구석에 두되, 분석 중에만 있다. */
      Positioned(
        right: 12,
        bottom: 10,
        child: GestureDetector(
          key: const Key('analyze-cancel'),
          onTap: ref.read(analyzeControllerProvider.notifier).cancel,
          behavior: HitTestBehavior.opaque,
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Text(
              '분석 취소',
              style: TextStyle(
                color: _kMuted,
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                decoration: TextDecoration.underline,
                decorationColor: _kMuted,
              ),
            ),
          ),
        ),
      ),
    ],
  );
}

/// 멈춘 자리 — 반려 · 실패 · 고장.
class _Stopped extends ConsumerWidget {
  const _Stopped({required this.title, required this.body, this.retry = true});

  final String title;
  final String body;

  /// 🔴 **분석 실패에는 주지 않는다** — 다시 눌러도 안 바뀐다.
  final bool retry;

  @override
  Widget build(BuildContext context, WidgetRef ref) => _Sheet(
    children: [
      Text(
        title,
        key: const Key('analyze-stopped'),
        textAlign: TextAlign.center,
        style: const TextStyle(
          color: _kOnPaper,
          fontSize: 19,
          fontWeight: FontWeight.w800,
        ),
      ),
      const SizedBox(height: 10),
      Text(
        body,
        textAlign: TextAlign.center,
        style: const TextStyle(color: _kMuted, fontSize: 13.5, height: 1.5),
      ),
      const SizedBox(height: 24),
      _Button(
        buttonKey: const Key('analyze-restart'),
        icon: Symbols.refresh,
        label: retry ? '다른 영상으로' : '처음으로',
        filled: true,
        onPaper: true,
        onTap: ref.read(analyzeControllerProvider.notifier).reset,
      ),
    ],
  );
}

/// 끝났다 — 리포트와 **저장 단추**.
/// 끝난 자리 — 🔴 **빌려온 결과면 그렇다고 먼저 말한다.**
class _Report extends ConsumerStatefulWidget {
  const _Report({
    super.key,
    required this.report,
    required this.keep,
    this.notice,
    this.borrowed = false,
  });

  final VideoReport report;
  final KeepState keep;
  final String? notice;

  /// 전에 낸 결과를 빌려온 것인가 — [AnalyzeDone.borrowed] 머리말 참고.
  final bool borrowed;

  @override
  ConsumerState<_Report> createState() => _ReportState();
}

class _ReportState extends ConsumerState<_Report> {
  /* 🔴 **빌려온 것이면 알림을 먼저 읽히고 본문을 뒤따라 띄운다**
     (2026-09-25 사용자 요청: 「'이미 리포트를 만든 영상입니다' 라고 나오면서
     그 후에 자연스럽고 부드럽게 이미 있는 리포트 보여주면」).
     새로 분석한 경우에는 기다릴 까닭이 없어 **처음부터 떠 있다.** */
  late bool _bodyIn = !widget.borrowed;
  Timer? _in;

  @override
  void initState() {
    super.initState();
    if (widget.borrowed) {
      _in = Timer(const Duration(milliseconds: 520), () {
        if (mounted) setState(() => _bodyIn = true);
      });
    }
  }

  @override
  void dispose() {
    _in?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final report = widget.report;
    final keep = widget.keep;
    final notice = widget.notice;
    final c = ref.read(analyzeControllerProvider.notifier);
    return ListView(
      /* 🔴 **리포트는 왼쪽 정렬이다** (2026-09-25 사용자 요청: 「분석 리포트
         나오는거는 가운데 말고 왼쪽으로」). 진행 칸은 가운데로 모았지만
         리포트는 **읽는 글**이라 왼쪽 끝이 가지런해야 훑을 수 있다.
         ⛔ 가운데 정렬로 되돌리지 말 것. */
      padding: const EdgeInsets.fromLTRB(_kGutter, 20, _kGutter, 24),
      children: [
        const Text(
          '리포트',
          textAlign: TextAlign.left,
          key: Key('analyze-report'),
          style: TextStyle(
            color: _kOnPaper,
            fontSize: 22,
            fontWeight: FontWeight.w800,
          ),
        ),
        if (widget.borrowed) ...[
          const SizedBox(height: 10),
          const Text(
            '이미 리포트를 만든 영상입니다.',
            key: Key('analyze-borrowed'),
            style: TextStyle(
              color: _kOnPaper,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          /* ⚠️ **왜 다시 안 도는지 말해 준다** — 계약이 그렇게 정한 까닭이
             「분석이 결정론적이라 같은 결과가 나온다」이기 때문이다. */
          const Text(
            '같은 영상은 다시 분석해도 같은 결과라, 전에 낸 것을 그대로 보여 드립니다.',
            style: TextStyle(color: _kMuted, fontSize: 12.5, height: 1.45),
          ),
        ],
        const SizedBox(height: 14),
        /* 🔴 **저장하지 않으면 사라진다.** 분석으로 올린 클립은 `kept: false` 로
           시작해서 **내 목록에도 안 뜨고**, 화면을 벗어나면 서버의 TTL 백스톱이
           지운다(계약 3-6절). 그래서 이 단추가 **리포트 아래가 아니라 위**에
           있다 — 끝까지 스크롤해야 보이면 못 보고 떠난다. */
        AnimatedOpacity(
          opacity: _bodyIn ? 1 : 0,
          duration: const Duration(milliseconds: 380),
          curve: Curves.easeOut,
          child: _KeepBar(keep: keep, notice: notice, onTap: c.keep),
        ),
        const SizedBox(height: 18),
        /* 🔴 **흰 판에 그대로 쓴다** (2026-09-24 사용자 결정: 「갈려져도
           괜찮지 않아? 그 흰색 판에 리포트가 쓰여야지」).

           ⚠️ 잠깐 **어두운 카드 한 장** 위에 올려 뒀었다 — [ReportView] 가
           어두운 바탕 전제(흰 글자)였기 때문이다. 사용자가 **갈림을 알고**
           흰 쪽을 골라서, 그 위젯에 `onPaper` 갈래를 냈다. 프로필의 리포트
           화면(`report_screen.dart`)은 **어두운 쪽 그대로**다. */
        AnimatedOpacity(
          opacity: _bodyIn ? 1 : 0,
          duration: const Duration(milliseconds: 380),
          curve: Curves.easeOut,
          child: ReportView(report: report, onPaper: true),
        ),
        const SizedBox(height: 16),
        Center(
          child: _Button(
            buttonKey: const Key('analyze-new'),
            icon: Symbols.refresh,
            label: '새 영상 분석',
            onPaper: true,
            onTap: c.reset,
          ),
        ),
      ],
    );
  }
}

/// 저장 줄 — 🔴 **이 화면에서 가장 중요한 단추다**(위 주석).
class _KeepBar extends StatelessWidget {
  const _KeepBar({required this.keep, required this.onTap, this.notice});

  final KeepState keep;
  final VoidCallback onTap;
  final String? notice;

  @override
  Widget build(BuildContext context) {
    if (keep == KeepState.saved) {
      return const Row(
        key: Key('analyze-kept'),
        children: [
          Icon(Icons.check_circle, color: _kGood, size: 18),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '내 프로필에 저장했습니다 — 영상과 리포트가 함께 남습니다.',
              style: TextStyle(color: _kGood, fontSize: 13, height: 1.4),
            ),
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: double.infinity,
          child: _Button(
            buttonKey: const Key('analyze-keep'),
            icon: Symbols.bookmark,
            label: keep == KeepState.saving ? '저장하는 중…' : '내 프로필에 저장',
            filled: true,
            onPaper: true,
            onTap: onTap,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          notice ?? '저장하지 않으면 이 영상과 리포트는 곧 지워집니다.',
          style: TextStyle(
            color: notice != null ? _kBad : _kMuted,
            fontSize: 12,
            height: 1.45,
          ),
        ),
      ],
    );
  }
}
