import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/core/network/upload_file.dart';
import 'package:super_sub/features/card/data/card_providers.dart';
import 'package:super_sub/features/card/data/card_repository.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/card/data/pick_photo.dart';
import 'package:super_sub/features/card/presentation/card_editor_screen.dart';

/// 1×1 투명 PNG — 🔴 **진짜 파일이 있어야 한다.** 미리보기가 `FileImage` 라
/// 없는 경로를 주면 그림 디코딩이 실패하면서 시험이 깨진다(화면 잘못이 아니다).
late final File _tempPhoto;

const _onePixelPng =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk'
    'YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';

/// 고른 척하는 대역. 실제 앨범을 안 연다.
class _FakePicker implements PhotoPicker {
  _FakePicker({this.contentType = 'image/png'});

  final String contentType;

  @override
  Future<PickedPhoto?> fromGallery() async => _made();

  @override
  Future<PickedPhoto?> fromCamera() async => _made();

  PickedPhoto _made() => PickedPhoto(
        path: _tempPhoto.path,
        file: UploadFile(
          name: '얼굴.png',
          contentType: contentType,
          sizeBytes: 4,
          openRead: () => Stream.value(const [1, 2, 3, 4]),
        ),
      );
}

/// 저장으로 **무엇이 갔는지**를 기록하는 대역.
class _SpyRepo implements CardRepository {
  String? tagline;
  bool? cleared;
  CardStyle? style;
  var saves = 0;

  @override
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
  }) async {
    saves += 1;
    this.tagline = tagline;
    cleared = clearTagline;
    this.style = style;
    return const PlayerCard(publicSlug: 'mine', nickname: '나');
  }

  @override
  Future<PlayerCard?> myCard() async => null;
  @override
  Future<PlayerCard> createMyCard() => throw UnimplementedError();
  @override
  Future<PlayerCard?> cardBySlug(String slug) async => null;

  /// 올린 사진 — **몇 번 올렸는지와 무엇으로 올렸는지**를 기록한다.
  var photoUploads = 0;
  UploadFile? uploadedPhoto;

  /// 다음 올리기를 실패시킨다 — 🔴 실패했을 때 **옛 키로 저장되지 않는지**를
  /// 재려면 실패를 만들 수 있어야 한다.
  bool failPhoto = false;

  @override
  Future<String> uploadCardPhoto(UploadFile file) async {
    photoUploads += 1;
    uploadedPhoto = file;
    if (failPhoto) throw const ApiException('올리지 못했습니다');
    return 'cards/photos/u-1/pc-1-abcd';
  }
}

Future<_SpyRepo> _pump(
  WidgetTester tester, {
  PlayerCard? card,
  PhotoPicker? picker,
}) async {
  final repo = _SpyRepo();
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        cardRepositoryProvider.overrideWithValue(repo),
        // 🔴 화면이 `PhotoPicker()` 를 직접 만들면 이 흐름을 못 몬다.
        if (picker != null) photoPickerProvider.overrideWithValue(picker),
      ],
      child: MaterialApp(
        home: CardEditorScreen(
          card: card ??
              const PlayerCard(
                publicSlug: 'mine',
                nickname: '나',
                tagline: 'THREE LUNGS',
              ),
        ),
      ),
    ),
  );
  await tester.pump();
  return repo;
}

