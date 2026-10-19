/// **화면 모양 ↔ 계약 모양** (계약 3-13절). 웹 `matchPrefsServer.ts` 를
/// 옮긴 것이다.
///
/// 🔴 **두 모양이 세 군데서 어긋난다** — 그냥 갈아 끼우면 조용히 틀린 값이
/// 저장된다:
///
/// | | 화면 | 계약 |
/// |---|---|---|
/// | 요일 | `day` **0(일)~6(토)** | `weekday` **0(월)~6(일)** |
/// | 시각 | `HH:MM` | `HH:MM:SS` |
/// | 지역·자리 | **이름·약칭** | **id** |
///
/// 🔴 **변환은 이 파일에만 둔다.** 두 군데서 하면 한쪽만 고쳐져 저장할 때와
/// 읽을 때가 갈린다 — 그러면 요일이 하루씩 밀리는데 **화면에는 아무 표시도
/// 안 난다**(겹침 계산만 조용히 틀린다).
library;

import 'match_prefs.dart';

/// 지역·포지션처럼 **id 와 보이는 글자**를 함께 갖는 참조 값.
class RefItem {
  const RefItem({required this.id, required this.label});

  final String id;

  /// 지역이면 이름(`서울 강남구`), 포지션이면 약칭(`MF`).
  final String label;
}

/// 계약이 주고받는 시간대 한 줄.
class MatchSlot {
  const MatchSlot({
    required this.weekday,
    required this.startTime,
    required this.endTime,
  });

  factory MatchSlot.fromJson(Map<String, dynamic> json) => MatchSlot(
        weekday: json['weekday'] as int,
        startTime: json['start_time'] as String,
        endTime: json['end_time'] as String,
      );

  /// 🔴 **0 = 월요일**이다(화면의 `day` 와 다르다).
  final int weekday;
  final String startTime;
  final String endTime;

  Map<String, dynamic> toJson() => {
        'weekday': weekday,
        'start_time': startTime,
        'end_time': endTime,
      };
}

/// 계약 모양의 조건 한 벌.
class ServerPrefs {
  const ServerPrefs({
    required this.regionIds,
    required this.slots,
    this.positionIds = const [],
  });

  factory ServerPrefs.fromJson(Map<String, dynamic> json) => ServerPrefs(
        regionIds: (json['region_ids'] as List?)?.cast<String>() ?? const [],
        slots: ((json['slots'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(MatchSlot.fromJson)
            .toList(),
        positionIds:
            (json['position_ids'] as List?)?.cast<String>() ?? const [],
      );

  final List<String> regionIds;
  final List<MatchSlot> slots;

  /// ⚠️ **팀 조건에는 없다** — 계약이 개인 조건에만 둔다.
  final List<String> positionIds;

  Map<String, dynamic> toJson({bool withPositions = false}) => {
        'region_ids': regionIds,
        'slots': [for (final s in slots) s.toJson()],
        if (withPositions) 'position_ids': positionIds,
      };
}

/// 화면 요일(0=일) → 계약 요일(0=월). 일(0)→6 · 월(1)→0 · 토(6)→5.
int _toServerWeekday(int day) => (day + 6) % 7;

/// 계약 요일(0=월) → 화면 요일(0=일). 위의 역이다.
int _toScreenDay(int weekday) => (weekday + 1) % 7;

MatchSlot toServerSlot(TimeSlot t) => MatchSlot(
      weekday: _toServerWeekday(t.day),
      startTime: '${t.from}:00',
      endTime: '${t.to}:00',
    );

TimeSlot toScreenSlot(MatchSlot s) => TimeSlot(
      day: _toScreenDay(s.weekday),
      /* `HH:MM:SS` → `HH:MM`. 🔴 서버가 초를 **안 붙여** 보내도 앞 다섯 자는
         같다 — 그래서 자르는 것이 아니라 앞에서 가져온다. */
      from: s.startTime.substring(0, 5),
      to: s.endTime.substring(0, 5),
    );

/// 보낼 모양으로 옮긴다.
///
/// 🔴 **모르는 지역 이름은 버린다.** 그대로 실어 보내면 422 `UNKNOWN_REGION`
/// 이고, 계약의 `PUT` 은 **통째로 교체**라 그 한 줄 때문에 **조건 전체가**
/// 저장되지 않는다. 이름을 지어내지도 않는다.
ServerPrefs toServerPrefs(MatchPrefs prefs, List<RefItem> regions) {
  final idOf = {for (final r in regions) r.label: r.id};
  return ServerPrefs(
    regionIds: [
      for (final label in prefs.regions) ?idOf[label],
    ],
    slots: prefs.times.map(toServerSlot).toList(),
  );
}

/// **내 조건**을 보낼 모양으로 — 팀 조건에 **포지션이 더 붙는다.**
///
/// 🔴 **화면은 약칭(`MF`)을, 계약은 id 를 쓴다.** 약칭은 **종목 안에서만**
/// 유일해서(야구 `C`=포수 · 농구 `C`=센터) 그대로 보낼 수가 없다.
/// 모르는 약칭은 지역과 같은 이유로 버린다.
ServerPrefs toServerMemberPrefs(
  MatchPrefs prefs,
  List<RefItem> regions,
  List<RefItem> positions,
) {
  final idOf = {for (final p in positions) p.label: p.id};
  final base = toServerPrefs(prefs, regions);
  return ServerPrefs(
    regionIds: base.regionIds,
    slots: base.slots,
    positionIds: [
      for (final code in prefs.positions) ?idOf[code],
    ],
  );
}

/// 받은 모양을 화면 모양으로 되돌린다.
///
/// 🔴 **모르는 id 는 이름을 지어내지 않고 뺀다** — 목록에 없는 것을
/// 「알 수 없음」 같은 글자로 채우면 사용자가 그것을 고른 줄로 읽는다.
MatchPrefs toScreenPrefs(
  ServerPrefs pref,
  List<RefItem> regions, {
  List<RefItem> positions = const [],
}) {
  final labelOf = {for (final r in regions) r.id: r.label};
  final codeOf = {for (final p in positions) p.id: p.label};
  return MatchPrefs(
    regions: [
      for (final id in pref.regionIds) ?labelOf[id],
    ],
    times: pref.slots.map(toScreenSlot).toList(),
    positions: [
      for (final id in pref.positionIds) ?codeOf[id],
    ],
  );
}
