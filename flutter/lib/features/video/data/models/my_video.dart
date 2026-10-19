/// 내 클립 한 편 — 계약 `GET /videos` 한 줄(= `POST /videos` 응답과 같은 모양).
///
/// 🔴 **갈래를 가르는 것은 [analysisJobId] 다**(웹 `MyVideos.tsx` 와 같은 판단).
/// [analysisStatus] 로 가르면 **분석을 걸었지만 아직 대기 중인 클립이
/// 「그냥 올린 것」 쪽으로 새어 나간다.**
///
/// 🔴 **반려된 클립은 업로드 갈래에 남는다** — 규격에 걸리면 분석을 아예 하지
/// 않으므로(계약 3-6절) 작업이 없는 것이 사실이고, 그 자리에서 반려 사유를
/// 보는 것이 사용자에게도 맞다.
class MyVideo {
  const MyVideo({
    required this.id,
    required this.sportCode,
    required this.storageKey,
    required this.durationMs,
    required this.createdAt,
    required this.passed,
    this.side,
    this.rejectReason,
    this.analysisJobId,
    this.analysisStatus,
    this.isPublic = false,
    this.isFeatured = false,
    this.title,
    this.description,
    this.kept = true,
    this.duplicateOfVideoId,
    this.duplicateStatus,
    this.duplicateFailureReason,
  });

  factory MyVideo.fromJson(Map<String, dynamic> json) => MyVideo(
        id: json['id'] as String,
        sportCode: json['sport_code'] as String,
        storageKey: json['storage_key'] as String? ?? '',
        durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
        createdAt: DateTime.parse(json['created_at'] as String),
        passed: json['passed'] as bool? ?? true,
        side: json['side'] as String?,
        rejectReason: json['reject_reason'] as String?,
        analysisJobId: json['analysis_job_id'] as String?,
        analysisStatus: json['analysis_status'] as String?,
        isPublic: json['is_public'] as bool? ?? false,
        isFeatured: json['is_featured'] as bool? ?? false,
        title: json['title'] as String?,
        description: json['description'] as String?,
        kept: json['kept'] as bool? ?? true,
        duplicateOfVideoId: json['duplicate_of_video_id'] as String?,
        duplicateStatus: json['duplicate_status'] as String?,
        duplicateFailureReason: json['duplicate_failure_reason'] as String?,
      );

  final String id;
  final String sportCode;

  /// S3 저장 키. 🔴 **뜯어보지 않는다** — 계약이 「그대로 넘긴다」로 정했다.
  /// 재생은 이 값이 아니라 `playbackUrl()` 로 받은 사전 서명 주소로 한다
  /// (키를 그대로 틀면 403 이다).
  final String storageKey;

  final int durationMs;
  final DateTime createdAt;

  /// 규격 검사를 통과했는가. 🔴 **반려는 실패가 아니라 `201` 이다** — 상태
  /// 코드가 아니라 이 값으로 분기한다(계약 3-6절).
  final bool passed;

  /// 던지는 팔·차는 발. 안 정했으면 `null`(에이전트가 자동 판별).
  final String? side;

  /// 반려 사유. [passed] 가 거짓일 때만 있다.
  final String? rejectReason;

  /// 🔴 **이 값이 갈래를 가른다.** 있으면 「분석 영상」, 없으면 「업로드 영상」.
  final String? analysisJobId;

  /// 가장 최근 분석 작업의 상태 — `queued` · `running` · `succeeded` · `failed`.
  /// 반려된 클립은 작업이 없어 `null` 이다.
  ///
  /// 🔴 **문자열 그대로 둔다** — 값이 늘 때 앱을 고치지 않으려는 것이다.
  final String? analysisStatus;

  final bool isPublic;

  /// 「나를 보여주는 대표 영상」인가. 🔴 **사람당 하나** — 세우면 다른 대표가
  /// 자동으로 내려간다(서버의 부분 유일 인덱스가 지킨다).
  final bool isFeatured;

  final String? title;
  final String? description;

  /// 프로필에 남았는가. 🔴 목록에는 `kept: true` 만 오므로 화면에서 볼 일은
  /// 없지만, 등록 직후 응답에는 `false` 가 올 수 있어 자리를 둔다.
  final bool kept;

  /// 같은 내용을 다시 올렸을 때 결과를 빌려온 원본 영상의 id (`ho` 41번).
  final String? duplicateOfVideoId;

  /// 🔴 **아래 둘은 등록 응답 한 번에만 실린다.** 나중에 목록으로 다시 읽으면
  /// `null` 이다 — 그 자리에서 화면에 반영하지 않으면 다시 볼 방법이 없다.
  final String? duplicateStatus;
  final String? duplicateFailureReason;

  /// 「분석 영상」 갈래인가.
  bool get analyzed => analysisJobId != null;

  MyVideo copyWith({
    bool? isPublic,
    bool? isFeatured,
    String? title,
    bool clearTitle = false,
    String? description,
    bool clearDescription = false,
    // 🔴 **프로필에 저장했는가** — `POST /videos/{id}/keep` 이 켜는 값이다.
    bool? kept,
  }) =>
      MyVideo(
        id: id,
        sportCode: sportCode,
        storageKey: storageKey,
        durationMs: durationMs,
        createdAt: createdAt,
        passed: passed,
        side: side,
        rejectReason: rejectReason,
        analysisJobId: analysisJobId,
        analysisStatus: analysisStatus,
        isPublic: isPublic ?? this.isPublic,
        isFeatured: isFeatured ?? this.isFeatured,
        title: clearTitle ? null : (title ?? this.title),
        description:
            clearDescription ? null : (description ?? this.description),
        kept: kept ?? this.kept,
        duplicateOfVideoId: duplicateOfVideoId,
        duplicateStatus: duplicateStatus,
        duplicateFailureReason: duplicateFailureReason,
      );

  @override
  bool operator ==(Object other) => other is MyVideo && other.id == id;

  @override
  int get hashCode => id.hashCode;
}

/// 클립의 지금 상태 — 알약 아래 배지로 나온다(웹 `videoState`).
///
/// 🔴 **반려를 먼저 본다.** 반려된 클립은 작업이 없어 [MyVideo.analysisStatus]
/// 가 `null` 인데 **분석을 안 건 클립도 `null`** 이라, 순서를 바꾸면 둘이 섞인다.
({String key, String label}) videoState(MyVideo v) {
  if (!v.passed) return (key: 'rejected', label: '규격 반려');
  switch (v.analysisStatus) {
    case 'succeeded':
      return (key: 'analyzed', label: '분석 완료');
    case 'queued':
    case 'running':
      return (key: 'running', label: '분석 중');
    case 'failed':
      return (key: 'failed', label: '분석 실패');
    default:
      return (key: 'raw', label: '분석 안 함');
  }
}
