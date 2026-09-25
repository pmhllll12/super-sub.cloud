import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../../core/widgets/figure_background.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/glass_panel.dart';
import '../chat_pane.dart';

const Color _kBg = Color(0xFF000000);
const Color _kOnDark = Color(0xFFFFFFFF);

/// 판 모서리. 홈의 카드와 같은 값이다 — 갈리면 두 화면이 다른 앱처럼 보인다.
const double _kPanelRadius = 18;

/// 위쪽 가로 판의 높이.
const double _kTopPanelHeight = 150;

/// 판과 화면 벽 사이.
const double _kEdge = 6;

/// 고르는 판 둘의 높이.
const double _kPickerHeight = 96;

/// ⛔ **더 이상 라우트에 안 걸려 있다 (2026-09-24).** `/videos` 는 이제
/// `analyze_screen.dart` 의 `AnalyzeScreen` 이다.
///
/// 🔴 **왜 갈아 치웠나 — 이 화면은 껍데기였다.** 「바로 찍기」·「앨범에서」가
/// 둘 다 「준비 중입니다」 스낵바여서 **영상을 고를 수조차 없었고**, 업로드도
/// 분석도 리포트도 없었다. 도는 것은 Mock 채팅([ChatPane])뿐이었고, 실제
/// 업로드 배선은 `my_videos_screen.dart` 에만 있어 둘이 서로를 몰랐다.
///
/// ⚠️ **지우지 않고 남겨 둔 까닭**: [ChatPane] 을 화면에 앉히는 짜임이 여기
/// 말고 없다. 분석 에이전트 채팅이 계약으로 열리면 **새 화면의 리포트 아래
/// 보조 칸**으로 다시 쓸 자리가 이 파일이다(웹도 오른쪽 판 맨 아래에 둔다).
/// 그때까지 쓰이지 않는다 — **살아 있는 화면으로 읽지 말 것.**
///
/// 판이 둘이다 — 위에 가로로 긴 것 하나, 아래에 하단 바 위까지 오는 세로로 긴
/// 것 하나. 둘 다 홈의 카드와 같은 굴절 유리를 쓰되 **둘레를 도는 빛은 두지
/// 않는다**: 판이 커서 도는 선이 화면을 계속 훑으면 내용보다 먼저 눈에 든다.
class VideoAnalysisScreen extends ConsumerStatefulWidget {
  const VideoAnalysisScreen({super.key});

  @override
  ConsumerState<VideoAnalysisScreen> createState() =>
      _VideoAnalysisScreenState();
}

class _VideoAnalysisScreenState extends ConsumerState<VideoAnalysisScreen> {
  /// 위 판을 눌러 펼쳤는가.
  bool _picking = false;

  void _notReady() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('준비 중입니다')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kBg,
      extendBody: true,
      bottomNavigationBar: FloatingNavBar(
        currentIndex: 1,
        onTap: (index) {
          if (index == 0) {
            context.go('/home');
            return;
          }
          // 🔴 3번은 내 프로필 — 홈과 같은 배선이다(2026-09-22).
          if (index == 3) {
            context.go('/profile');
            return;
          }
          /* 🔴 **1번은 이 화면 자신이다**(`/videos` 가 여기다) — 아무것도 안
             한다. `context.go` 를 부르면 같은 화면을 다시 쌓아 **뒤로 가기가
             한 번 더 필요해진다.** */
          if (index == 1) return;
          _notReady();
        },
      ),
      body: Stack(
        fit: StackFit.expand,
        children: [
          const FigureBackground(),
          SafeArea(
            child: Padding(
              // 판을 화면 벽에 붙인다. 바는 자리를 차지하지 않고 떠 있으므로
              // 딱 그 높이만큼만 띄워 판이 바로 위까지 오게 한다.
              padding: EdgeInsets.fromLTRB(
                _kEdge,
                _kEdge,
                _kEdge,
                FloatingNavBar.heightOf(context),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SizedBox(
                    height: _kTopPanelHeight,
                    child: GlassPanel(
                      radius: _kPanelRadius,
                      child: InkWell(
                        key: const Key('video-pick'),
                        onTap: () => setState(() => _picking = !_picking),
                        child: Center(
                          child: Text(
                            _picking ? '어디서 가져올까요' : '분석할 영상을 골라주세요',
                            style: const TextStyle(
                              color: _kOnDark,
                              fontSize: 15,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  // 고르는 판 둘. **위 판 안에 넣지 않는다** — 유리 안에 유리를
                  // 또 넣으면 안쪽이 아직 안 끝난 바깥을 읽어 내용이 프레임째로
                  // 사라진다(refractive_glass.dart 주석). 밖에 두면 다른 판과
                  // 똑같은 유리를 그대로 쓸 수 있다.
                  AnimatedSize(
                    duration: const Duration(milliseconds: 260),
                    curve: Curves.easeOutCubic,
                    child: _picking
                        ? Padding(
                            padding: const EdgeInsets.only(top: 14),
                            child: SizedBox(
                              height: _kPickerHeight,
                              child: Row(
                                children: [
                                  Expanded(
                                    child: _PickTile(
                                      tileKey: const Key('video-pick-camera'),
                                      icon: Symbols.photo_camera,
                                      label: '바로 찍기',
                                      onTap: _notReady,
                                    ),
                                  ),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: _PickTile(
                                      tileKey: const Key('video-pick-gallery'),
                                      icon: Symbols.photo_library,
                                      label: '앨범에서',
                                      onTap: _notReady,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                        : const SizedBox(width: double.infinity),
                  ),
                  const SizedBox(height: 14),
                  // 남은 자리를 다 쓴다 — 하단 바 바로 위까지 내려온다.
                  const Expanded(
                    child: GlassPanel(
                      radius: _kPanelRadius,
                      child: ChatPane(),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

}

/// 영상을 어디서 가져올지 고르는 판. 다른 판과 같은 유리다.
class _PickTile extends StatelessWidget {
  const _PickTile({
    required this.tileKey,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final Key tileKey;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      radius: _kPanelRadius,
      child: InkWell(
        key: tileKey,
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: _kOnDark, size: 26, weight: 300),
            const SizedBox(height: 8),
            Text(
              label,
              style: const TextStyle(color: _kOnDark, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}
