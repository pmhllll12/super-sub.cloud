/// **경기 조건** — 「어느 동네에서 · 언제 · (팀원이면) 내 자리」.
/// 웹 `www/src/lib/matchPrefs.ts` 를 옮긴 것이다.
///
/// 🔴 **RAG 가 「비슷하다」를 판단할 근거가 이 값이다.** 이게 없으면 비교할
/// 것이 없어서, 명단의 「같은 지역」 알약은 손으로 적어 둔 글자에 지나지 않는다.
///
/// 🔴 **팀 조건과 내 조건을 따로 둔다.** 같은 사람이 팀장이면서 팀원일 수
/// 있다 — 한 벌로 두면 「우리 팀이 찾는 경기」와 「내가 뛸 수 있는 때」가 섞인다.
library;

/// 언제 뛸 수 있는가 — 한 줄.
class TimeSlot {
  const TimeSlot({required this.day, required this.from, required this.to});

  /// 🔴 **0 = 일요일 … 6 = 토요일.** `DateTime.weekday`(1=월 … 7=일)와도,
  /// 계약의 `weekday`(0=월)와도 **다르다** — 옮기는 자리는
  /// `match_prefs_server.dart` 한 곳뿐이다.
  final int day;

  /// `HH:MM` — 30분 단위.
  final String from;
  final String to;

  /// `토 09:00~11:00` — 화면에 한 줄로 적을 때.
  String get text => '${kDays[day]} $from~$to';

  /// 두 시간대가 **겹치는가.**
  ///
  /// 🔴 **끝이 닿기만 한 것은 안 겹친 것이다** — `09:00~11:00` 과
  /// `11:00~13:00` 은 함께 뛸 시간이 0분이다.
  bool overlaps(TimeSlot other) =>
      day == other.day &&
      from.compareTo(other.to) < 0 &&
      other.from.compareTo(to) < 0;

  @override
  bool operator ==(Object other) =>
      other is TimeSlot &&
      other.day == day &&
      other.from == from &&
      other.to == to;

  @override
  int get hashCode => Object.hash(day, from, to);
}

/// 정해 둔 경기 조건.
class MatchPrefs {
  const MatchPrefs({
    this.regions = const [],
    this.times = const [],
    this.positions = const [],
  });

  /// 고른 지역 **이름들**(`서울 강남구`). 계약으로 갈 때 id 로 바뀐다.
  final List<String> regions;
  final List<TimeSlot> times;

  /// 내가 뛸 자리 — **팀원 조건에만** 쓴다. 팀 조건에서는 늘 빈 목록이다.
  final List<String> positions;

  /// 🔴 **둘 다 채워야 찾을 수 있다** — 지역이나 시간 하나가 비면 「비슷한
  /// 팀」을 고를 근거가 없다.
  bool get isReady => regions.isNotEmpty && times.isNotEmpty;

  MatchPrefs copyWith({
    List<String>? regions,
    List<TimeSlot>? times,
    List<String>? positions,
  }) =>
      MatchPrefs(
        regions: regions ?? this.regions,
        times: times ?? this.times,
        positions: positions ?? this.positions,
      );
}

/// 어느 쪽 조건인가 — 화면도 저장 자리도 이 값으로 갈린다.
enum PrefsKind { team, me }

/// 요일 이름. 🔴 **0 이 일요일**이다(위 [TimeSlot.day] 주석).
const List<String> kDays = ['일', '월', '화', '수', '목', '금', '토'];

/// 고를 수 있는 시각 — **30분 단위, 06:00~24:00**.
///
/// 🔴 **24:00 을 끝에 둔다** — 밤 경기의 끝을 적을 자리가 없으면 23:30 까지
/// 밖에 못 적는다.
final List<String> kHours = () {
  final out = <String>[];
  for (var m = 6 * 60; m <= 24 * 60; m += 30) {
    final h = (m ~/ 60).toString().padLeft(2, '0');
    out.add('$h:${m % 60 == 0 ? '00' : '30'}');
  }
  return List<String>.unmodifiable(out);
}();
