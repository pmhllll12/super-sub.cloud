import 'package:flutter/material.dart';

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
  });

  final List<MyVideo> videos;
  final int current;
  final ValueChanged<int> onPick;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: videos.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final on = i == current;
          final state = videoState(videos[i]);
          return Semantics(
            selected: on,
            button: true,
            label: '${i + 1}번째 영상 · ${state.label}',
            child: Material(
              color: on ? _kSeed.withValues(alpha: 0.18) : Colors.white10,
              borderRadius: BorderRadius.circular(10),
              child: InkWell(
                key: Key('strip-$i'),
                borderRadius: BorderRadius.circular(10),
                onTap: () => onPick(i),
                child: Container(
                  width: 64,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: on ? _kSeed : Colors.white24,
                      width: on ? 1.5 : 1,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '${i + 1}',
                        style: TextStyle(
                          color: on ? _kSeed : Colors.white70,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          height: 1.1,
                        ),
                      ),
                      /* 🔴 **상태를 글자로 적는다.** 섬네일이 없으니 칸끼리
                         구별할 것이 번호밖에 없는데, 반려된 클립을 모르고
                         고르면 왜 단추가 없는지 알 데가 없다. */
                      Text(
                        state.label,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.55),
                          fontSize: 9,
                          height: 1.2,
                        ),
                      ),
                    ],
                  ),
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
