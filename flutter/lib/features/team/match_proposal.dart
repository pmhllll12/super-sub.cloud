import 'match_prefs.dart';

/// **조건 슬롯 → 실제 경기 시각** (계약 3-15절이 요구하는 `played_at`).
/// 웹 `www/src/lib/matchProposal.ts` 를 옮긴 것이다.
///
/// 🔴 **왜 필요한가.** 「맞는 상대」 후보(`GET /teams/{id}/match-candidates`)는
/// **팀 후보이지 경기 공고가 아니라서 시각·구장이 없다.** 그런데 신청
/// (`POST /teams/{id}/match-requests`)은 `played_at`·`place` 를 **필수로**
/// 받는다. 🔴 **지어내지 않는다** — 시각은 **우리가 올린 경기 조건**에서
/// 만들고, 구장은 경기장 목록에서 고른다.
///
/// 🔴 **조건이 없으면 빈 목록이다.** 아무 시각이나 채워 넣으면 아무도 못 뛰는
/// 경기가 잡힌다.
class Proposal {
  const Proposal({required this.at, required this.label, required this.slot});

  final DateTime at;

  /// `토 09/26 11:00~13:00` — 고르는 자리에 그대로 적는다.
  final String label;
  final TimeSlot slot;

  /* 🔴 **값으로 견준다**(2026-09-25에 데였다). 이 목록은 **매 빌드마다 새로**
     만들어지는데, 고른 값을 객체로 들고 있으면 다음 빌드의 목록에는 같은
     것이 하나도 없다 — 고르는 칸이 **아무것도 안 그린다.** 오류도 안 난다. */
  @override
  bool operator ==(Object other) =>
      other is Proposal && other.at == at && other.slot == slot;

  @override
  int get hashCode => Object.hash(at, slot);
}

String _p2(int n) => n.toString().padLeft(2, '0');

/// 화면의 `day`(0=일) 로 본 그 날의 요일.
///
/// 🔴 `DateTime.weekday` 는 **1=월 … 7=일**이라 그대로 못 쓴다.
int _screenDayOf(DateTime d) => d.weekday % 7;

/// 그 조건이 **다음에 오는 날**의 그 시각.
///
/// 🔴 **같은 요일이라도 시각이 이미 지났으면 다음 주다.** 지난 시각으로
/// 신청하면 서버가 받아 줘도 아무도 못 뛴다.
DateTime nextOccurrence(TimeSlot slot, [DateTime? now]) {
  final base = now ?? DateTime.now();
  final parts = slot.from.split(':');
  var at = DateTime(
    base.year,
    base.month,
    base.day,
    int.parse(parts[0]),
    int.parse(parts[1]),
  );

  var ahead = (slot.day - _screenDayOf(at) + 7) % 7;
  // 오늘인데 시각이 지났으면 다음 주 같은 요일이다.
  if (ahead == 0 && !at.isAfter(base)) ahead = 7;
  return at.add(Duration(days: ahead));
}

/// 조건 전부를 **이른 것부터** 고를 수 있는 목록으로 펼친다.
///
/// 🔴 순서는 **실제 날짜 순**이다 — 조건에 적힌 순서가 아니다. 목요일에
/// 「일 09:00」과 「토 11:00」을 갖고 있으면 **토요일이 먼저 온다.**
List<Proposal> proposalsFrom(List<TimeSlot> slots, [DateTime? now]) {
  final out = [
    for (final slot in slots)
      () {
        final at = nextOccurrence(slot, now);
        return Proposal(
          at: at,
          slot: slot,
          label: '${kDays[slot.day]} ${_p2(at.month)}/${_p2(at.day)} '
              '${slot.from}~${slot.to}',
        );
      }(),
  ]..sort((a, b) => a.at.compareTo(b.at));
  return out;
}

/// 계약이 받는 모양으로 — **현지 시각의 오프셋을 붙인다.**
///
/// 🔴 **`toIso8601String()` 을 그대로 쓰지 않는다.** UTC 로 바꿔 버리면
/// 「토 11:00」이 「토 02:00」으로 저장된다 — 사람이 고른 것은 **그 지역
/// 시각의 11시**다.
String toPlayedAt(DateTime at) {
  final off = at.timeZoneOffset;
  final sign = off.isNegative ? '-' : '+';
  final mins = off.inMinutes.abs();
  return '${at.year}-${_p2(at.month)}-${_p2(at.day)}'
      'T${_p2(at.hour)}:${_p2(at.minute)}:00'
      '$sign${_p2(mins ~/ 60)}:${_p2(mins % 60)}';
}
