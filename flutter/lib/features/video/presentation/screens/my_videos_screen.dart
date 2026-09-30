import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../../core/theme/app_theme.dart';
import '../../data/clip_file.dart';
import '../../data/models/my_video.dart';
import '../../data/pick_clip.dart';
import '../my_videos_controller.dart';
import '../widgets/clip_player.dart';
import '../widgets/publish_form.dart';
import '../widgets/report_panel.dart';
import '../widgets/video_strip.dart';

/// 내 영상 — 웹 `/me` 오른쪽 칸(`MyVideos.tsx`)을 폰 세로에 맞춰 옮긴 것이다.
///
/// 웹은 좌우 두 단이라 이것이 옆 칸인데, **폰에는 옆으로 펼 자리가 없어**
/// 프로필에서 밀고 들어오는 전용 화면으로 뒀다(이식 지침 §2-2).
///
/// 🔴 **「영상 분석」 화면과 같은 골격이다** (2026-09-25 사용자: 「UI 가 혼자
/// 따로 놀거든? … 영상 분석 시작하기 누르면 나오는 그런 스타일로 만들어줘」).
/// 위 3분의 1은 **검은 영상 자리**, 아래는 **밝은 판**(`analyze_screen.dart`
/// 의 `_Stage`/`_Paper` 와 같은 배치). 전에는 어두운 초록 바탕에 네모 카드와
/// 꽉 찬 테두리 단추가 섞여 있어서, 같은 앱의 두 화면이 서로 다른 제품처럼
/// 보였다.
/// ⛔ 어두운 초록(`#14201A`) 바탕으로 되돌리지 말 것.
class MyVideosScreen extends ConsumerStatefulWidget {
  const MyVideosScreen({super.key});

  @override
  ConsumerState<MyVideosScreen> createState() => _MyVideosScreenState();
}

