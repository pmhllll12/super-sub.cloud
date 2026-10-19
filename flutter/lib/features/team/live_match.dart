import 'data/models/match_candidate.dart';

/// 이 신청이 **지금 살아 있는 확정 경기**인가.
///
/// 🔴 **이 판단을 두 곳에서 따로 하면 안 된다** — 웹이 세 번 신고받은
/// 자리다(`www/src/lib/useNotifyInbox.ts` 의 `isLiveConfirmed` 머리말).
/// 머리칸의 「경기 잡힘」과 대기 화면을 띄우는 쪽이 **서로 다른 조건**을
/// 쓰는 바람에, 「경기 완료」를 눌러도 같은 갱신이 판을 곧바로 되살렸다.
/// 그래서 앱에서는 **이 함수 하나**만 쓴다.
///
/// 조건 넷:
/// - `accepted` 이고
/// - 🔴 **`matchId` 가 차 있고** — 취소는 `match` 행만 지우고 `status` 는
///   `accepted` 로 남는다(외래키가 `match_id` 만 비운다). `status` 만 보면
///   취소된 경기를 계속 켠다. 서버의 겹치기 방지도 같은 것을 본다(계약 3-15절)
/// - 경기 시각이 **아직 안 지났고**
/// - 🔴 **끝냈다고 적어 두지 않았다** — 서버에 「완료」 상태가 없어서 기기에
///   적어 둔 것을 본다. 없으면 「경기 완료」를 눌러도 곧바로 되살아난다
bool isLiveConfirmed(
  TeamMatchRequest r, {
  required DateTime now,
  Set<String> done = const {},
}) {
  if (!r.isAccepted) return false;
  final matchId = r.matchId;
  if (matchId == null) return false;
  if (done.contains(matchId)) return false;

  /* 🔴 **못 읽는 시각은 살아 있다고 보지 않는다** — 모르는 값으로 대기
     화면을 띄우면 무엇을 기다리는지도 못 적는다. */
  final at = DateTime.tryParse(r.playedAt);
  if (at == null) return false;
  return !at.isBefore(now);
}

/// 살아 있는 확정 경기 하나. 없으면 `null`.
///
/// 🔴 **하나만 고른다** — 계약이 수락되는 순간 두 팀의 다른 `pending` 을 전부
/// 정리하므로(3-15절 「동시 확정 방지」) 살아 있는 것은 하나뿐이다.
TeamMatchRequest? firstLiveMatch(
  List<TeamMatchRequest> all, {
  required DateTime now,
  Set<String> done = const {},
}) {
  for (final r in all) {
    if (isLiveConfirmed(r, now: now, done: done)) return r;
  }
  return null;
}
