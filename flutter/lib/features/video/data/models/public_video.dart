/// 누군가 **공개해 둔** 클립 한 편 — 계약 `GET /videos/public` 한 줄.
///
/// 🔴 **[MyVideo] 와 다른 모델이다.** 같은 「영상」이지만 서버가 주는 것이
/// 다르다 — 이쪽에는 **저장 키가 없고**(키에 업로더의 `user_id` 가 그대로
/// 들어 있어서 일부러 뺀 것이다, 미결 `paik` 16번) 대신 **업로더**가 실린다.
/// 하나로 합치면 안 오는 칸을 `null` 로 채우게 되고, 그러면 화면이 「없는
/// 것」과 「이 갈래엔 원래 없는 것」을 못 가른다.
///
/// 🔴 **목록에 드는 조건은 `is_public && kept` 다**(서버 질의). 올리는 것만으로는
/// 안 뜬다 — 등록 시 `is_public` 은 무조건 `false` 이고, 「공개」로 바꿔야 한다.
/// `kept` 는 업로드 갈래면 등록과 동시에 참, 분석 갈래면 「프로필에 저장」을
/// 눌러야 참이 된다.
class PublicVideo {
  const PublicVideo({
    required this.id,
    required this.sportCode,
    required this.durationMs,
    required this.createdAt,
    this.title,
    this.description,
    this.uploaderNickname,
    this.uploaderCardSlug,
    this.width,
    this.height,
  });

  factory PublicVideo.fromJson(Map<String, dynamic> json) => PublicVideo(
        id: json['id'] as String,
        sportCode: json['sport_code'] as String? ?? '',
        durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
        createdAt: DateTime.parse(json['created_at'] as String),
        title: json['title'] as String?,
        description: json['description'] as String?,
        uploaderNickname: json['uploader_nickname'] as String?,
        uploaderCardSlug: json['uploader_card_slug'] as String?,
        width: (json['width'] as num?)?.toInt(),
        height: (json['height'] as num?)?.toInt(),
      );

  final String id;
  final String sportCode;
  final int durationMs;
  final DateTime createdAt;
  final String? title;
  final String? description;

  /// 올린 사람 — **모든 사용자에게 있다.**
  final String? uploaderNickname;

  /// 올린 사람의 카드 슬러그 — **카드를 만든 사람만.** 있으면 눌러서 그 사람
  /// 카드로 갈 수 있다.
  final String? uploaderCardSlug;

  /// 원본 화면 크기. 🔴 **이 칸이 생기기 전 등록분은 둘 다 `null`** 이다 —
  /// 그때는 [aspectRatio] 가 16:9 로 답한다(계약이 정한 기존 동작).
  final int? width;
  final int? height;

  /// 칸 비율 — 🔴 **화면이 미리 알아야 덜컥거리지 않는다**(미결 `paik` 15번).
  /// 값이 없거나 이상하면 16:9.
  double get aspectRatio {
    final w = width, h = height;
    if (w == null || h == null || w <= 0 || h <= 0) return 16 / 9;
    return w / h;
  }
}
