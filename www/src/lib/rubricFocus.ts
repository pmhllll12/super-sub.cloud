/**
 * **무엇을 집중해서 볼지** — 에이전트가 실제로 채점하는 항목들.
 *
 * 🔴 **정본은 `agent/rubrics/*.yaml` 이다.** 여기 있는 것은 그 파일들에서
 * 옮겨 적은 사본이고, 화면이 루브릭 파일을 읽을 수 없어서(파이썬 쪽이다)
 * 이렇게 둔다. 항목 이름 · id 는 그 파일의 `criteria[].name` · `id` 와
 * **글자까지 같아야 한다** — 갈리면 화면이 고른 것과 서버가 채점한 것이
 * 서로를 못 가리킨다.
 *
 * 🔴 **종목당 `status: active` 인 루브릭 하나만 싣는다.** 루브릭 파일이 그
 * 규칙을 스스로 적어 두었다 — *"status: 사용자 선택지에 올릴지 여부 — active만
 * 오른다. draft는 파일은 갖추었으나 아직 열지 않은 동작이다."*
 * 그래서 아래 셋에는 draft 인 인사이드 패스 · 타격 · 레이업이 **없다.**
 * (2026-09-08 기준. `grep -l 'status: active' agent/rubrics/*.yaml` 로 확인한다.)
 *
 * 🔴 **`deferred` 항목은 뺐다.** 루브릭이 "지금은 못 잰다"고 미뤄 둔 것들이다
 * (농구의 릴리스 높이 · 팔꿈치 정렬, 축구의 임팩트 지점 · 스윙 가속 타이밍,
 * 야구의 릴리스 포인트 일관성 · 그립). 못 보는 것을 고르게 하면 고르고도
 * 아무 답을 못 받는다.
 *
 * ⚠️ **고른 값을 아직 아무 데도 못 보낸다.** 계약 3-6절에 실을 자리가 없고
 * (동작조차 없다 — 미결 jin 17번), 에이전트 CLI 에도 "이 항목만 봐 달라"는
 * 옵션이 없다(`analyze_s3.py --help` 로 확인했다). 화면에만 남는 값이고,
 * 미결 paik 8번이 그 자리를 요청한다.
 */
import type { SportKey } from '@/lib/sports'

export type FocusItem = {
  /** 루브릭의 `criteria[].id`. 자리가 생기면 이 값이 그대로 나간다. */
  id: string
  /** 루브릭의 `criteria[].name`. 화면에 그대로 적는다. */
  label: string
}

export type SportFocus = {
  /** 그 종목의 열린 동작(루브릭의 `motion_ko`). 안내 문장에 쓴다. */
  motion: string
  /** 루브릭 파일 이름 — 어디서 왔는지 화면 코드에서 되짚을 수 있게 남긴다. */
  rubric: string
  items: FocusItem[]
}

export const FOCUS: Record<SportKey, SportFocus> = {
  soccer: {
    motion: '인스텝 슈팅',
    rubric: 'football_instep_shot',
    items: [
      { id: 'plant_knee_flexion', label: '디딤발 무릎 굴곡' },
      { id: 'swing_knee_extension', label: '차는 다리 무릎 신전' },
      { id: 'trunk_lean', label: '상체 기울기' },
      { id: 'hip_rotation', label: '골반 회전' },
      { id: 'follow_through', label: '팔로스루' },
      { id: 'plant_foot_position', label: '디딤발 위치' },
    ],
  },
  baseball: {
    motion: '투구',
    rubric: 'baseball_pitching',
    items: [
      { id: 'release_arm_extension', label: '릴리스 팔 신전' },
      { id: 'hip_shoulder_separation', label: '골반-어깨 분리' },
      { id: 'stride_leg_block', label: '디딤발 버팀' },
      { id: 'trunk_tilt', label: '상체 기울기' },
      { id: 'arm_deceleration', label: '팔 감속' },
    ],
  },
  basketball: {
    motion: '점프슛',
    rubric: 'basketball_jump_shot',
    items: [
      { id: 'release_arm_extension', label: '슛하는 팔 신전' },
      { id: 'guide_hand', label: '가이드 핸드' },
      { id: 'follow_through', label: '팔로스루' },
      { id: 'trunk_alignment', label: '상체 정렬' },
      { id: 'leg_drive', label: '하체 신전' },
    ],
  },
}
