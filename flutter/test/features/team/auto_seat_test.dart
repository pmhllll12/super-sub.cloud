import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/auto_seat.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/seats_from_squad.dart';

SquadMember _m({
  String id = '1',
  String? slug = 's1',
  String nickname = '남',
  String pos = 'MF',
  int? col,
  int? row,
}) =>
    SquadMember(
      id: id,
      playerCardId: 'card-$id',
      cardPublicSlug: slug,
      nickname: nickname,
      positionCode: pos,
      positionLabel: pos,
      gridCol: col,
      gridRow: row,
      accepted: true,
    );

Squad _squad(List<SquadMember> members) => Squad(
      id: 's',
      teamId: 't',
      publicSlug: 'p',
      formation: '5:5',
      members: members,
    );

AutoSeatChoice? _pick(Squad? squad, {String? slug = 'mine'}) => pickAutoSeat(
      squad: squad,
      myCardSlug: slug,
      size: SquadSize.five,
    );

void main() {
  /// 🔴 이 회차의 핵심 — 웹은 「팀을 만든 사람은 뛴다고 보고 FW 에 먼저
  /// 앉힌다」(2026-09-17 사용자 판단). 이게 없으면 앱에서 내 카드가 판에 설
  /// 방법이 아예 없다.
  test('판이 비어 있으면 FW 에 앉힌다', () {
    final choice = _pick(_squad(const []));

    expect(choice, isNotNull);
    // 5:5 의 fw1 은 (1, 0) 이다.
    expect(choice!.col, 1);
    expect(choice.row, 0);
    expect(choice.positionCode, 'FW');
  });

  /// 🔴 「무조건 뛴다」가 전제라 남이 앉아 있어도 나는 판에 선다 — 다만
  /// **남을 밀어내지는 않는다.**
  test('FW 가 차 있으면 다른 빈 자리에 앉힌다', () {
    final choice = _pick(_squad([_m(pos: 'FW', col: 1, row: 0)]));

    expect(choice, isNotNull);
    expect(choice!.row, isNot(0));
  });

  test('빈 자리가 하나도 없으면 앉히지 않는다', () {
    final full = _squad([
      _m(id: '1', slug: 's1', pos: 'FW', col: 1, row: 0),
      _m(id: '2', slug: 's2', pos: 'MF', col: 0, row: 1),
      _m(id: '3', slug: 's3', pos: 'MF', col: 2, row: 1),
      _m(id: '4', slug: 's4', pos: 'DF', col: 1, row: 2),
      _m(id: '5', slug: 's5', pos: 'GK', col: 1, row: 3),
    ]);

    expect(_pick(full), isNull);
  });

  test('이미 판에 서 있으면 앉히지 않는다', () {
    final choice = _pick(_squad([
      _m(slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2),
    ]));

    expect(choice, isNull);
  });

  /// 🔴 칸 없는 내 등재도 배치 함수가 자리에 앉히므로 「이미 서 있다」로 본다 —
  /// 여기서 또 앉히면 같은 등재가 서버로 두 번 나간다.
  test('칸 없는 내 등재가 있으면 앉히지 않는다', () {
    final choice = _pick(_squad([_m(slug: 'mine', nickname: '나', pos: 'FW')]));

    expect(choice, isNull);
  });

  test('카드가 없으면 앉히지 않는다', () {
    expect(_pick(_squad(const []), slug: null), isNull);
  });

  test('스쿼드가 없으면 앉히지 않는다', () {
    // 판을 아직 안 만든 팀이다 — 만드는 것이 먼저다.
    expect(_pick(null), isNull);
  });

  test('앉힐 자리의 포지션은 그 행이 뜻하는 것이다', () {
    // FW 를 막고 나면 MF 줄이 다음이다.
    final choice = _pick(_squad([_m(pos: 'FW', col: 1, row: 0)]));

    expect(choice!.positionCode, const ['FW', 'MF', 'DF', 'GK'][choice.row]);
  });
}
