import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/video_report.dart';
import '../../data/video_providers.dart';
import '../widgets/report_view.dart';

/// 분석 리포트 — **전체 화면으로 민다.**
///
/// 🔴 웹은 이것이 왼쪽 칸을 덮는 판인데, 폰에는 옆으로 펼 자리가 없다
/// (`www/docs/2026-08-31-앱-이식-지침.md` §2-2). 시트로 하면 레이더+항목+
/// 장면이 길어 내내 끌어야 해서 화면 전환으로 갔다.
class ReportScreen extends ConsumerWidget {
  const ReportScreen({super.key, required this.videoId, this.title});

  final String videoId;

  /// 어느 영상의 리포트인지 — 없으면 제목 없이 「분석 리포트」만.
  final String? title;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncReport = ref.watch(videoReportProvider(videoId));

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        foregroundColor: _kOn,
        title: const Text('분석 리포트'),
      ),
      body: SafeArea(
        child: asyncReport.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          /* 🔴 **읽기 자체가 실패한 것**(네트워크·401)은 리포트 갈래가 아니다.
             「리포트가 없다」로 보이면 화면이 조용히 잘못된 상태에 머문다. */
          error: (e, _) => _Note(
            text: '$e',
            onRetry: () => ref.invalidate(videoReportProvider(videoId)),
          ),
          data: (result) => switch (result) {
            ReportReady(:final report) => ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  if (title != null && title!.isNotEmpty) ...[
                    Text(
                      title!,
                      style: TextStyle(
                        color: _kOn.withValues(alpha: 0.6),
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  ReportView(report: report),
                  const SizedBox(height: 18),
                  Text(
                    '${report.savedAt} 에 분석했습니다.',
                    style: TextStyle(
                      color: _kOn.withValues(alpha: 0.5),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            /* 🔴 **「아직」에는 다시 볼 길을 준다** — 분석이 끝나면 여기에
               나온다. 반대로 아래 「실패」에는 주지 않는다: 다시 물어봐도
               절대 안 바뀌는데 단추를 두면 영영 누르게 된다(웹에서 사용자가
               실제로 그 무한 반복을 겪었다). */
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
      ),
    );
  }
}

const Color _kBg = Color(0xFF14201A);
const Color _kOn = Color(0xFFFFFFFF);

class _Note extends StatelessWidget {
  const _Note({required this.text, this.onRetry});

  final String text;

  /// `null` 이면 다시 볼 단추를 안 낸다 — **다시 해도 안 바뀌는 상태**다.
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              text,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: _kOn.withValues(alpha: 0.75),
                fontSize: 14,
                height: 1.5,
              ),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              OutlinedButton(
                key: const Key('report-retry'),
                onPressed: onRetry,
                style: OutlinedButton.styleFrom(
                  foregroundColor: _kOn,
                  side: BorderSide(color: _kOn.withValues(alpha: 0.4)),
                ),
                child: const Text('다시 확인'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
