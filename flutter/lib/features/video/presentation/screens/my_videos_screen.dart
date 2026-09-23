import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../data/clip_file.dart';
import '../../data/models/my_video.dart';
import '../../data/pick_clip.dart';
import '../my_videos_controller.dart';
import '../widgets/clip_player.dart';
import '../widgets/publish_form.dart';
import '../widgets/video_strip.dart';
import 'report_screen.dart';

/// 내 영상 — 웹 `/me` 오른쪽 칸(`MyVideos.tsx`)을 폰 세로에 맞춰 옮긴 것이다.
///
/// 웹은 좌우 두 단이라 이것이 옆 칸인데, **폰에는 옆으로 펼 자리가 없어**
/// 프로필에서 밀고 들어오는 전용 화면으로 뒀다(이식 지침 §2-2).
class MyVideosScreen extends ConsumerStatefulWidget {
  const MyVideosScreen({super.key});

  @override
  ConsumerState<MyVideosScreen> createState() => _MyVideosScreenState();
}

class _MyVideosScreenState extends ConsumerState<MyVideosScreen> {
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

  @override
  Widget build(BuildContext context) {
    final asyncVideos = ref.watch(myVideosProvider);

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        foregroundColor: _kOn,
        title: const Text('내 영상'),
        actions: [
          IconButton(
            key: const Key('videos-upload'),
            icon: const Icon(Symbols.upload),
            tooltip: '업로드',
            onPressed: _busy ? null : _pick,
          ),
        ],
      ),
      body: SafeArea(
        child: asyncVideos.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Text(
                '$e',
                textAlign: TextAlign.center,
                style: TextStyle(color: _kOn.withValues(alpha: 0.75)),
              ),
            ),
          ),
          data: _body,
        ),
      ),
    );
  }

  Widget _body(List<MyVideo> all) {
    final split = splitVideos(all);
    final shown = _analyzedTab ? split.analyzed : split.uploaded;
    /* 🔴 **자리를 상태로 들고 있으므로 목록이 짧아지면 넘칠 수 있다.** 그릴
       때 여기서 한 번 잡는다 — 탭을 누를 때만 0 으로 되돌리면 목록 자체가
       줄어드는 경우(지운 뒤)를 놓친다. */
    final i = shown.isEmpty ? 0 : _at.clamp(0, shown.length - 1);
    final v = shown.isEmpty ? null : shown[i];

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
      children: [
        _Tabs(
          analyzed: _analyzedTab,
          onPick: (next) => setState(() {
            _analyzedTab = next;
            _at = 0;
            _confirming = null;
            _publishing = null;
          }),
        ),
        const SizedBox(height: 12),

        // 올리는 중에 무슨 일이 있었는지 — 거른 사유 · 반려 사유 · 실패 사유.
        if (_notice != null) ...[
          _Notice(text: _notice!, onClose: () => setState(() => _notice = null)),
          const SizedBox(height: 12),
        ],
        if (_busy) ...[
          const LinearProgressIndicator(minHeight: 2),
          const SizedBox(height: 12),
        ],

        if (v == null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 40),
            child: Text(
              _analyzedTab ? '아직 분석한 영상이 없습니다.' : '아직 업로드한 영상이 없습니다.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _kOn.withValues(alpha: 0.6)),
            ),
          )
        else ...[
          ClipPlayer(videoId: v.id),
          if (v.rejectReason != null) ...[
            const SizedBox(height: 10),
            _Notice(text: v.rejectReason!),
          ],
          const SizedBox(height: 10),
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
            Text(
              '추천 판에서 나를 소개할 때 이 장면이 돕니다.',
              style: TextStyle(
                color: _kOn.withValues(alpha: 0.6),
                fontSize: 12,
              ),
            ),
          ],
          if (_publishing == v.id && !v.isPublic) ...[
            const SizedBox(height: 12),
            PublishForm(
              key: ValueKey('publish-${v.id}'),
              onCancel: () => setState(() => _publishing = null),
              onSave: (title, what) => _publish(v, title, what),
            ),
          ],
          const SizedBox(height: 16),
          VideoStrip(
            videos: shown,
            current: i,
            onPick: (next) => setState(() {
              _at = next;
              _confirming = null;
            }),
          ),
          /* 🔴 **분석 갈래에서만 낸다** — 그냥 올린 영상에는 리포트가 없다.
             ⚠️ 상태를 안 가린다: 「분석 중」·「찾을 수 없음」도 판 안에서
             말한다. 단추가 상태마다 사라지면 눌러 볼 데가 없어진다. */
          if (_analyzedTab) ...[
            const SizedBox(height: 16),
            OutlinedButton.icon(
              key: const Key('videos-report'),
              icon: const Icon(Symbols.lab_profile, size: 18),
              label: const Text('해당 영상 리포트 보기'),
              style: OutlinedButton.styleFrom(
                foregroundColor: _kOn,
                side: BorderSide(color: _kOn.withValues(alpha: 0.4)),
                minimumSize: const Size.fromHeight(44),
              ),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => ReportScreen(videoId: v.id, title: v.title),
                ),
              ),
            ),
          ],
        ],
      ],
    );
  }

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

const Color _kBg = Color(0xFF14201A);
const Color _kOn = Color(0xFFFFFFFF);
const Color _kSeed = Color(0xFF70ED88);

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

