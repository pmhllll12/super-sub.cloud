import 'package:flutter/material.dart';

import '../../match_prefs.dart';
import '../sheets/sheet_skin.dart';

/// 새 시간대의 **첫 값** — 오늘 요일 · 다음 정각부터 두 시간.
///
/// 🔴 **요일을 박아 두지 않는다**(2026-09-25 사용자: 「왜 토요일과 시간대가
/// 고정이야」). 고르는 칸이 바로 옆에 있으니 첫 값은 **지금에 가까운 쪽**이
/// 손이 덜 간다.
TimeSlot defaultSlot([DateTime? now]) {
  final at = now ?? DateTime.now();
  // 화면의 `day` 는 0=일 기준이다(`DateTime.weekday` 는 1=월 … 7=일).
  final day = at.weekday % 7;

  /// 다음 30분 칸. 목록 밖이면(이른 새벽·자정 넘김) 첫 칸에서 시작한다.
  var i = kHours.indexWhere((h) {
    final p = h.split(':');
    final m = int.parse(p[0]) * 60 + int.parse(p[1]);
    return m > at.hour * 60 + at.minute;
  });
  if (i < 0) i = 0;
  /* 🔴 **마지막 칸에서 시작하면 끝을 둘 자리가 없다** — 한 칸 물러선다.
     안 그러면 `clamp` 의 아래 한계가 위 한계를 넘어 그 자리에서 터진다. */
  if (i >= kHours.length - 1) i = kHours.length - 2;
  // 끝은 두 시간 뒤(30분 칸 넷). 목록 끝을 넘지 않는다.
  final j = (i + 4).clamp(i + 1, kHours.length - 1);
  return TimeSlot(day: day, from: kHours[i], to: kHours[j]);
}

/// 시간대 한 줄을 **고르는** 칸 — 요일 · 시작 · 끝.
///
/// 🔴 **두 폼이 이것 하나를 나눠 쓴다**(팀 조건 · 내 조건). 2026-09-25에
/// 사용자가 잡았다: 「대체 왜 시간이랑 날짜를 선택할 수 없게 해놓은거야? 왜
/// 토요일과 시간대가 고정이야」 — 한쪽 폼에는 **고를 칸을 아예 안 넣고**
/// 토요일 09:00~11:00 을 박아 뒀었다. 두 폼이 각자 그리면 그런 일이 또 난다.
///
/// 🔴 **끝은 시작보다 뒤만 고른다.** 뒤집힌 시간은 겹침 계산에서 **늘
/// 거짓**이라 조용히 아무것도 안 걸린다 — 서버도 422 로 막는 까닭이다.
class SlotEditor extends StatelessWidget {
  const SlotEditor({
    super.key,
    required this.slot,
    required this.onChanged,
    required this.onRemove,
    this.removeKey,
  });

  final TimeSlot slot;
  final ValueChanged<TimeSlot> onChanged;
  final VoidCallback onRemove;

  /// 지우기 단추의 열쇠 — 시험이 그 줄을 집는다.
  final Key? removeKey;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        /* 🔴 **셋이 폭 360 에 간신히 든다** — 칸을 고정폭으로 두면 45px 이
           넘친다(시험이 잡았다). 남는 폭을 나눠 갖게 하고, 지우기 단추만
           제 크기를 지킨다. */
        child: Row(
          children: [
            /* 🔴 **셋 다 남는 폭을 나눠 갖는다.** 요일만 밖에 두면 그 칸이
               **폭 무한대**로 들어가고, `isExpanded` 가 그 자리에서 터진다. */
            Expanded(
              flex: 2,
              child: _Pick<int>(
                pickKey: const Key('slot-day'),
                value: slot.day,
                items: [for (var d = 0; d < 7; d++) (d, kDays[d])],
                onChanged: (d) =>
                    onChanged(TimeSlot(day: d, from: slot.from, to: slot.to)),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              flex: 3,
              child: _Pick<String>(
                pickKey: const Key('slot-from'),
              value: slot.from,
              items: [for (final h in kHours) (h, h)],
              onChanged: (h) => onChanged(
                TimeSlot(
                  day: slot.day,
                  from: h,
                  /* 🔴 **시작이 끝을 넘으면 끝도 함께 민다** — 안 그러면
                     뒤집힌 채로 저장돼 서버가 422 를 낸다. */
                    to: h.compareTo(slot.to) >= 0 ? _after(h) : slot.to,
                  ),
                ),
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4),
              child: Text('~', style: TextStyle(color: kSheetBoxInk)),
            ),
            Expanded(
              flex: 3,
              child: _Pick<String>(
                pickKey: const Key('slot-to'),
              value: slot.to,
              // 🔴 시작 이전은 아예 목록에 안 넣는다.
              items: [
                for (final h in kHours)
                  if (h.compareTo(slot.from) > 0) (h, h),
              ],
                onChanged: (h) =>
                    onChanged(TimeSlot(day: slot.day, from: slot.from, to: h)),
              ),
            ),
            IconButton(
              key: removeKey,
              tooltip: '지우기',
              onPressed: onRemove,
              icon: Icon(
                Icons.close,
                size: 18,
                color: kSheetBoxInk.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      );

  /// 그 시각 **바로 다음** 칸. 끝이면 마지막(24:00)에 머문다.
  static String _after(String h) {
    final i = kHours.indexOf(h);
    return i < 0 || i + 1 >= kHours.length ? kHours.last : kHours[i + 1];
  }
}

class _Pick<T> extends StatelessWidget {
  const _Pick({
    required this.pickKey,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final Key pickKey;
  final T value;
  final List<(T, String)> items;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: kSheetBoxInk.withValues(alpha: 0.25)),
        ),
        child: DropdownButton<T>(
          key: pickKey,
          value: value,
          isDense: true,
          // 🔴 남는 폭에 맞춘다 — 안 맞추면 긴 값에서 줄이 넘친다.
          isExpanded: true,
          underline: const SizedBox.shrink(),
          dropdownColor: kSheetBox,
          iconEnabledColor: kSheetBoxInk.withValues(alpha: 0.6),
          style: const TextStyle(color: kSheetBoxInk, fontSize: 13),
          items: [
            for (final (v, label) in items)
              DropdownMenuItem(
                value: v,
                child: Text(
                  label,
                  style: const TextStyle(color: kSheetBoxInk, fontSize: 13),
                ),
              ),
          ],
          onChanged: (v) {
            if (v != null) onChanged(v);
          },
        ),
      );
}
