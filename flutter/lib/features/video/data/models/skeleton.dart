/// 영상 한 편의 **관절 시계열** — 계약 3-14절(`GET /videos/{id}/skeleton`).
///
/// 🔴 **에이전트가 낸 값이다.** 웹 화면은 브라우저에서 MoveNet 을 실시간으로
/// 돌리지만(그쪽은 tfjs·canvas 에 매여 있어 앱으로 못 옮긴다), 이 경로는
/// **서버가 이미 계산해 둔 것**을 그대로 내준다 — 앱은 **받아서 그리기만**
/// 하면 된다.
///
/// 🔴 **선수 관절도 같은 모양이다**(`GET /reference-players/{id}/skeleton`) —
/// 다음 회차의 「선수와 비교하기」가 이 클래스를 그대로 쓴다.
class Skeleton {
  const Skeleton({
    required this.known,
    this.why,
    this.fps = 0,
    this.frameWidth = 0,
    this.frameHeight = 0,
    this.swingLeg,
    this.direction,
    this.keypointNames = const [],
    this.joints = const [],
    this.moments = const {},
    this.momentsSeconds = const {},
    this.afterClipped = false,
  });

  /// 🔴 **거짓은 오류가 아니다.** 옛 리포트(`schema_version` 1.4 이전)는 관절이
  /// 없어서 **404 가 아니라 `200` 으로** `{known: false, why}` 가 온다 —
  /// 「리포트 자체가 없는 것」과 다른 상태라서다(계약). 화면은 그냥 안 그린다.
  final bool known;
  final String? why;

  final double fps;

  /// 원본 화면 크기 — 좌표가 이 값으로 **나눠진** 채 온다.
  final int frameWidth;
  final int frameHeight;

  /// 차는 다리(`left`·`right`)와 차는 방향(오른쪽이 1).
  final String? swingLeg;
  final int? direction;

  /// 🔴 **인덱스의 뜻은 이 목록이 정한다** — COCO-17 순서를 **따로 상수로 들고
  /// 있지 말 것.** 두 표가 갈려도 아무 데서도 안 터지고 그림만 틀어진다
  /// (웹이 지금 그 상태다 — `angles.ts` 가 순서를 하드코딩하고 있다).
  final List<String> keypointNames;

  /// 프레임마다 `[x, y, confidence]` × 관절 수.
  ///
  /// 🔴 **못 잡은 프레임은 `null` 로 자리를 지킨다 — 빼고 압축하지 말 것.**
  /// 인덱스가 곧 프레임 번호라, 어긋나면 세 순간이 엉뚱한 자세를 가리키는데
  /// **스켈레톤은 어느 쪽이든 그럴듯해 보여 눈으로도 안 잡힌다**(계약).
  final List<List<List<double>>?> joints;

  /// 세 순간의 **프레임 번호** — `before`(백스윙) · `impact`(접촉) · `after`.
  /// 🔴 **서버가 골라 준다** — 앱이 피크를 다시 찾을 필요가 없다.
  final Map<String, int> moments;

  /// 같은 세 순간의 **초**.
  final Map<String, double> momentsSeconds;

  /// `after` 가 영상 끝에 걸렸는가.
  final bool afterClipped;

  factory Skeleton.fromJson(Map<String, dynamic> json) {
    if (json['known'] != true) {
      return Skeleton(known: false, why: json['why'] as String?);
    }
    final size = (json['frame_size'] as List?) ?? const [0, 0];
    return Skeleton(
      known: true,
      fps: (json['fps'] as num?)?.toDouble() ?? 0,
      frameWidth: (size.isNotEmpty ? size[0] as num : 0).toInt(),
      frameHeight: (size.length > 1 ? size[1] as num : 0).toInt(),
      swingLeg: json['swing_leg'] as String?,
      direction: (json['direction'] as num?)?.toInt(),
      keypointNames: [
        for (final n in (json['keypoint_names'] as List?) ?? const [])
          n as String,
      ],
      joints: [
        for (final frame in (json['joints'] as List?) ?? const [])
          // 🔴 `null` 을 그대로 둔다 — 위 머리말.
          if (frame == null)
            null
          else
            [
              for (final kp in frame as List)
                [for (final v in kp as List) (v as num).toDouble()],
            ],
      ],
      moments: {
        for (final e in ((json['moments'] as Map?) ?? const {}).entries)
          e.key as String: (e.value as num).toInt(),
      },
      momentsSeconds: {
        for (final e in ((json['moments_seconds'] as Map?) ?? const {}).entries)
          e.key as String: (e.value as num).toDouble(),
      },
      afterClipped: json['after_clipped'] as bool? ?? false,
    );
  }

  /// 그 이름의 관절이 몇 번째인가 — 없으면 `-1`.
  int indexOf(String name) => keypointNames.indexOf(name);

  /// 그 **초**에 해당하는 프레임의 관절. 없거나 못 잡았으면 `null`.
  ///
  /// ⚠️ **재생 위치로 찾는다.** [fps] 가 0 이면 환산할 수가 없어 `null` 이다.
  List<List<double>>? at(Duration position) {
    if (!known || fps <= 0 || joints.isEmpty) return null;
    final i = (position.inMilliseconds / 1000 * fps).floor();
    if (i < 0 || i >= joints.length) return null;
    return joints[i];
  }
}

/// 관절 읽기의 갈래 — 🔴 **리포트와 오류 셋이 같다**(계약 3-14절). 그래서
/// 화면은 [ReportResult] 를 다루던 방식을 그대로 쓸 수 있다.
sealed class SkeletonResult {
  const SkeletonResult();
}

class SkeletonReady extends SkeletonResult {
  const SkeletonReady(this.skeleton);
  final Skeleton skeleton;
}

/// 아직 분석이 안 끝났다 — 다시 물으면 바뀐다.
class SkeletonNotReady extends SkeletonResult {
  const SkeletonNotReady();
}

/// 분석이 실패했거나 없는 영상이다 — 다시 물어도 안 바뀐다.
class SkeletonUnavailable extends SkeletonResult {
  const SkeletonUnavailable(this.reason);
  final String reason;
}
