/// 앱에 **들고 다니는 본보기**(영상·관절)가 실제로 읽히는가.
///
/// 🔴 **어긋나도 아무 데서도 안 터진다** — 파일 이름이 틀리면 빌드는 되고
/// **재생만 안 되거나 관절만 안 붙는다.** 그래서 여기서 못 박는다.
///
/// 🔴 **관절을 들고 다니는 까닭**: 같은 값을 서버에 물으면 0.67~11.5초로
/// 들쭉날쭉하다(2026-09-25 여덟 번 실측 — 계약이 「요청마다 S3 에서 읽는다」고
/// 정해 두어서다). 선수 관절은 절대 안 바뀌는 값이라 기기에 둔다.
library;

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/models/reference_player.dart';
import 'package:super_sub/features/video/data/models/skeleton.dart';
import 'package:super_sub/features/video/domain/motion/motion.dart';

void main() {
  /// 서버가 실제로 내주는 둘 — `GET /reference-players` 의 `id` 와 같아야 한다.
  const ids = ['rovelli', 'castanheira'];

  for (final id in ids) {
    group(id, () {
      final player = ReferencePlayer(id: id, name: '아무개');

      test('영상과 관절을 둘 다 들고 다닌다', () {
        // 🔴 **짝이다** — 하나만 있으면 영상은 도는데 관절이 안 붙는다.
        expect(player.clipAsset, isNotNull);
        expect(player.skeletonAsset, isNotNull);
      });

      test('들고 다니는 관절이 계약 모양으로 읽힌다', () async {
        final raw = await rootBundle.loadString(player.skeletonAsset!);
        final skeleton = Skeleton.fromJson(
          jsonDecode(raw) as Map<String, dynamic>,
        );

        expect(skeleton.known, isTrue);
        expect(skeleton.fps, greaterThan(0));
        expect(skeleton.joints, isNotEmpty);
        expect(skeleton.keypointNames, contains('left_hip'));
        // 🔴 세 순간이 있어야 비교가 선다 — 없으면 `motionOf` 가 `null` 이다.
        expect(skeleton.moments.keys, containsAll(['before', 'impact', 'after']));
      });

      /// 🔴 **비교가 실제로 서는지**까지 본다 — 읽히는 것과 쓸 수 있는 것은 다르다.
      /// 차는 다리나 세 순간이 빠지면 여기서 걸린다.
      test('그 관절로 비교를 세울 수 있다', () async {
        final raw = await rootBundle.loadString(player.skeletonAsset!);
        final m = motionOf(
          Skeleton.fromJson(jsonDecode(raw) as Map<String, dynamic>),
        );

        expect(m, isNotNull);
        expect(m!.motion.at(m.moments.impact), isNotNull);
      });

      test('영상 에셋이 실제로 들어 있다', () async {
        final bytes = await rootBundle.load(player.clipAsset!);
        expect(bytes.lengthInBytes, greaterThan(100000));
      });
    });
  }

  /// 🔴 **서버가 새 선수를 내줘도 앱이 죽지 않는다** — 그때는 영상 칸을 비우고
  /// 관절은 서버에 묻는다(에셋을 억지로 열면 그 자리에서 터진다).
  test('안 들고 다니는 선수는 둘 다 null 이다', () {
    const stranger = ReferencePlayer(id: 'who-is-this', name: '새 선수');
    expect(stranger.clipAsset, isNull);
    expect(stranger.skeletonAsset, isNull);
  });
}
