import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/network/upload_file.dart';
import 'package:super_sub/features/card/data/card_providers.dart';
import 'package:super_sub/features/card/data/card_repository.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/card/presentation/mate_cards_controller.dart';

/// 부른 횟수를 세고, 슬러그마다 무엇을 돌려줄지 정해 주는 대역.
class _SpyCardRepository implements CardRepository {
  _SpyCardRepository({this.broken = const {}, this.failing = const {}});

  /// 카드 모양이 아닌 것(빈 슬러그)을 돌려줄 슬러그들.
  final Set<String> broken;

  /// 예외를 던질 슬러그들.
  final Set<String> failing;

  final calls = <String>[];

  @override
  Future<PlayerCard?> cardBySlug(String slug) async {
    calls.add(slug);
    if (failing.contains(slug)) throw Exception('끊김');
    if (broken.contains(slug)) {
      return const PlayerCard(publicSlug: '', nickname: '');
    }
    return PlayerCard(publicSlug: slug, nickname: '아무개');
  }

  @override
  Future<PlayerCard> createMyCard() => throw UnimplementedError();

  @override
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
    List<String>? titles,
  }) =>
      throw UnimplementedError();

  @override
  Future<PlayerCard?> myCard() => throw UnimplementedError();

  // 이 대역은 팀원 카드를 받는 것만 잰다 — 사진 올리기는 안 쓴다.
  @override
  Future<String> uploadCardPhoto(UploadFile file) =>
      throw UnimplementedError();
}

({ProviderContainer container, _SpyCardRepository repo}) _setUp({
  Set<String> broken = const {},
  Set<String> failing = const {},
}) {
  final repo = _SpyCardRepository(broken: broken, failing: failing);
  final container = ProviderContainer(
    overrides: [cardRepositoryProvider.overrideWithValue(repo)],
  );
  addTearDown(container.dispose);
  return (container: container, repo: repo);
}

void main() {
  test('부른 슬러그의 카드를 담는다', () async {
    final s = _setUp();

    s.container.read(mateCardsProvider.notifier).want(['s1', 's2']);
    await pumpEventQueue();

    expect(s.container.read(mateCardsProvider).keys, containsAll(['s1', 's2']));
  });

  /// 🔴 자리마다 카드를 부르면 판 하나를 여는 데 요청이 자리 수만큼 나가고,
  /// 판을 다시 그릴 때마다 또 나간다.
  test('같은 슬러그를 두 번 받지 않는다', () async {
    final s = _setUp();
    final notifier = s.container.read(mateCardsProvider.notifier);

    notifier.want(['s1', 's1', 's2']);
    await pumpEventQueue();
    notifier.want(['s1', 's2']);
    await pumpEventQueue();

    expect(s.repo.calls, hasLength(2));
  });

  test('받는 중인 슬러그를 다시 부르지 않는다', () async {
    final s = _setUp();
    final notifier = s.container.read(mateCardsProvider.notifier);

    // await 없이 연달아 — 첫 요청이 아직 안 끝났다.
    notifier.want(['s1']);
    notifier.want(['s1']);
    await pumpEventQueue();

    expect(s.repo.calls, hasLength(1));
  });

  /// 🔴 없는 값이 카드 자리에 들어가면 카드를 그리다 통째로 깨진다.
  test('카드 모양이 아닌 응답은 버린다', () async {
    final s = _setUp(broken: {'broken'});

    s.container.read(mateCardsProvider.notifier).want(['broken']);
    await pumpEventQueue();

    expect(s.container.read(mateCardsProvider).containsKey('broken'), isFalse);
  });

  /// 🔴 팀원 하나의 카드가 없다고 판이 안 그려지면 나머지 자리까지 못 본다.
  test('한 장이 실패해도 나머지는 담긴다', () async {
    final s = _setUp(failing: {'bad'});

    s.container.read(mateCardsProvider.notifier).want(['bad', 'good']);
    await pumpEventQueue();

    expect(s.container.read(mateCardsProvider).containsKey('good'), isTrue);
    expect(s.container.read(mateCardsProvider).containsKey('bad'), isFalse);
  });

  test('실패한 슬러그는 다시 부를 수 있다', () async {
    final s = _setUp(failing: {'bad'});
    final notifier = s.container.read(mateCardsProvider.notifier);

    notifier.want(['bad']);
    await pumpEventQueue();
    notifier.want(['bad']);
    await pumpEventQueue();

    // 받는 중 표시가 풀려야 재시도가 된다.
    expect(s.repo.calls, hasLength(2));
  });

  test('빈 슬러그는 부르지 않는다', () async {
    final s = _setUp();

    s.container.read(mateCardsProvider.notifier).want(['']);
    await pumpEventQueue();

    expect(s.repo.calls, isEmpty);
  });
}
