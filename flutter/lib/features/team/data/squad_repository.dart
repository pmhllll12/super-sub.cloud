import 'models/squad.dart';

/// 화면이 아는 유일한 스쿼드 계약.
///
/// 🔴 **「안 만들었다」를 예외로 던지지 않는다** — 카드와 같은 판단이다
/// (`card_repository.dart`).
abstract class SquadRepository {
  /// 팀의 스쿼드. **아직 안 만들었으면 `null`** 이다.
  ///
  /// 🔴 빈 스쿼드를 돌려주면 「만들지 않은 것」과 「비어 있는 것」이 같아
  /// 보인다 — 계약이 404 `SQUAD_NOT_FOUND` 를 내는 이유가 그것이다.
  ///
  /// 읽기는 **소속이면 된다**(주장이 아니어도 된다). 팀 id 로 남의 팀 구성을
  /// 훑는 것을 막는 자리라, 소속이 아니면 404 가 아니라 403 이 온다.
  Future<Squad?> squadOf(String teamId);

  /// 카드를 판에 **앉힌다**(`POST /teams/{id}/squad/members`). 바뀐 스쿼드
  /// 전체가 돌아온다.
  ///
  /// 🔴 **주장만 된다** — 등재는 팀을 대표하는 행위다. 팀원이 부르면 403 이고,
  /// 그때 화면에만 앉혀 두면 **새로고침에 사라진다.**
  /// 🔴 **칸은 함께 주거나 함께 비운다** — 한쪽만 주면 서버가 422 다.
  Future<Squad> enlist(
    String teamId, {
    required String playerCardId,
    required String positionCode,
    int? gridCol,
    int? gridRow,
  });

  /// 등재 하나의 **포지션·칸**을 바꾼다
  /// (`PATCH /teams/{id}/squad/members/{memberId}`).
  ///
  /// 🔴 [positionCode] 는 **항상 보낸다** — 등재는 포지션 없이 존재하지 않는다.
  /// 칸만 옮길 때도 지금 코드를 그대로 싣는다(계약 3-7절).
  /// 🔴 칸을 둘 다 `null` 로 주면 등재는 남기고 **판에서만 뺀다.**
  Future<Squad> moveSeat(
    String teamId, {
    required String memberId,
    required String positionCode,
    int? gridCol,
    int? gridRow,
  });

  /// 등재를 **뺀다**(`DELETE /teams/{id}/squad/members/{memberId}`).
  /// 바뀐 스쿼드 전체가 돌아온다.
  ///
  /// 🔴 **카드는 안 지워진다** — 스쿼드에서 빠질 뿐이다.
  /// 🔴 **주장만 된다.**
  Future<Squad> removeSeat(String teamId, {required String memberId});

  /// 사람을 **팀에서 내보낸다**(`DELETE /teams/{id}/members/{userId}`).
  ///
  /// 🔴 **판에서 내리는 것만으로는 모자라다** — 그 사람이 여전히 팀원이라
  /// **AI 추천 후보에서 계속 빠진다**(추천은 그 팀 소속을 뺀다). 웹 운영에서
  /// 그렇게 12명이 쌓여 추천 목록이 말랐다(2026-09-18 사용자 결정).
  ///
  /// 🔴 **나를 내보내지 않는다** — 주장이 스스로 나가면 팀이 주인을 잃는다
  /// (서버도 409 `LAST_OWNER` 로 막는다).
  ///
  /// ⚠️ 서버는 행을 지우지 않고 `left_at` 을 채운다 — 되돌리려면 다시 부른다.
  Future<void> removeTeamMember(String teamId, {required String userId});
}