class _MyVideosScreenState extends ConsumerState<MyVideosScreen>
    with SingleTickerProviderStateMixin {
  /// 지금 보고 있는 갈래.
  bool _analyzedTab = true;

  /// 갈래 안에서 몇 번째를 보고 있나.
  int _at = 0;

  /// 거른 사유 · 반려 사유 · 실패 사유가 다 여기로 나온다.
  String? _notice;

  /// 지울지 한 번 더 묻는 중인 영상 id. **되돌릴 수 없어서 곧바로 안 지운다.**
  String? _confirming;

  bool _busy = false;

  /// 공개 폼이 열린 영상 id.
  String? _publishing;

  /// 리포트를 펴 둘 것인가 — 🔴 **처음부터 참이다** (2026-09-25 사용자:
  /// 「리포트는 분석 영상에서는 기본값은 보여주는 거로 하자. 들어가면 바로
  /// 리포트 보이게 하고, 사용자가 닫게 하자」).
  ///
  /// 분석 영상을 보러 온 사람이 보려는 것이 **리포트**다 — 한 번 더 누르게
  /// 하면 그 화면의 목적이 한 단 뒤로 밀린다. ⛔ 기본값을 `false` 로 되돌리지
  /// 말 것.
  ///
  /// ⚠️ 영상을 넘겨도 **이 값은 그대로다** — 편 채로 넘기면 넘긴 자리에서
  /// 그 영상의 리포트가 이어서 펴진다(앞 영상 것이 붙어 있지 않다).
  bool _reportWanted = true;

  late final AnimationController _reportOpen;
  late final CurvedAnimation _reportCurve;

  /* 🔴 **`late final … = AnimationController(vsync: this)` 로 두지 말 것.**
     한 번도 안 열린 채 화면을 떠나면 `dispose()` 안에서 **그제서야** 만들어
     지는데, 그때 티커가 `TickerMode` 를 찾다가 「Looking up a deactivated
     widget's ancestor is unsafe」로 터진다(시험 열넷이 한꺼번에 깨졌다). */
  @override
  void initState() {
    super.initState();
    _reportOpen = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
      // 🔴 **펴진 채로 시작한다** — 들어가자마자 접히는 연출을 보일 까닭이 없다.
      value: 1,
    );
    _reportCurve = CurvedAnimation(
      parent: _reportOpen,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
  }

  @override
  void dispose() {
    _reportCurve.dispose();
    _reportOpen.dispose();
    super.dispose();
  }

  /// 리포트를 편다/접는다 — 🔴 **화면을 밀지 않는다**([ReportPanel] 머리말).
  void _toggleReport() {
    setState(() => _reportWanted = !_reportWanted);
    if (_reportWanted) {
      _reportOpen.forward();
    } else {
      /* 🔴 **다 접힌 뒤에 떼려고 다시 그린다.** 누르는 순간 떼면 내용이
         사라진 **빈 칸만** 접혀서, 리포트가 툭 사라진 것처럼 보인다. */
      _reportOpen.reverse().whenComplete(() {
        if (mounted) setState(() {});
      });
    }
  }

  /// 판이 **트리에 붙어 있는가** — 접히는 동안에도 참이다(위 주석).
  bool get _reportMounted => _reportWanted || _reportOpen.value > 0;

  @override
  Widget build(BuildContext context) {
    final asyncVideos = ref.watch(myVideosProvider);
    final all = asyncVideos.value ?? const <MyVideo>[];
    final split = splitVideos(all);
    final shown = _analyzedTab ? split.analyzed : split.uploaded;
    /* 🔴 **자리를 상태로 들고 있으므로 목록이 짧아지면 넘칠 수 있다.** 그릴
       때 여기서 한 번 잡는다 — 탭을 누를 때만 0 으로 되돌리면 목록 자체가
       줄어드는 경우(지운 뒤)를 놓친다. */
    final i = shown.isEmpty ? 0 : _at.clamp(0, shown.length - 1);
    final v = shown.isEmpty ? null : shown[i];

    return Scaffold(
      backgroundColor: _kBg,
      body: SafeArea(
        bottom: false,
        child: LayoutBuilder(
          // 🔴 **위 3분의 1은 늘 영상 자리다**(`analyze_screen.dart` 와 같다).
          builder: (context, box) => Column(
            /* 🔴 [Column] 의 기본 `crossAxisAlignment` 는 center 라 밝은 판이
               **제 내용 너비**로 줄어든다 — `stretch` 가 그 자리를 꽉 채운다.
               ⛔ 지우지 말 것(같은 것에 분석 화면이 먼저 걸렸다). */
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              /* 🔴 **맨 윗줄은 뒤로가기 하나다** (2026-09-25 정정, 사용자:
                 「맨 윗줄 뒤로 가기 있는 곳만 영상이랑 안겹치게 그 뒤로가기
                 크기 만큼만 위에 남겨두고, 분석영상 업로드 영상 업로드 하기
                 버튼 영상 아래에 두자」).

                 ⛔ 갈래 셋을 이 줄로 되돌리지 말 것 — 한 줄에 같이 세웠더니
                 알약이 좁아져 「업로드 하기」가 잘렸고, 화살표와 섞여 무엇이
                 갈래인지 안 읽혔다. */
              Align(
                alignment: Alignment.centerLeft,
                child: IconButton(
                  key: const Key('videos-back'),
                  icon: const Icon(Symbols.arrow_back, color: _kOn, size: 22),
                  tooltip: '뒤로',
                  onPressed: () => Navigator.of(context).maybePop(),
                ),
              ),
              SizedBox(
                height: box.maxHeight / 3,
                child: _Stage(video: v, loading: asyncVideos.isLoading),
              ),
              Expanded(
                /* 🔴 **아래 모서리만 살짝 둥글다** — 위는 검은 칸과 맞물리는
                   자리라 각지게 둔다. [ClipRRect] 인 까닭은 안에서 글이 구르기
                   때문이다(안 자르면 둥근 모서리 위로 글자가 삐져나간다). */
                child: ClipRRect(
                  borderRadius: const BorderRadius.vertical(
                    bottom: Radius.circular(16),
                  ),
                  child: ColoredBox(
                    color: _kPaper,
                    child: asyncVideos.hasError
                        ? _Centered(text: '${asyncVideos.error}')
                        : _paper(shown, i, v),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 🔴 **줄 차례를 사용자가 정했다** (2026-09-25): 영상 → **분석 완료들**
  /// (스트립) → 다음 영상 고르기 → 삭제·대표 → 리포트.
  ///
  /// ⛔ 순서를 바꾸지 말 것. 전에는 넘기는 줄이 스트립 위에 있었는데, 고를
  /// 것들이 **아래**에 있으면서 `1 / N` 만 위에 있으면 무엇을 세는 숫자인지
  /// 안 읽힌다.
  Widget _paper(List<MyVideo> shown, int i, MyVideo? v) => ListView(
        padding: const EdgeInsets.fromLTRB(_kGutter, 14, _kGutter, 28),
        children: [
          /* 🔴 **한 줄에 셋이다** (2026-09-25 사용자 요청: 「업로드 버튼도 한
             줄에 둬. 총 3개」). 자리는 **영상 아래 판 맨 위**다(위 주석). */
          _Tabs(
            analyzed: _analyzedTab,
            busy: _busy,
            onPick: (next) => setState(() {
              _analyzedTab = next;
              _at = 0;
              _confirming = null;
              _publishing = null;
            }),
            onUpload: _pick,
          ),
          const SizedBox(height: 12),

          // 올리는 중에 무슨 일이 있었는지 — 거른 사유 · 반려 사유 · 실패 사유.
          if (_notice != null) ...[
            _Notice(text: _notice!, onClose: () => setState(() => _notice = null)),
            const SizedBox(height: 12),
          ],
          if (_busy) ...[
            const LinearProgressIndicator(minHeight: 2, color: _kOnPaper),
            const SizedBox(height: 12),
          ],

          if (v == null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 36),
              child: Text(
                _analyzedTab ? '아직 분석한 영상이 없습니다.' : '아직 업로드한 영상이 없습니다.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: _kMuted, fontSize: 13.5),
              ),
            )
          else ...[
            if (v.rejectReason != null) ...[
              _Notice(text: v.rejectReason!),
              const SizedBox(height: 10),
            ],
            VideoStrip(
              videos: shown,
              current: i,
              onPaper: true,
              onPick: (next) => setState(() {
                _at = next;
                _confirming = null;
              }),
            ),
            _NavRow(
              index: i,
              total: shown.length,
              onStep: (delta) => setState(() {
                // 끝에서 반대쪽으로 돈다 — 목록이 짧아 끝이 금방 온다.
                _at = (i + delta + shown.length) % shown.length;
                _confirming = null;
              }),
            ),
            const SizedBox(height: 10),
            /* 🔴 **바로 위에 얇은 검정 선 하나** (2026-09-25 사용자 요청) —
               넘기는 줄과 **되돌릴 수 없는 단추**를 가른다. */
            const Divider(
              key: Key('videos-actions-line'),
              color: Color(0x33000000),
              height: 1,
              thickness: 1,
            ),
            const SizedBox(height: 10),
            /* 🔴 **삭제는 왼쪽, 대표는 오른쪽** (2026-09-25 사용자 지시) —
               한 줄에 양 끝으로 벌린다. */
            _Actions(
              video: v,
              analyzedTab: _analyzedTab,
              confirming: _confirming == v.id,
              publishOpen: _publishing == v.id,
              busy: _busy,
              onConfirmDelete: () => setState(() => _confirming = v.id),
              onCancelDelete: () => setState(() => _confirming = null),
              onDelete: () => _remove(v),
              onToggleFeatured: () => _toggleFeatured(v),
              onTogglePublish: () => _togglePublish(v),
            ),
            /* 🔴 **단추와 같은 갈래에서만 낸다.** 그냥 올린 영상은 리포트가
               없어 추천 판에 아예 안 들어간다 — 거기 두면 「이 장면이 돕니다」가
               사실이 아닌 말이 된다. */
            if (_analyzedTab && v.passed && v.isFeatured) ...[
              const SizedBox(height: 8),
              const Text(
                '추천 판에서 나를 소개할 때 이 장면이 돕니다.',
                textAlign: TextAlign.center,
                style: TextStyle(color: _kMuted, fontSize: 12),
              ),
            ],
            if (_publishing == v.id && !v.isPublic) ...[
              const SizedBox(height: 12),
              PublishForm(
                key: ValueKey('publish-${v.id}'),
                onPaper: true,
                onCancel: () => setState(() => _publishing = null),
                onSave: (title, what) => _publish(v, title, what),
              ),
            ],
            /* 🔴 **분석 갈래에서만 낸다** — 그냥 올린 영상에는 리포트가 없다.
               ⚠️ 상태를 안 가린다: 「분석 중」·「찾을 수 없음」도 판 안에서
               말한다. 단추가 상태마다 사라지면 눌러 볼 데가 없어진다. */
            if (_analyzedTab) ...[
              const SizedBox(height: 12),
              /* 🔴 **좌우를 꽉 채우지 않는다** (2026-09-25 사용자 요청:
                 「컴팩트하게 좌우 쫙 줄여」). 전에는 `minimumSize:
                 Size.fromHeight(44)` 라 폭을 통째로 먹어서, 이 화면에서 가장
                 큰 단추가 **가장 덜 쓰는 것**이 되어 있었다. */
              Center(
                child: _Pill(
                  pillKey: const Key('videos-report'),
                  icon: _reportWanted
                      ? Symbols.keyboard_arrow_up
                      : Symbols.lab_profile,
                  label: _reportWanted ? '리포트 닫기' : '리포트 보기',
                  selected: _reportWanted,
                  onTap: _toggleReport,
                ),
              ),
              /* 🔴 **제자리에서 펴진다**([ReportPanel] 머리말). 높이를 0 에서
                 제 크기까지 늘리면서 **같이 흐려졌다 드러난다** — 둘 중 하나만
                 하면 접힐 때 글자가 뭉개지거나 빈 칸이 툭 사라진다.
                 ⛔ `Navigator.push` 로 되돌리지 말 것. */
              if (_reportMounted)
                AnimatedBuilder(
                  animation: _reportCurve,
                  builder: (context, child) => ClipRect(
                    child: Align(
                      alignment: Alignment.topCenter,
                      heightFactor: _reportCurve.value,
                      child: Opacity(opacity: _reportCurve.value, child: child),
                    ),
                  ),
                  /* ⚠️ **`child:` 자리가 아니라 builder 밖이다** — 매 프레임
                     도는 애니메이션이라 여기 두면 판이 초당 60번 다시 지어진다.
                     🔴 그런데 **영상이 바뀌면 다시 지어져야 한다** — 열쇠에
                     영상 id 를 넣어 그때만 갈아 끼운다. */
                  child: ReportPanel(
                    key: const Key('inline-report'),
                    videoId: v.id,
                    title: v.title,
                  ),
                ),
            ],
          ],
        ],
      );

  Future<void> _pick() async {
    setState(() => _notice = null);
    final PickedClip? picked;
    try {
      picked = await ClipPicker().fromGallery();
    } catch (e) {
      setState(() => _notice = '영상을 고르지 못했습니다: $e');
      return;
    }
    // 고르다 말았다 — 오류가 아니다.
    if (picked == null) return;

    /* 🔴 **형식·용량은 여기서 막는다** — 그 둘은 `upload-url` 이 422 로 튕겨
       아무 데도 안 남는다. 길이·해상도는 반대로 서버가 반려 사유로 남겨야
       하는 것이라(SFR-001) 여기서 가로채지 않는다. */
    final bad = checkClip(picked.file);
    if (bad != null) {
      setState(() => _notice = bad);
      return;
    }

    setState(() => _busy = true);
    try {
      final saved = await ref.read(myVideosProvider.notifier).upload(
            file: picked.file,
            meta: picked.meta,
            sportCode: kUploadSportCode,
          );
      if (!mounted) return;
      setState(() {
        /* 🔴 **보낸 뜻이 아니라 돌아온 응답을 믿는다.** 우리는 `analyze:
           false` 로 보냈지만 서버가 무시하고 분석을 걸 수 있다 — 그러면
           `analysis_job_id` 가 채워져 오고, 그때는 「분석 영상」이 사실이다. */
        _analyzedTab = saved.analyzed;
        _at = 0;
        if (!saved.passed) {
          _notice = saved.rejectReason ?? '규격에 맞지 않아 반려됐습니다.';
        } else {
          /* 🔴 **같은 영상을 다시 올렸으면 그 자리에서 말한다**(CCC 48).
             이 사실은 **등록 응답에만** 실려 오므로 지금 안 적으면 다시 볼
             방법이 없다. 막지는 않는다 — 올라간 것은 올라간 것이고 안내다. */
          _notice = duplicateNotice(saved);
        }
      });
    } catch (e) {
      if (mounted) setState(() => _notice = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleFeatured(MyVideo v) async {
    setState(() => _notice = null);
    try {
      await ref.read(myVideosProvider.notifier).setFeatured(v.id, !v.isFeatured);
    } catch (e) {
      if (mounted) setState(() => _notice = '$e');
    }
  }

  Future<void> _togglePublish(MyVideo v) async {
    setState(() => _notice = null);
    if (v.isPublic) {
      try {
        await ref.read(myVideosProvider.notifier).unpublish(v.id);
      } catch (e) {
        if (mounted) setState(() => _notice = '$e');
      }
      return;
    }
    // 🔴 **열려 있으면 닫는다** — 같은 단추가 「전체 공개」이자 「닫기」다.
    setState(() => _publishing = _publishing == v.id ? null : v.id);
  }

  Future<void> _publish(MyVideo v, String title, String what) async {
    setState(() => _notice = null);
    try {
      await ref
          .read(myVideosProvider.notifier)
          .publish(v.id, title: title, description: what);
      if (mounted) setState(() => _publishing = null);
    } catch (e) {
      if (mounted) setState(() => _notice = '$e');
    }
  }

  Future<void> _remove(MyVideo v) async {
    setState(() {
      _notice = null;
      _busy = true;
    });
    try {
      await ref.read(myVideosProvider.notifier).remove(v.id);
      if (mounted) setState(() => _confirming = null);
    } catch (e) {
      if (mounted) setState(() => _notice = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

/// 🔴 **「영상 분석」 화면과 같은 색이다** — 두 화면이 나란히 놓여도 한 제품으로
/// 읽히게(`analyze_screen.dart` 의 같은 이름들과 값이 같다).
const Color _kBg = Color(0xFF000000);
const Color _kOn = Color(0xFFFFFFFF);
const Color _kPaper = kSheetPaper;
const Color _kOnPaper = Color(0xFF14161A);
const Color _kMuted = Color(0xFF6B7078);

/// 되돌릴 수 없는 것 — 🔴 **완전한 빨강**(2026-09-25 사용자 요청: 「해당 영상
/// 삭제는 완전 빨간색으로」). 전에는 흐린 회색 글자 단추라 대표·공개와 같은
/// 무게로 보였다.
const Color kVideoDanger = Color(0xFFD32F2F);

const double _kGutter = 20;

/// 위 칸 — **지금 보고 있는 영상**이 검은 바탕에서 돈다.
class _Stage extends StatelessWidget {
  const _Stage({required this.video, required this.loading});

  final MyVideo? video;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    final v = video;
    if (v != null) {
      /* 🔴 **열쇠가 영상 id 다.** 넘길 때마다 위젯을 갈아 끼워야 옛 컨트롤러가
         제때 버려진다 — 안 버리면 디코더가 쌓여 몇 편 뒤부터 아무것도 안 열린다
         (`clip_player.dart` 머리말). */
      return ClipPlayer(key: ValueKey(v.id), videoId: v.id, fill: true);
    }
    if (loading) {
      // 🔴 **작게** — 분석 화면과 같은 크기다(큰 원은 화면을 다 먹는다).
      return const Center(
        child: SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 1.8, color: Colors.white24),
        ),
      );
    }
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Symbols.video_library, color: _kOn, size: 26, weight: 300),
          SizedBox(height: 10),
          Text(
            '내 영상',
            style: TextStyle(color: _kOn, fontSize: 16, fontWeight: FontWeight.w700),
          ),
          SizedBox(height: 4),
          Text(
            '올린 클립과 분석한 클립이 여기 모입니다',
            style: TextStyle(color: Color(0x8CFFFFFF), fontSize: 12.5),
          ),
        ],
      ),
    );
  }
}

class _Centered extends StatelessWidget {
  const _Centered({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(color: _kMuted, fontSize: 13.5, height: 1.5),
          ),
        ),
      );
}

/// 🔴 **종목을 묻지 않는다 — 축구 하나다**(미결 `ho` 39번, 웹 `lib/sports.ts`
/// 와 같은 판단). 고를 것이 하나뿐인 단추는 무엇을 고르라는 것인지 안 읽힌다.
///
/// 🔴 **종목을 되살리면 여기에 고르는 자리를 같이 되살린다** — 안 그러면 다른
/// 종목 영상이 **축구 루브릭으로 조용히 채점된다.**
const String kUploadSportCode = 'football';

/// 같은 내용을 다시 올렸을 때의 안내 (웹 `lib/duplicateNotice.ts`).
///
/// 🔴 **막지 않는다** — 올라간 것은 올라간 것이고 이건 안내다. 분석이
/// 결정론적이라 다시 돌려도 같은 결과가 나오는데, 안내가 없으면 사람이
/// 같은 영상을 계속 다시 올린다(실서버에서 아홉 번 있었다).
String? duplicateNotice(MyVideo saved) {
  if (saved.duplicateOfVideoId == null) return null;
  return switch (saved.duplicateStatus) {
    'succeeded' => '같은 영상을 전에 분석한 적이 있어 그 결과를 그대로 씁니다.',
    'failed' => '같은 영상을 전에 분석했고 그때도 실패했습니다'
        '${saved.duplicateFailureReason == null ? '.' : ' — ${saved.duplicateFailureReason}'}',
    _ => '같은 영상을 전에 올린 적이 있습니다.',
  };
}

/// 갈래 둘 + **업로드** — 🔴 셋이 한 줄이다(위 `_paper` 주석).
///
/// 🔴 **편수를 안 적는다** — 몇 편인지는 아래 `1 / N` 이 이미 말하고 있다.
class _Tabs extends StatelessWidget {
  const _Tabs({
    required this.analyzed,
    required this.busy,
    required this.onPick,
    required this.onUpload,
  });

  final bool analyzed;
  final bool busy;
  final ValueChanged<bool> onPick;
  final VoidCallback onUpload;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: _Pill(
              pillKey: const Key('tab-analyzed'),
              label: '분석 영상',
              selected: analyzed,
              compact: true,
              onTap: () => onPick(true),
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _Pill(
              pillKey: const Key('tab-uploaded'),
              label: '업로드 영상',
              selected: !analyzed,
              compact: true,
              onTap: () => onPick(false),
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _Pill(
              pillKey: const Key('videos-upload'),
              icon: Symbols.upload,
              label: '업로드 하기',
              compact: true,
              onTap: busy ? null : onUpload,
            ),
          ),
        ],
      );
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, this.onClose});

  final String text;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.fromLTRB(12, 10, onClose == null ? 12 : 4, 10),
        decoration: BoxDecoration(
          color: _kOnPaper.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                text,
                style: const TextStyle(
                  color: _kOnPaper,
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
            ),
            if (onClose != null)
              IconButton(
                icon: const Icon(Symbols.close, size: 18),
                color: _kMuted,
                onPressed: onClose,
                tooltip: '닫기',
              ),
          ],
        ),
      );
}

/// 🔴 **한 편뿐이어도 그린다** — `1 / 1` 이 보여야 갈래 안에 몇 편이 있는지
/// 알 수 있고, 갈래를 바꿔도 줄이 사라졌다 나타나지 않는다. 다만 넘길 데가
/// 없으므로 두 단추는 잠근다.
class _NavRow extends StatelessWidget {
  const _NavRow({
    required this.index,
    required this.total,
    required this.onStep,
  });

  final int index;
  final int total;
  final ValueChanged<int> onStep;

  @override
  Widget build(BuildContext context) {
    final can = total > 1;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        IconButton(
          key: const Key('videos-prev'),
          icon: const Icon(Symbols.chevron_left),
          color: _kOnPaper,
          disabledColor: _kMuted.withValues(alpha: 0.4),
          tooltip: '이전 영상',
          onPressed: can ? () => onStep(-1) : null,
        ),
        Text(
          '${index + 1} / $total',
          style: const TextStyle(
            color: _kOnPaper,
            fontSize: 13,
            fontWeight: FontWeight.w700,
            fontFeatures: [FontFeature.tabularFigures()],
          ),
        ),
        IconButton(
          key: const Key('videos-next'),
          icon: const Icon(Symbols.chevron_right),
          color: _kOnPaper,
          disabledColor: _kMuted.withValues(alpha: 0.4),
          tooltip: '다음 영상',
          onPressed: can ? () => onStep(1) : null,
        ),
      ],
    );
  }
}

