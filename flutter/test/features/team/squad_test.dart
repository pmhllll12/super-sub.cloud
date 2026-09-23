import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/squad.dart';

Map<String, dynamic> _member({
  Object? col = 1,
  Object? row = 3,
  Map<String, dynamic> extra = const {},
}) =>
    {
      'id': '1d4f',
      'player_card_id': '9a2e',
      'card_public_slug': 'hong-gildong-4f2a',
      'nickname': '홍길동',
      'position_code': 'GK',
      'position_label': '골키퍼',
      'grid_col': col,
      'grid_row': row,
      ...extra,
    };

Squad _squad({
  Object? formation = '5:5',
  List<Map<String, dynamic>> members = const [],
}) =>
    Squad.fromJson({
      'id': '7c05',
      'team_id': '3f1c',
      'public_slug': 'aB3xK9mQ2pL7vN4t',
      'formation': formation,
      'members': members,
    });

void main() {
  test('계약 응답을 읽는다', () {
    final squad = _squad(members: [_member()]);

    expect(squad.id, '7c05');
    expect(squad.teamId, '3f1c');
    expect(squad.publicSlug, 'aB3xK9mQ2pL7vN4t');
    expect(squad.formation, '5:5');

    final m = squad.members.single;
    expect(m.positionCode, 'GK');
    expect(m.positionLabel, '골키퍼');
    expect(m.cardPublicSlug, 'hong-gildong-4f2a');
    expect(m.gridCol, 1);
    expect(m.gridRow, 3);
    expect(m.hasSeat, isTrue);
  });

  test('판에 안 올린 등재는 칸이 null 이다', () {
    final m = _squad(members: [_member(col: null, row: null)]).members.single;

    expect(m.gridCol, isNull);
    expect(m.hasSeat, isFalse);
  });

  test('카드 슬러그가 null 도 정상이다 — 「아직 판이 없습니다」', () {
    final m = _squad(
      members: [
        _member(extra: const {'card_public_slug': null}),
      ],
    ).members.single;

    expect(m.cardPublicSlug, isNull);
  });

  test('⚠️ formation 이 null 일 수 있다 — 2026-09-18 이전 스쿼드', () {
    expect(_squad(formation: null).formation, isNull);
  });

  test('members 가 없어도 빈 목록이다', () {
    expect(_squad().members, isEmpty);
  });

  group('accepted_at — 계약 문서에 없는 값', () {
    test('🔴 아예 안 오면 「수락됨」으로 본다', () {
      // 옛 응답에는 이 칸이 없었고, 그때는 팀원만 앉을 수 있어 앉은 것이 곧
      // 온 것이었다.
      expect(_squad(members: [_member()]).members.single.accepted, isTrue);
    });

    test('null 로 와 있으면 대기중이다', () {
      final m = _squad(
        members: [
          _member(extra: const {'accepted_at': null}),
        ],
      ).members.single;

      expect(m.accepted, isFalse);
    });

    test('시각이 차 있으면 수락됐다', () {
      final m = _squad(
        members: [
          _member(extra: const {'accepted_at': '2026-09-17T05:00:00Z'}),
        ],
      ).members.single;

      expect(m.accepted, isTrue);
    });
  });
}