void main() {
  setUpAll(() {
    _tempPhoto = File(
      '${Directory.systemTemp.createTempSync('ss-card-photo').path}/p.png',
    )..writeAsBytesSync(base64Decode(_onePixelPng));
  });

  testWidgets('탭 넷이 선다', (tester) async {
    await _pump(tester);

    for (final k in const ['colors', 'photo', 'text', 'mark']) {
      expect(find.byKey(Key('card-editor-tab-$k')), findsOneWidget, reason: k);
    }
  });

  testWidgets('지금 글자가 칸에 들어와 있다', (tester) async {
    await _pump(tester);
    await tester.tap(find.byKey(const Key('card-editor-tab-text')));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key('card-editor-tagline')),
    );
    expect(field.controller!.text, 'THREE LUNGS');
  });

  /// 🔴 20자까지다 — 넘기면 서버가 422 다. 화면에서 먼저 막는다.
  testWidgets('한 줄은 20자까지만 쳐진다', (tester) async {
    await _pump(tester);
    await tester.tap(find.byKey(const Key('card-editor-tab-text')));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key('card-editor-tagline')),
    );
    expect(field.maxLength, 20);
  });

  testWidgets('저장하면 글자와 꾸미기가 함께 간다', (tester) async {
    final repo = await _pump(tester);

    await tester.tap(find.byKey(const Key('card-editor-save')));
    await tester.pump();

    expect(repo.saves, 1);
    expect(repo.tagline, 'THREE LUNGS');
    expect(repo.style, isNotNull);
  });

  /// 🔴 비우면 「안 정함」이 아니라 **「일부러 지웠다」**다 — 그 둘을
  /// `clearTagline` 이 가른다(서버는 null 과 공백을 똑같이 다룬다).
  testWidgets('글자를 비우면 지운다고 보낸다', (tester) async {
    final repo = await _pump(tester);
    await tester.tap(find.byKey(const Key('card-editor-tab-text')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('card-editor-tagline')), '');
    await tester.tap(find.byKey(const Key('card-editor-save')));
    await tester.pump();

    expect(repo.cleared, isTrue);
    expect(repo.tagline, isNull);
  });

  group('자국 고르기', () {
    /// 🔴 배열에서 빼면 뒤 번호가 당겨져 **그 자국을 쓰던 카드가 말없이 다른
    /// 그림**이 된다 — 자리를 남기고 고르는 칸에서만 숨긴다.
    test('숨긴 자국(7·8)은 고르는 칸에 없지만 번호는 남아 있다', () {
      expect(kPickableMarks, isNot(contains(7)));
      expect(kPickableMarks, isNot(contains(8)));
      // 그 뒤 번호가 당겨지지 않았다.
      expect(kPickableMarks, contains(9));
      expect(kPickableMarks.last, 18);
    });

    test('기본(0)과 없음(1)도 고를 수 있다', () {
      expect(kPickableMarks.take(2), [0, 1]);
    });

    testWidgets('자국을 고르면 저장에 그 번호가 실린다', (tester) async {
      final repo = await _pump(tester);
      await tester.tap(find.byKey(const Key('card-editor-tab-mark')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('card-editor-mark-12')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('card-editor-save')));
      await tester.pump();

      expect(repo.style!.brush, 12);
    });

    /// 🔴 「없음」을 골랐으면 조정할 것이 없다 — 웹도 이때 칸을 감춘다.
    testWidgets('없음을 고르면 색·크기 칸이 사라진다', (tester) async {
      await _pump(tester);
      await tester.tap(find.byKey(const Key('card-editor-tab-mark')));
      await tester.pumpAndSettle();

      expect(find.text('자국 색'), findsOneWidget);

      await tester.tap(find.byKey(const Key('card-editor-mark-1')));
      await tester.pumpAndSettle();

      expect(find.text('자국 색'), findsNothing);
    });
  });

  group('사진', () {
    /// 🔴 **고르면 미리보기부터 뜨고 키는 비운다.** 옛 사진의 키가 남아
    /// 있으면 올리기가 실패했을 때 **새 그림 + 옛 키**로 저장돼, 내가 보는
    /// 카드와 남이 보는 카드가 갈린다.
    testWidgets('고르면 올라가고 키가 저장에 실린다', (tester) async {
      final repo = await _pump(tester, picker: _FakePicker());
      await tester.tap(find.byKey(const Key('card-editor-tab-photo')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('card-editor-photo-pick')));
      await tester.pumpAndSettle();

      expect(repo.photoUploads, 1);

      await tester.tap(find.byKey(const Key('card-editor-save')));
      await tester.pump();

      expect(repo.style!.photoKey, equals('cards/photos/u-1/pc-1-abcd'));
    });

    /// 🔴 **폰 앨범은 HEIC 도 내준다** — 서버는 셋만 받으므로 고른 즉시
    /// 막는다. 안 막으면 올라가다 422 로 죽고, 사람은 한참 뒤에 거절을 본다.
    testWidgets('받지 않는 형식은 올리지도 않는다', (tester) async {
      final repo = await _pump(
        tester,
        picker: _FakePicker(contentType: 'image/heic'),
      );
      await tester.tap(find.byKey(const Key('card-editor-tab-photo')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('card-editor-photo-pick')));
      await tester.pumpAndSettle();

      expect(repo.photoUploads, 0);
      expect(find.byKey(const Key('card-editor-photo-note')), findsOneWidget);
    });

    /// 🔴 **올리기가 실패하면 옛 키로 저장되면 안 된다** — 그러면 새 그림을
    /// 골랐는데 남에게는 옛 사진이 계속 보인다.
    testWidgets('올리기가 실패하면 옛 키가 안 실린다', (tester) async {
      final repo = await _pump(
        tester,
        picker: _FakePicker(),
        card: PlayerCard(
          publicSlug: 'mine',
          nickname: '나',
          style: CardStyle.fromJson(const {'photo_key': 'old-key'}),
        ),
      )
        ..failPhoto = true;
      await tester.tap(find.byKey(const Key('card-editor-tab-photo')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('card-editor-photo-pick')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('card-editor-save')));
      await tester.pump();

      expect(repo.style!.photoKey, isNull);
    });

    /// 🔴 **말 안 해 주면 「저장했는데 사라졌다」가 된다.**
    testWidgets('아직 안 올라간 상태를 말해 준다', (tester) async {
      // 올리기를 실패시켜 「키가 없는 채로 그림만 있는」 상태를 만든다.
      (await _pump(tester, picker: _FakePicker())).failPhoto = true;
      await tester.tap(find.byKey(const Key('card-editor-tab-photo')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('card-editor-photo-pending')), findsNothing);

      await tester.tap(find.byKey(const Key('card-editor-photo-pick')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('card-editor-photo-pending')), findsOneWidget);
    });
  });
}
