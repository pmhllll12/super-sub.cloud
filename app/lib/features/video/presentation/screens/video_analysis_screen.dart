import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../../../core/widgets/figure_background.dart';
import '../../../../core/widgets/floating_nav_bar.dart';
import '../../../../core/widgets/glass_panel.dart';

const Color _kBg = Color(0xFF000000);
const Color _kOnDark = Color(0xFFFFFFFF);

/// 판 모서리. 홈의 카드와 같은 값이다 — 갈리면 두 화면이 다른 앱처럼 보인다.
const double _kPanelRadius = 18;

/// 위쪽 가로 판의 높이.
const double _kTopPanelHeight = 150;

/// 고르는 판 둘의 높이.
const double _kPickerHeight = 96;

/// 영상 분석 화면.
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
          _notReady();
        },
      ),
      body: Stack(
        fit: StackFit.expand,
        children: [
          const FigureBackground(),
          SafeArea(
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                20,
                12,
                20,
                // 바는 자리를 차지하지 않고 떠 있다 — 아래 판이 바에 먹히지
                // 않도록 그만큼 띄운다.
                FloatingNavBar.heightOf(context) + 12,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _header(context),
                  const SizedBox(height: 14),
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
                      child: Center(
                        child: Text(
                          '분석한 영상이 여기 쌓입니다',
                          style: TextStyle(color: _kOnDark, fontSize: 15),
                        ),
                      ),
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

  Widget _header(BuildContext context) {
    return Row(
      children: [
        IconButton(
          key: const Key('video-back'),
          color: _kOnDark,
          icon: const Icon(Symbols.arrow_back, weight: 300),
          tooltip: '뒤로',
          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/home'),
        ),
        const Expanded(
          child: Text(
            '영상 분석',
            style: TextStyle(
              color: _kOnDark,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
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