/// 지우기 · 대표 · 공개 — 🔴 **모두 알약이다**(2026-09-25 사용자 요청:
/// 「알약 버튼으로 컴팩트하게」).
class _Actions extends StatelessWidget {
  const _Actions({
    required this.video,
    required this.analyzedTab,
    required this.confirming,
    required this.publishOpen,
    required this.busy,
    required this.onConfirmDelete,
    required this.onCancelDelete,
    required this.onDelete,
    required this.onToggleFeatured,
    required this.onTogglePublish,
  });

  final MyVideo video;
  final bool analyzedTab;
  final bool confirming;
  final bool publishOpen;
  final bool busy;
  final VoidCallback onConfirmDelete;
  final VoidCallback onCancelDelete;
  final VoidCallback onDelete;
  final VoidCallback onToggleFeatured;
  final VoidCallback onTogglePublish;

  @override
  Widget build(BuildContext context) {
    /* 🔴 **한 번 더 묻는다** — 되돌릴 수 없다. 묻는 동안에는 다른 단추를
       치운다: 지울지 정하는 중에 대표를 세우는 것은 뜻이 안 맞고, 좁은
       폰에서 단추 넷이 한 줄에 서면 잘못 누른다. */
    if (confirming) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _Pill(
            pillKey: const Key('videos-delete-confirm'),
            icon: Symbols.delete_forever,
            label: busy ? '지우는 중…' : '정말 지웁니다',
            danger: true,
            onTap: busy ? null : onDelete,
          ),
          const SizedBox(width: 8),
          _Pill(
            pillKey: const Key('videos-delete-cancel'),
            label: '취소',
            onTap: busy ? null : onCancelDelete,
          ),
        ],
      );
    }

    /* 🔴 **한 줄에 양 끝으로 벌린다** (2026-09-25 사용자 지시: 「영상 삭제
       버튼이 왼쪽에 대표 영상 버튼이 오른쪽에」). 되돌릴 수 없는 것과 세워
       두는 것이 **나란히 붙어 있으면** 잘못 누른다.
       ⚠️ 오른쪽 자리는 갈래에 따라 대표이거나 공개다 — 둘 다 없는 경우
       (반려된 클립)에는 빈 자리를 둬서 삭제가 왼쪽에 그대로 있게 한다. */
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _Pill(
          pillKey: const Key('videos-delete'),
          icon: Symbols.delete,
          label: '영상 삭제',
          danger: true,
          onTap: onConfirmDelete,
        ),
        /* 🔴 **업로드 갈래에서만** 낸다. 분석을 건 영상은 리포트를 보려고
           올린 것이고, 영상 모음은 올린 장면을 훑는 자리다 — 성격이 다르다. */
        if (!analyzedTab)
          _Pill(
            pillKey: const Key('videos-publish'),
            icon: video.isPublic
                ? Symbols.visibility
                : publishOpen
                    ? Symbols.close
                    : Symbols.visibility_off,
            label: video.isPublic
                ? '전체 공개 중'
                : publishOpen
                    ? '닫기'
                    : '전체 공개',
            selected: video.isPublic,
            onTap: onTogglePublish,
          ),
        /* 🔴 **분석 갈래에서만** 낸다. 그냥 올린 영상은 리포트가 없어
           추천 판에 아예 안 들어가므로, 여기 단추를 두면 **아무 데도 안
           쓰이는 값**을 고르게 된다.
           ⚠️ 서버가 막는 것은 아니다 — 계약이 거부하는 것은 반려된
           클립뿐이고, 분석 안 한 영상도 세울 수는 있다. 화면의 판단이다.
           ⚠️ 반려된 클립에는 안 낸다 — 서버가 안 보는 영상이다. */
        if (analyzedTab && video.passed)
          _Pill(
            pillKey: const Key('videos-featured'),
            icon: video.isFeatured ? Symbols.stars : Symbols.star,
            label: '대표 영상',
            selected: video.isFeatured,
            onTap: onToggleFeatured,
          )
        else if (analyzedTab)
          // 🔴 반려된 클립 — 오른쪽 자리를 비워 둔다(위 주석).
          const SizedBox.shrink(),
      ],
    );
  }
}