/// 갈래 알약 둘.
///
/// 🔴 **편수를 안 적는다** — 몇 편인지는 아래 `1 / N` 이 이미 말하고 있다.
class _Tabs extends StatelessWidget {
  const _Tabs({required this.analyzed, required this.onPick});

  final bool analyzed;
  final ValueChanged<bool> onPick;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: _pill('분석 영상', analyzed, () => onPick(true), 'tab-analyzed')),
        const SizedBox(width: 8),
        Expanded(child: _pill('업로드 영상', !analyzed, () => onPick(false), 'tab-uploaded')),
      ],
    );
  }

  Widget _pill(String label, bool on, VoidCallback onTap, String key) {
    return Semantics(
      selected: on,
      button: true,
      child: Material(
        color: on ? _kSeed.withValues(alpha: 0.2) : Colors.transparent,
        borderRadius: BorderRadius.circular(999),
        child: InkWell(
          key: Key(key),
          borderRadius: BorderRadius.circular(999),
          onTap: onTap,
          child: Container(
            height: 38,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: on ? _kSeed : _kOn.withValues(alpha: 0.25),
              ),
            ),
            child: Text(
              label,
              style: TextStyle(
                color: on ? _kSeed : _kOn.withValues(alpha: 0.7),
                fontSize: 13,
                fontWeight: on ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, this.onClose});

  final String text;
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 4, 10),
      decoration: BoxDecoration(
        color: _kOn.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: _kOn.withValues(alpha: 0.9),
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
          if (onClose != null)
            IconButton(
              icon: const Icon(Symbols.close, size: 18),
              color: _kOn.withValues(alpha: 0.7),
              onPressed: onClose,
              tooltip: '닫기',
            ),
        ],
      ),
    );
  }
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
          color: _kOn,
          tooltip: '이전 영상',
          onPressed: can ? () => onStep(-1) : null,
        ),
        Text(
          '${index + 1} / $total',
          style: TextStyle(
            color: _kOn.withValues(alpha: 0.8),
            fontSize: 13,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
        IconButton(
          key: const Key('videos-next'),
          icon: const Icon(Symbols.chevron_right),
          color: _kOn,
          tooltip: '다음 영상',
          onPressed: can ? () => onStep(1) : null,
        ),
      ],
    );
  }
}

/// 지우기 · 대표 · 공개.
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
        children: [
          Expanded(
            child: FilledButton(
              key: const Key('videos-delete-confirm'),
              onPressed: busy ? null : onDelete,
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFB3261E),
                foregroundColor: _kOn,
              ),
              child: Text(busy ? '지우는 중…' : '정말 지웁니다'),
            ),
          ),
          const SizedBox(width: 8),
          TextButton(
            key: const Key('videos-delete-cancel'),
            onPressed: busy ? null : onCancelDelete,
            style: TextButton.styleFrom(foregroundColor: _kOn),
            child: const Text('취소'),
          ),
        ],
      );
    }

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        TextButton.icon(
          key: const Key('videos-delete'),
          icon: const Icon(Symbols.delete, size: 18),
          label: const Text('해당 영상 삭제'),
          style: TextButton.styleFrom(
            foregroundColor: _kOn.withValues(alpha: 0.75),
          ),
          onPressed: onConfirmDelete,
        ),
        Wrap(
          spacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            /* 🔴 **업로드 갈래에서만** 낸다. 분석을 건 영상은 리포트를 보려고
               올린 것이고, 영상 모음은 올린 장면을 훑는 자리다 — 성격이 다르다. */
            if (!analyzedTab)
              TextButton.icon(
                key: const Key('videos-publish'),
                icon: Icon(
                  video.isPublic
                      ? Symbols.visibility
                      : publishOpen
                          ? Symbols.close
                          : Symbols.visibility_off,
                  size: 18,
                ),
                label: Text(
                  video.isPublic
                      ? '전체 공개 중'
                      : publishOpen
                          ? '닫기'
                          : '전체 공개',
                ),
                style: TextButton.styleFrom(
                  foregroundColor: video.isPublic ? _kSeed : _kOn.withValues(alpha: 0.75),
                ),
                onPressed: onTogglePublish,
              ),
            /* 🔴 **분석 갈래에서만** 낸다. 그냥 올린 영상은 리포트가 없어
               추천 판에 아예 안 들어가므로, 여기 단추를 두면 **아무 데도 안
               쓰이는 값**을 고르게 된다.
               ⚠️ 서버가 막는 것은 아니다 — 계약이 거부하는 것은 반려된
               클립뿐이고, 분석 안 한 영상도 세울 수는 있다. 화면의 판단이다.
               ⚠️ 반려된 클립에는 안 낸다 — 서버가 안 보는 영상이다. */
            if (analyzedTab && video.passed)
              TextButton.icon(
                key: const Key('videos-featured'),
                icon: Icon(
                  video.isFeatured ? Symbols.stars : Symbols.star,
                  size: 18,
                  fill: video.isFeatured ? 1 : 0,
                ),
                label: const Text('대표 영상 설정'),
                style: TextButton.styleFrom(
                  foregroundColor:
                      video.isFeatured ? _kSeed : _kOn.withValues(alpha: 0.75),
                ),
                onPressed: onToggleFeatured,
              ),
          ],
        ),
      ],
    );
  }
}
