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
  const Proposal({
    required this.at,
    required this.label,
    required this.slot,
    this.isCustom = false,
  });

  /* 🔴 **조건 밖의 날짜를 직접 고른 것** (2026-09-29 사용자 지적: 「다음주일
     수도 있고 다음달일 수도 있는거잖아」).

     조건은 **매주 반복되는 가용 시간**이라 [proposalsFrom] 이 만드는 것은
     「다음에 오는 그 요일」 **딱 한 번**이다. 그래서 2주 뒤·다음 달로는
     아예 신청할 길이 없었다 — 서버는 `played_at` 을 아무 날짜나 받는데
     화면이 못 만들고 있었다.

     🔴 **끝 시각을 지어내지 않는다.** 추천 쪽은 조건에 적힌 `to` 가 있지만
     직접 고른 것은 시작만 고른 것이다. 계약(`POST …/match-requests`)도
     **`played_at` 하나만** 받으므로 끝은 어차피 안 나간다 — 없는 값을
     「~16:00」처럼 적으면 상대가 약속으로 읽는다.

     ⚠️ **웹에는 없다**(`www/src/lib/matchProposal.ts`). 해커톤에 공개
     도메인으로 내놓은 상태라 손대지 않기로 했다(2026-09-29 사용자 지시).
     🔴 **웹을 다시 만질 때 같이 옮긴다** — 두 화면이 갈린 채로 남아 있다. */
  factory Proposal.custom(DateTime at) {
    final day = _screenDayOf(at);
    final from = '${_p2(at.hour)}:${_p2(at.minute)}';
    return Proposal(
      at: at,
      // 🔴 추천과 **모양이 다르다** — 끝 시각이 없는 것이 눈에 보여야 한다.
      label: '${kDays[day]} ${_p2(at.month)}/${_p2(at.day)} $from',
      /* 목록에서 견주기 위한 자리일 뿐이다. `to` 는 안 쓰이지만 [TimeSlot] 이
         요구해서 시작과 같은 값을 둔다 — **길이 0 이라 어디와도 안 겹친다**는
         뜻이 되어, 실수로 겹침 계산에 들어가도 조용히 참이 되지 않는다. */
      slot: TimeSlot(day: day, from: from, to: from),
      isCustom: true,
    );
  }

  final DateTime at;

  /// `토 09/26 11:00~13:00` — 고르는 자리에 그대로 적는다.
  final String label;
  final TimeSlot slot;

  /// 조건에서 나온 것이 아니라 **사람이 달력에서 고른 것**인가.
  final bool isCustom;

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

/// 추천 목록에 **직접 고른 것**을 끼워 넣는다 — 이른 것부터.
///
/// 🔴 **고른 값이 목록 안에 있어야 한다.** `DropdownButton` 은 `value` 와
/// **같은** 항목이 `items` 에 없으면 아무것도 안 그린다(2026-09-25에 이미
/// 데인 자리다 — 그때는 값 동등성이 없어서였다). 직접 고른 것을 목록에
/// 안 넣으면 **고르자마자 칸이 비어 보인다.**
///
/// 🔴 **같은 시각이면 추천 쪽을 남긴다** — 조건에서 나온 것이라 끝 시각까지
/// 있어 더 많은 것을 말해 준다. 둘 다 두면 같은 시각이 두 줄로 보인다.
List<Proposal> withCustom(List<Proposal> base, Proposal? custom) {
  if (custom == null) return base;
  if (base.any((p) => p.at == custom.at)) return base;
  return [...base, custom]..sort((a, b) => a.at.compareTo(b.at));
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
