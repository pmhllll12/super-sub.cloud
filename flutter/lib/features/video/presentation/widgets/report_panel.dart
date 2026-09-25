import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../data/models/video_report.dart';
import '../../data/video_providers.dart';
import 'report_view.dart';

/// 분석 리포트 — 🔴 **화면이 아니라 판이다.**
///
/// 처음엔 전체 화면으로 밀었다(`report_screen.dart`, 2026-09-25에 지웠다).
/// 사용자가 **제자리에서 펴지는 쪽**으로 정했다: 「새로운 리포트 탭이 나오는게
/// 아니라 부드럽고 자연스럽게 펴지면서 아래로 리포트 나오게 해줘」.
/// 화면을 밀면 위에서 돌던 영상이 사라졌다 돌아오고, 닫으려면 뒤로 가야 한다 —
/// 리포트는 **그 영상에 딸린 것**이라 같은 화면에 있는 편이 맞다.
///
/// ⛔ 다시 `Navigator.push` 로 되돌리지 말 것.
///
/// 🔴 **밝은 판 위에 산다** — [ReportView] 는 어두운 바탕 전제(흰 글자)라
/// `onPaper: true` 를 안 넘기면 글자가 판에 묻혀 아무것도 안 보인다.
class ReportPanel extends ConsumerWidget {
  const ReportPanel({super.key, required this.videoId, this.title});

  final String videoId;

  /// 어느 영상의 리포트인지 — 없으면 제목 줄을 안 낸다.
  final String? title;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncReport = ref.watch(videoReportProvider(videoId));

    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: asyncReport.when(
        loading: () => const Padding(
          padding: EdgeInsets.symmetric(vertical: 22),
          child: Center(
            child: SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 1.8,
                color: _kMuted,
              ),
            ),
          ),
        ),
        /* 🔴 **읽기 자체가 실패한 것**(네트워크·401)은 리포트 갈래가 아니다.
           「리포트가 없다」로 보이면 화면이 조용히 잘못된 상태에 머문다. */
        error: (e, _) => _Note(
          text: '$e',
          onRetry: () => ref.invalidate(videoReportProvider(videoId)),
        ),
        data: (result) => switch (result) {
          ReportReady(:final report) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                /* 🔴 **얇은 줄 하나로 위와 가른다** — 밝은 판이라 이 한 줄이
                   「여기부터 리포트」를 말하는 전부다(분석 화면과 같다). */
                const Divider(color: Color(0x22000000), height: 1),
                const SizedBox(height: 14),
                if (title != null && title!.isNotEmpty) ...[
                  Text(
                    title!,
                    style: const TextStyle(color: _kMuted, fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                ],
                ReportView(report: report, onPaper: true),
                const SizedBox(height: 14),
                Text(
                  '${report.savedAt} 에 분석했습니다.',
                  style: const TextStyle(color: _kMuted, fontSize: 12),
                ),
              ],
            ),
          /* 🔴 **「아직」에는 다시 볼 길을 준다** — 분석이 끝나면 여기에 나온다.
             반대로 아래 「실패」에는 주지 않는다: 다시 물어봐도 절대 안 바뀌는데
             단추를 두면 영영 누르게 된다(웹에서 사용자가 실제로 그 무한 반복을
             겪었다). */
          ReportNotReady() => _Note(
              text: '분석 중입니다 — 끝나면 여기에 나옵니다.',
              onRetry: () => ref.invalidate(videoReportProvider(videoId)),
            ),
          ReportFailed(:final reason) => _Note(text: '분석에 실패했습니다 — $reason'),
          ReportMissing() => const _Note(text: '리포트를 찾을 수 없습니다.'),
          ReportError(:final message) => _Note(
              text: message,
              onRetry: () => ref.invalidate(videoReportProvider(videoId)),
            ),
        },
      ),
    );
  }
}

const Color _kOnPaper = Color(0xFF14161A);
const Color _kMuted = Color(0xFF6B7078);

class _Note extends StatelessWidget {
  const _Note({required this.text, this.onRetry});

  final String text;

  /// `null` 이면 다시 볼 단추를 안 낸다 — **다시 해도 안 바뀌는 상태**다.
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 18),
        child: Column(
          children: [
            Text(
              text,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: _kOnPaper,
                fontSize: 13.5,
                height: 1.5,
              ),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 14),
              // 🔴 다른 단추와 같은 알약이다 — 네모 테두리로 되돌리지 말 것.
              GestureDetector(
                key: const Key('report-retry'),
                onTap: onRetry,
                behavior: HitTestBehavior.opaque,
                child: Container(
                  height: 36,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: BoxDecoration(
                    border: Border.all(color: _kOnPaper.withValues(alpha: 0.3)),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Symbols.refresh, size: 16, color: _kOnPaper),
                      SizedBox(width: 5),
                      Text(
                        '다시 확인',
                        style: TextStyle(
                          color: _kOnPaper,
                          fontSize: 12.5,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      );
}
