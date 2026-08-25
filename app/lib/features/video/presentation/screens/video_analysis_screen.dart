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

/// 영상 분석 화면.
///
/// 판이 둘이다 — 위에 가로로 긴 것 하나, 아래에 하단 바 위까지 오는 세로로 긴
/// 것 하나. 둘 다 홈의 카드와 같은 굴절 유리를 쓰되 **둘레를 도는 빛은 두지
/// 않는다**: 판이 커서 도는 선이 화면을 계속 훑으면 내용보다 먼저 눈에 든다.
class VideoAnalysisScreen extends ConsumerWidget {
  const VideoAnalysisScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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
          _notReady(context);
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
                  const SizedBox(
                    height: _kTopPanelHeight,
                    child: GlassPanel(
                      radius: _kPanelRadius,
                      child: _TopPanelBody(),
                    ),
                  ),
                  const SizedBox(height: 14),
                  // 남은 자리를 다 쓴다 — 하단 바 바로 위까지 내려온다.
                  const Expanded(
                    child: GlassPanel(
                      radius: _kPanelRadius,
                      child: _BottomPanelBody(),
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

  /// 제목 줄. 오른쪽 끝에 바로 찍는 버튼이 선다.
  Widget _header(BuildContext context) {
    return Row(
      children: [
        IconButton(
          key: const Key('video-back'),
          color: _kOnDark,
          icon: const Icon(Symbols.arrow_back, weight: 300),
          tooltip: '뒤로',
          onPressed: () => context.canPop() ? context.pop() : context.go('/home'),
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
        _CameraButton(onTap: () => _notReady(context)),
      ],
    );
  }

  void _notReady(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('준비 중입니다')),
    );
  }
}

/// 바로 찍어서 분석하는 버튼.
class _CameraButton extends StatelessWidget {
  const _CameraButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox.square(
      dimension: 44,
      child: GlassPanel(
        key: const Key('video-camera'),
        radius: 22,
        child: InkWell(
          onTap: onTap,
          child: const Icon(
            Symbols.photo_camera,
            color: _kOnDark,
            size: 22,
            weight: 300,
          ),
        ),
      ),
    );
  }
}

class _TopPanelBody extends StatelessWidget {
  const _TopPanelBody();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text(
        '분석할 영상을 올리세요',
        style: TextStyle(color: _kOnDark, fontSize: 15),
      ),
    );
  }
}

class _BottomPanelBody extends StatelessWidget {
  const _BottomPanelBody();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Text(
        '분석한 영상이 여기 쌓입니다',
        style: TextStyle(color: _kOnDark, fontSize: 15),
      ),
    );
  }
}
