import 'dart:typed_data';

import 'clip_file.dart';
import 'models/my_video.dart';
import 'models/public_video.dart';
import 'models/reference_player.dart';
import 'models/skeleton.dart';
import 'models/video_report.dart';

/// 화면이 아는 유일한 영상 계약.
///
/// 구현체가 Mock 인지 API 인지 화면은 모른다. 교체는 `video_providers.dart`
/// 한 줄이다 — **네 번째 교체 지점**이다(auth · chat · sport 다음).
abstract class VideoRepository {
  /// 내 클립 목록. **최근 것이 앞에 온다.**
  Future<List<MyVideo>> myVideos();

  /// 누군가 공개해 둔 클립 목록 — 🔴 **남의 것까지** 온다. 최근 것이 앞.
  ///
  /// 🔴 **[myVideos] 로 때우지 말 것.** 홈의 영상 줄이 이걸 쓰는데, 내 것만
  /// 주면 「업로드된 영상들을 보여 준다」가 「내가 올린 것만 보여 준다」가 된다.
  /// 계약 테스트가 **올린 사람이 여럿인지**로 그걸 잡는다.
  ///
  /// 🔴 **목록에 드는 조건은 서버가 정한다** — `is_public && kept`. 올리는
  /// 것만으로는 안 뜬다(자세한 것은 [PublicVideo] 머리말).
  ///
  /// 🔴 **재생 주소는 안 실린다.** 영상마다 [playbackUrl] 로 따로 받는다.
  Future<List<PublicVideo>> publicVideos();

  /// 카드에 깔 **한 장면**(JPEG). **없으면 `null`.**
  ///
  /// 🔴 **[playbackUrl] 로 대신하지 말 것.** 그 주소로 영상을 열어 첫 프레임을
  /// 뽑던 것이 **한 장에 1.9초**였다(실기기 실측). 이쪽은 서버가 미리 떠서
  /// 캐시해 둔 작은 JPEG 이라 즉시 온다.
  ///
  /// 🔴 **`null` 은 정상이다** — 못 뜨는 영상(형식·길이)이 있고, 서버에
  /// `ffmpeg` 이 없는 배포도 그렇다. 화면은 그때 자리표시를 그린다.
  Future<Uint8List?> poster(String videoId);

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

  /// **프로필에 저장한다** — `kept` 를 참으로 만든다 (2026-09-24 신설).
  ///
  /// 🔴 **분석한 클립은 이걸 안 부르면 사라진다.** `analyze: true` 로 등록한
  /// 클립은 `kept: false` 로 시작해서 **본인 목록에도 공개 목록에도 안 뜨고**,
  /// 화면을 벗어나면 서버의 TTL 백스톱이 지운다(계약 3-6절). 분석 결과를
  /// 남기려면 **리포트가 나온 뒤 이 호출이 있어야 한다.**
  ///
  /// 🔴 **리포트가 `ready` 일 때만 부른다.** 실패·반려로 끝났으면 남길 것이
  /// 없다(웹도 같은 규칙이다).
  ///
  /// ⚠️ **멱등이다** — 이미 저장된 클립에 다시 불러도 `200` 이다.
  /// ⚠️ **갈래마다 3개 상한이 여기 걸린다** → `422 VIDEO_LIMIT_EXCEEDED`.
  /// 그 상한을 **진짜로 지키는 관문이 이 호출**이라, 화면은 이 자리에서
  /// 사유를 보여 줘야 한다.
  ///
  /// 응답은 `GET /videos` 한 줄과 같은 모양이다 — 🔴 **`storage_key` 가
  /// 바뀌어 온다**(임시 자리에서 리포트 자리로 옮기기 때문).
  Future<MyVideo> keepVideo(String videoId);

  /// 그 영상의 **관절 시계열** (계약 3-14절, 2026-09-25 신설).
  ///
  /// 🔴 **오류 셋이 [report] 와 같다** — `VIDEO_NOT_FOUND`·`ANALYSIS_FAILED`·
  /// `REPORT_NOT_READY`. 그래서 화면이 리포트를 다루던 방식을 그대로 쓴다.
  ///
  /// 🔴 **옛 리포트는 `200` 으로 `{known:false}` 가 온다** — 404 가 아니다.
  /// 「관절이 없다」와 「리포트가 없다」는 다른 상태라서다.
  Future<SkeletonResult> skeleton(String videoId);

  /// 견줄 **본보기 선수** 목록 (계약 3-14절).
  ///
  /// 🔴 **재생 주소는 안 온다** — 영상은 앱이 에셋으로 들고 다닌다
  /// ([ReferencePlayer] 머리말). 서버가 주는 것은 `id` 와 `name` 뿐이다.
  Future<List<ReferencePlayer>> referencePlayers();

  /// 그 선수의 **관절 시계열** — [skeleton] 과 **모양이 같다**(계약).
  ///
  /// 🔴 **오류 셋이 다르다.** 영상 쪽은 「아직 안 끝남」이 있지만 선수는 미리
  /// 계산되어 있어 없으면 그냥 `404 PLAYER_NOT_FOUND` 다 — 다시 물어도 안 바뀐다.
  Future<SkeletonResult> referencePlayerSkeleton(String playerId);

  /// 그 영상의 분석 리포트.
  ///
  /// 🔴 **예외가 아니라 갈래를 돌려준다** — [ReportResult] 머리말 참고.
  Future<ReportResult> report(String videoId);
}
