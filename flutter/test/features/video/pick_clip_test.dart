import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/clip_file.dart';
import 'package:super_sub/features/video/data/pick_clip.dart';

void main() {
  group('contentTypeOf', () {
    test('mp4 와 mov 를 계약이 받는 형식으로 읽는다', () {
      expect(contentTypeOf('첫 골.mp4'), equals('video/mp4'));
      expect(contentTypeOf('첫 골.MP4'), equals('video/mp4'));
      expect(contentTypeOf('IMG_0042.mov'), equals('video/quicktime'));
      expect(contentTypeOf('IMG_0042.MOV'), equals('video/quicktime'));
    });

    /// 🔴 **모르는 확장자를 `video/mp4` 로 지어내지 않는다.** 지어내면
    /// `checkClip` 이 통과시키고 S3 서명까지 만들어진 뒤 **등록에서 422 로
    /// 죽는다** — 사람은 한참 올린 다음에야 거절을 본다.
    test('모르는 확장자를 mp4 로 지어내지 않는다', () {
      expect(contentTypeOf('경기.avi'), isNot(equals('video/mp4')));
      expect(contentTypeOf('경기.mkv'), isNot(equals('video/mp4')));
      expect(contentTypeOf('확장자없음'), isNot(equals('video/mp4')));
    });

    /// 위와 짝 — 지어내지 않은 결과가 **고른 즉시** 막히는지.
    test('모르는 확장자는 checkClip 이 그 자리에서 막는다', () {
      final bad = ClipFile(
        name: '경기.avi',
        contentType: contentTypeOf('경기.avi'),
        sizeBytes: 1024,
        openRead: () => const Stream<List<int>>.empty(),
      );

      expect(checkClip(bad), isNotNull);
      expect(checkClip(bad), contains('mp4'));
    });

    test('점이 여럿이어도 마지막 것을 본다', () {
      expect(contentTypeOf('2026.09.22 경기.mov'), equals('video/quicktime'));
    });
  });

  group('checkClip', () {
    ClipFile clip({required String type, required int size}) => ClipFile(
          name: 'x',
          contentType: type,
          sizeBytes: size,
          openRead: () => const Stream<List<int>>.empty(),
        );

    test('받는 형식과 용량이면 통과한다', () {
      expect(checkClip(clip(type: 'video/mp4', size: 1024)), isNull);
      expect(checkClip(clip(type: 'video/quicktime', size: 1024)), isNull);
    });

    test('상한을 딱 맞추면 통과하고 1바이트 넘으면 막는다', () {
      expect(checkClip(clip(type: 'video/mp4', size: kClipMaxBytes)), isNull);
      expect(
        checkClip(clip(type: 'video/mp4', size: kClipMaxBytes + 1)),
        isNotNull,
      );
    });

    /// 🔴 **길이·해상도는 여기서 막지 않는다** — 서버가 `reject_reason` 으로
    /// 남겨야 하는 것이고(SFR-001 이 규격 검사를 두는 이유), 화면이 미리
    /// 막으면 **그 사유가 사라진다.** `checkClip` 이 크기와 형식만 받는
    /// 것으로 그 선이 그어져 있다.
    test('형식과 용량 말고는 보지 않는다 — 길이·해상도는 서버 몫이다', () {
      // 두 시간짜리 8K 라도 형식·용량이 맞으면 여기서는 통과한다.
      expect(checkClip(clip(type: 'video/mp4', size: 1024)), isNull);
    });
  });
}
