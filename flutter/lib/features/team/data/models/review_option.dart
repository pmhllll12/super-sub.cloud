/// 평가에서 고를 수 있는 항목 한 줄 — `GET /review-options`.
///
/// 🔴 **문구를 앱에 박지 않는다.** 정본은 서버이고(마이그레이션이 시드한다),
/// **배열 순서가 곧 노출 순서**다 — 알파벳순으로 정렬하면 「주의」가 맨 앞에
/// 온다.
class ReviewOption {
  const ReviewOption({
    required this.code,
    required this.category,
    required this.label,
  });

  factory ReviewOption.fromJson(Map<String, dynamic> json) => ReviewOption(
        code: json['code'] as String,
        category: json['category'] as String? ?? '',
        label: json['label'] as String? ?? '',
      );

  /// 계약으로 나가는 값 — `option_codes` 에 이것을 싣는다.
  final String code;

  /// `manner` · `skill` · `repeat` · `caution`. 화면이 묶음을 나눌 때 쓴다.
  final String category;

  /// 사람이 읽는 문장. **이 글자를 그대로 보여 준다.**
  final String label;

  /// 🔴 **고르면 안 좋은 쪽**인가 — 화면이 색을 갈라야 잘못 누르지 않는다.
  bool get isCaution => category == 'caution';
}
