import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/models/skeleton.dart';

/* 관절 시계열(계약 3-14절). 🔴 **계약이 「하지 말 것」으로 못 박은 넷**을
   여기서 지킨다 — 어기면 **아무 데서도 안 터지고 그림만 틀어진다.** */

Map<String, dynamic> _json({List<dynamic>? joints}) => {
  'known': true,
  'fps': 15.0,
  'frames': 3,
  'frame_size': [1920, 1080],
  'swing_leg': 'right',
  'direction': 1,
  'keypoint_names': ['nose', 'left_shoulder', 'right_shoulder'],
  'moments': {'before': 41, 'impact': 46, 'after': 61},
  'moments_seconds': {'before': 2.733, 'impact': 3.067, 'after': 4.067},
  'after_clipped': false,
  'joints': joints ??
      [
        [
          [0.48, 0.39, 0.94],
          [0.40, 0.50, 0.90],
          [0.56, 0.50, 0.88],
        ],
        null,
        [
          [0.49, 0.38, 0.91],
          [0.41, 0.49, 0.87],
          [0.57, 0.49, 0.85],
        ],
      ],
};

void main() {
  /* 🔴 **못 잡은 프레임은 배열에서 안 빠지고 `null` 로 자리를 지킨다.**
     인덱스가 곧 프레임 번호라, 압축하면 **세 순간이 엉뚱한 자세**를 가리킨다 —
     그런데 스켈레톤은 어느 쪽이든 그럴듯해 보여 **눈으로도 안 잡힌다.** */
  test('못 잡은 프레임은 null 로 자리를 지킨다', () {
    final s = Skeleton.fromJson(_json());
    expect(s.joints.length, 3, reason: '빼고 압축하면 안 된다');
    expect(s.joints[1], isNull);
    expect(s.joints[2], isNotNull);
  });

  /* 🔴 **0~1 을 벗어나도 자르지 않는다** — 화면 밖으로 나간 관절이 실제로
     있고, 자르면 **발이 가장자리에 붙은 것처럼** 그려진다. */
  test('화면 밖 좌표를 자르지 않는다', () {
    final s = Skeleton.fromJson(_json(joints: [
      [
        [-0.12, 1.08, 0.80],
        [0.40, 0.50, 0.90],
        [0.56, 0.50, 0.88],
      ],
    ]));
    expect(s.joints[0]![0][0], -0.12);
    expect(s.joints[0]![0][1], 1.08);
  });

  /* 🔴 **인덱스의 뜻은 `keypoint_names` 가 정한다** — 자기 상수표를 따로 들면
     두 표가 갈려도 안 터지고 그림만 틀어진다. */
  test('관절 이름으로 자리를 찾는다', () {
    final s = Skeleton.fromJson(_json());
    expect(s.indexOf('left_shoulder'), 1);
    expect(s.indexOf('없는관절'), -1);
  });

  /* 🔴 **옛 리포트는 404 가 아니라 `200` 으로 `{known:false}`** 가 온다 —
     「관절이 없다」와 「리포트가 없다」는 다른 상태다. 오류로 다루면 안 된다. */
  test('known:false 는 오류가 아니라 상태다', () {
    final s = Skeleton.fromJson({'known': false, 'why': '옛 스키마입니다'});
    expect(s.known, isFalse);
    expect(s.why, '옛 스키마입니다');
    expect(s.joints, isEmpty);
  });

  /* 🔴 **세 순간은 서버가 골라 준다** — 앱이 피크를 다시 찾을 필요가 없다
     (웹은 브라우저에서 다시 계산하고 있다). */
  test('세 순간을 프레임과 초로 함께 받는다', () {
    final s = Skeleton.fromJson(_json());
    expect(s.moments['impact'], 46);
    expect(s.momentsSeconds['impact'], closeTo(3.067, 0.001));
    expect(s.swingLeg, 'right');
    expect(s.direction, 1);
  });

  group('재생 위치 → 프레임', () {
    test('fps 로 환산해 그 프레임을 준다', () {
      final s = Skeleton.fromJson(_json());
      // 15fps 에서 0.14초는 2번째 프레임(인덱스 2)이다.
      expect(s.at(const Duration(milliseconds: 140)), isNotNull);
      // 인덱스 1 은 못 잡은 프레임이라 null 이다.
      expect(s.at(const Duration(milliseconds: 70)), isNull);
    });

    test('범위를 벗어나면 null 이다', () {
      final s = Skeleton.fromJson(_json());
      expect(s.at(const Duration(seconds: 10)), isNull);
    });

    /* ⚠️ `fps` 가 0 이면 환산할 수가 없다 — 지어내지 않고 안 그린다. */
    test('fps 가 없으면 안 그린다', () {
      final s = Skeleton.fromJson({..._json(), 'fps': 0});
      expect(s.at(const Duration(milliseconds: 140)), isNull);
    });
  });
}