/// 밝은 판 위의 알약 하나 — 🔴 **이 화면의 단추는 전부 이것이다.**
///
/// 분석 화면의 `_Button` 과 같은 모양(모서리 = 높이의 절반)이되, 여기는 줄에
/// 셋씩 서므로 **더 낮고 좁다**([compact]).
class _Pill extends StatelessWidget {
  const _Pill({
    required this.pillKey,
    required this.label,
    required this.onTap,
    this.icon,
    this.selected = false,
    this.danger = false,
    this.compact = false,
  });

  final Key pillKey;
  final String label;

  /// `null` 이면 잠긴 것이다 — 흐리게 그리고 안 눌린다.
  final VoidCallback? onTap;
  final IconData? icon;

  /// 켜져 있는가 — 면이 짙은 잉크로 찬다.
  final bool selected;

  /// 🔴 **되돌릴 수 없는가** — 완전한 빨강으로 찬다(위 [kVideoDanger]).
  final bool danger;

  /// 한 줄에 여럿 설 때 — 아이콘을 줄이고 글자를 한 줄로 조인다.
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final off = onTap == null;
    /* ⚠️ 한때 **검은 바탕 갈래**(`dark`)가 있었다 — 갈래 줄을 영상 위로
       올렸던 회차다. 줄이 판으로 내려오면서 걷었다. */
    const base = _kOnPaper;
    const over = _kPaper;
    final face = danger
        ? kVideoDanger
        : selected
            ? base
            : Colors.transparent;
    final filled = danger || selected;
    final ink = filled ? (danger ? _kOn : over) : base;
    return Opacity(
      opacity: off ? 0.45 : 1,
      child: GestureDetector(
        key: pillKey,
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          height: compact ? 34 : 36,
          /* 🔴 **글자와 아이콘에 딱 맞춘다** (2026-09-25 사용자 요청: 「좌우
             패딩을 버튼 안에 글자랑 아이콘에 맞춰서 패딩 완전 줄여」). */
          padding: EdgeInsets.symmetric(horizontal: compact ? 6 : 10),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: face,
            border: Border.all(
              color: filled ? face : base.withValues(alpha: 0.3),
            ),
            borderRadius: BorderRadius.circular(compact ? 17 : 18),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: compact ? 14 : 17, color: ink),
                SizedBox(width: compact ? 4 : 6),
              ],
              /* 🔴 **좁은 줄에서 글자가 넘친다** — 셋이 한 줄에 서면 폭 360
                 에서 「업로드 하기」가 잘린다. 줄이는 쪽을 택한다(줄바꿈은
                 알약 높이를 들쭉날쭉하게 만든다). */
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: ink,
                    fontSize: compact ? 11.5 : 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
