import 'clip_file.dart';
import 'models/my_video.dart';
import 'models/video_report.dart';

/// 화면이 아는 유일한 영상 계약.
///
/// 구현체가 Mock 인지 API 인지 화면은 모른다. 교체는 `video_providers.dart`
/// 한 줄이다 — **네 번째 교체 지점**이다(auth · chat · sport 다음).
abstract class VideoRepository {
  /// 내 클립 목록. **최근 것이 앞에 온다.**
  Future<List<MyVideo>> myVideos();

  /// 재생용 사전 서명 주소. **없으면 `null`.**
  ///
  /// 🔴 **404 는 예외가 아니다** — 계약이 「없는 클립」과 「비공개 남의 클립」을
  /// 같게 답하기로 했고(`VIDEO_NOT_FOUND`), 배포 환경에서 저장소가 안 붙어
  /// 있으면 주소가 아예 안 나오는 것도 정상 상태다. 그때 화면은 플레이어
  /// 자리를 비워 두고 나머지를 그대로 그린다.
  ///
  /// 🔴 **캐시하지 않는다** — `expires_in`(900초) 뒤 만료된다. 볼 때마다 받는다.
  Future<String?> playbackUrl(String videoId);

  /// 클립을 올린다 — 계약 3-6절의 **세 단계를 한 덩어리로.**
  ///
  /// ```
  /// (1) POST /videos/upload-url   올릴 자리를 받는다
  /// (2) PUT  <upload_url>          S3 에 직접 (앱 서버를 안 지난다, PER-002)
  /// (3) POST /videos               등록하고 서버가 규격을 검사한다
  /// ```
  ///
  /// 🔴 **반려(`passed: false`)는 예외가 아니다.** 계약이 `201` 로 답하고
  /// 사유를 본문에 싣는다 — 예외로 만들면 **그 사유가 화면까지 못 온다.**
  /// 부르는 쪽은 상태 코드가 아니라 [MyVideo.passed] 로 분기한다.
  ///
  /// [analyze] 가 거짓이면 **규격은 검사하되 분석 작업을 만들지 않는다**
  /// (「업로드 영상」). ⚠️ **보낸 뜻이 아니라 돌아온 응답을 믿는다** — 서버가
  /// 무시하고 분석을 걸면 `analysis_job_id` 가 채워져 오고, 그때는 「분석
  /// 영상」이 사실이다.
  Future<MyVideo> uploadClip({
    required ClipFile file,
    required ClipMeta meta,
    required String sportCode,
    bool analyze = false,
  });

  /// 공개 여부 · 제목 · 한 줄 설명 · 대표 여부를 바꾼다.
  ///
  /// 🔴 **보낸 것만 바뀐다.** 안 보낸 것은 그대로다. 응답은 **바뀐 한 줄**이라
  /// 화면은 목록에서 그 줄만 갈아 끼우면 된다.
  ///
  /// 🔴 **반려된 클립은 대표가 될 수 없다** → `422 CANNOT_FEATURE`.
  /// 🔴 대표는 **사람당 하나** — 세우면 다른 대표가 자동으로 내려간다. 옛
  /// 대표를 따로 내리지 않는다(서버가 지킨다).
  Future<MyVideo> patchVideo(
    String videoId, {
    bool? isPublic,
    String? title,
    String? description,
    bool? isFeatured,
  });

  /// 클립을 지운다 — 저장소의 영상과 그 분석 리포트까지. **되돌릴 수 없다.**
  ///
  /// 🔴 공개·대표는 **따로 지울 것이 없다** — 둘 다 클립의 성질이라 클립이
  /// 사라지면서 같이 없어진다. 여기서 `patchVideo` 를 부르면 **방금 지운
  /// 영상에 PATCH 를 쏘게 되고** 404 다.
  Future<void> deleteVideo(String videoId);

  /// 그 영상의 분석 리포트.
  ///
  /// 🔴 **예외가 아니라 갈래를 돌려준다** — [ReportResult] 머리말 참고.
  Future<ReportResult> report(String videoId);
}
