import 'package:flutter/material.dart';

import '../../../../core/widgets/silver_edge.dart';
import '../../../../core/widgets/silver_sweep_border.dart';
import '../../data/models/my_video.dart';

/// 선 아래의 **가로로 굴리는 목록.** 넘기는 단추가 한 편씩 앞뒤로만 가는 데
/// 비해 여기서는 보고 싶은 것을 바로 고른다.
///
/// 🔴 **웹과 달리 영상 섬네일이 아니다.** 웹은 칸마다 `<video preload=metadata
/// #t=0.1>` 을 놓지만, 앱에서 `VideoPlayerController` N개는 **디코더 핸들을
/// N개 연다** — 안드로이드는 동시 디코더가 몇 개 안 돼서 목록이 길면 판이
/// 통째로 안 열린다. 그래서 웹이 **재생 주소가 없을 때 쓰는 폴백과 같은
/// 모양**(순번 칸)으로 간다.
///
/// ⚠️ 진짜 섬네일이 필요해지면 **서버에 포스터 이미지를 요청하는 것**이 맞다
/// (클립마다 첫 프레임 한 장). 앱에서 N개를 디코딩해 만드는 길로 가지 말 것.
///
/// 🔴 **한 편뿐이어도 그린다** — 갈래를 오갈 때 이 줄이 생겼다 없어지면 아래
/// 것들이 그때마다 들썩인다.
class VideoStrip extends StatelessWidget {
  const VideoStrip({
    super.key,
    required this.videos,
    required this.current,
    required this.onPick,
    this.onPaper = false,
  });

  final List<MyVideo> videos;
  final int current;
  final ValueChanged<int> onPick;

  /// 밝은 판 위인가 — 🔴 **완전한 원이다.**
  ///
  /// 2026-09-25 하루에 두 단계를 거쳤다: 네모 칸 → 「사각형 그냥 빼고」(테
  /// 없는 글자) → **원 + 실버 테**. 칸마다 네모를 두르면 짧은 목록에서도 줄이
  /// 상자로 빽빽해져 위아래 알약들과 다른 판처럼 보였고, 테를 아예 빼니
  /// 이번에는 **누르는 자리로 안 읽혔다.** 원은 둘 다 피한다.
  ///
  /// 🔴 고른 칸만 실버가 **돈다**. ⛔ 네모로 되돌리지 말 것.
  final bool onPaper;

  /// 밝은 판 위 칸의 지름 — 🔴 **완전한 원**이라 폭과 높이가 같다.
  static const double circle = 54;

  @override
  Widget build(BuildContext context) {
    final ink = onPaper ? _kOnPaper : Colors.white;
    return SizedBox(
      height: onPaper ? circle : 52,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: videos.length,
        separatorBuilder: (_, _) => SizedBox(width: onPaper ? 8 : 4),
        itemBuilder: (context, i) {
          final on = i == current;
          final state = videoState(videos[i]);
          final tint =
              on ? (onPaper ? _kOnPaper : _kSeed) : ink.withValues(alpha: 0.45);
          final inside = Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                '${i + 1}',
                style: TextStyle(
                  color: tint,
                  fontSize: onPaper ? 13 : 15,
                  fontWeight: on ? FontWeight.w800 : FontWeight.w600,
                  height: 1.1,
                ),
              ),
              /* 🔴 **상태를 글자로 적는다.** 섬네일이 없으니 칸끼리 구별할
                 것이 번호밖에 없는데, 반려된 클립을 모르고 고르면 왜 단추가
                 없는지 알 데가 없다. */
              Text(
                state.label,
                maxLines: 1,
                style: TextStyle(
                  color: tint.withValues(alpha: on ? 0.8 : 0.45),
                  fontSize: onPaper ? 8 : 9,
                  height: 1.2,
                ),
              ),
            ],
          );

          return Semantics(
            selected: on,
            button: true,
            label: '${i + 1}번째 영상 · ${state.label}',
            child: Material(
              color: Colors.transparent,
              shape: onPaper
                  ? const CircleBorder()
                  : RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
              child: InkWell(
                key: Key('strip-$i'),
                customBorder: onPaper ? const CircleBorder() : null,
                borderRadius: onPaper ? null : BorderRadius.circular(10),
                onTap: () => onPick(i),
                /* 🔴 **밝은 판에서는 완전한 원이다** (2026-09-25 사용자 요청:
                   「분석완료는 완전 원으로 버튼 두자. 외곽선 완전 세련된
                   실버색으로 하고, 선택된 분석완료 버튼만 실버색 돌아가게」).
                   ⛔ 네모로 되돌리지 말 것. */
                child: onPaper
                    ? SizedBox(
                        width: circle,
                        height: circle,
                        /* 🔴 **고른 칸에만 실버가 돈다** — 칸마다 돌면 서로 다른
                           박자로 돌아 「어디를 보라는 건지」가 사라진다
                           (`silver_sweep_border.dart` 머리말의 그 규칙이다). */
                        child: on
                            ? SilverSweepBorder(
                                radius: circle / 2,
                                // 🔴 밝은 판용 값이다 — [_kSweepOnPaper] 머리말.
                                color: _kSweepOnPaper,
                                baseColor: _kSweepBaseOnPaper,
                                strokeWidth: 1.4,
                                child: Center(child: inside),
                              )
                            : DecoratedBox(
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  border: Border.fromBorderSide(
                                    BorderSide(
                                      /* 🔴 **고른 칸보다 옅어야 한다**(위
                                         머리말). 진하면 안 고른 것이 고른
                                         것처럼 보인다. */
                                      color: SilverEdge.onWhite
                                          .withValues(alpha: 0.35),
                                      width: SilverEdge.onWhiteWidth,
                                    ),
                                  ),
                                ),
                                child: Center(child: inside),
                              ),
                      )
                    : Container(
                        width: 64,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color:
                              on ? _kSeed.withValues(alpha: 0.18) : Colors.white10,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: inside,
                      ),
              ),
            ),
          );
        },
      ),
    );
  }
}

const Color _kSeed = Color(0xFF70ED88);
const Color _kOnPaper = Color(0xFF14161A);

/// 밝은 판 위를 도는 실버 — 🔴 **어두운 쪽 실버를 그대로 쓰면 안 보인다.**
///
/// (2026-09-25 사용자: 「내가 선택한게 오히려 더 안보이고 선택 안한게 오히려
/// 선택한거 처럼 잘 보여」.) [SilverSweepBorder] 의 기본값(`#E8F0F4`)은 **검은
/// 화면에서 경계를 내려고 고른 밝은 값**이라 밝은 판에 붙어 사라졌고, 그 옆의
/// 안 고른 칸은 [SilverEdge.onWhite] 실선이라 또렷해서 **정반대로 읽혔다.**
///
/// 🔴 하단 바가 흰 막대가 되면서 **같은 것을 먼저 겪었다** — 그쪽 주석의
/// 「어두운 막대에서는 밝을수록 보였는데 흰 막대에서는 진할수록 보인다」가
/// 그것이다. 값은 [SilverEdge.onWhite] 를 한 단 더 눌러 은빛 결은 지킨다.
/// ⛔ 기본 실버로 되돌리지 말 것.
const Color _kSweepOnPaper = Color(0xFF5E6C72);

/// 빛이 지나가지 않는 동안에도 남는 바닥 선 — 없으면 고른 칸의 반대쪽
/// 모서리가 통째로 사라진다. 🔴 **안 고른 칸의 테보다 진하다.**
const Color _kSweepBaseOnPaper = Color(0x8C9AA7AD);
