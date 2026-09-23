import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/card_providers.dart';
import '../data/models/player_card.dart';

/// 팀원 카드 — **보이는 것만, 한 번만** 받는다. 키는 카드 공개 슬러그다.
///
/// 🔴 **목록을 그릴 때 줄마다 부르지 않는다.** 자리마다 카드를 부르면 판 하나를
/// 여는 데 요청이 자리 수만큼 나가고, 판을 다시 그릴 때마다 또 나간다
/// (웹 `SquadPanel` 이 같은 규칙을 쓴다).
///
/// 🔴 **한 장이 실패해도 판 전체를 오류로 만들지 않는다** — 그 자리만 이름표로
/// 남는다. 팀원 하나의 카드가 없다고 판이 안 그려지면 나머지 자리까지 못 본다.
class MateCardsController extends Notifier<Map<String, PlayerCard>> {
  /// 지금 받는 중인 슬러그 — 같은 것을 두 번 부르지 않게 한다.
  final _inFlight = <String>{};

  @override
  Map<String, PlayerCard> build() => const {};

  /// 이 슬러그들의 카드가 필요하다. 이미 있거나 받는 중이면 아무 일도 안 한다.
  void want(Iterable<String> slugs) {
    final repo = ref.read(cardRepositoryProvider);
    for (final slug in slugs.toSet()) {
      if (slug.isEmpty || state.containsKey(slug) || _inFlight.contains(slug)) {
        continue;
      }
      _inFlight.add(slug);
      repo.cardBySlug(slug).then((card) {
        _inFlight.remove(slug);
        /* 🔴 **응답이 카드 모양이 아니면 버린다.** 없는 값이 카드 자리에
           들어가면 카드를 그리다 통째로 깨진다 — 웹도 같은 검사를 한다
           (`public_slug` 가 문자열인지까지 본다). */
        if (card == null || card.publicSlug.isEmpty) return;
        state = {...state, slug: card};
      }).catchError((Object _) {
        // 한 장이 안 와도 그 자리만 이름표다.
        _inFlight.remove(slug);
      });
    }
  }
}

final mateCardsProvider =
    NotifierProvider<MateCardsController, Map<String, PlayerCard>>(
  MateCardsController.new,
);
