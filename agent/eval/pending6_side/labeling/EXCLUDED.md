# 판독 단계에서 뺀 27클립 (2026.09.03)

`side_form.csv`는 **라벨이 있는 12건만** 담는다. 나머지 27건은 판독자가
**타자가 아니거나 스윙 상태가 아닌 이미지**로 판정해 뺀 것이다.

**여기 적어 두는 이유는 분모 때문이다.** `AFTER_LABELS.md` 0절이
"분모를 두 벌 적는다 — 39건 전체와, 제외한 유효 건수"라고 정해 두었는데,
서식에서 행을 지우면 39가 파일에서 사라진다. 전체 명단은
`reference_AFTER_LABELING.csv`(39행)에 남아 있고 이 문서가 사유를 잇는다.

## 🔴 두 사유가 합쳐졌다 — 되돌릴 수 없다

명세 0절은 제외 사유를 **둘로 갈라** 두었다.

| 사유 | 뜻 | 명세상 처리 |
|---|---|---|
| `subject_ok = n` | 스켈레톤이 타자가 아니다 | **클립 통째로** 제외 |
| `na` | 그 사지에 동작이 없다 | **해당 사지만** 제외 |

행을 지우는 방식은 둘을 구분하지 않으므로, 아래 27건이 각각 어느 쪽인지
**이 자료로는 알 수 없다.** 나중에 사지별 분모를 다시 세야 하면 그 27건을
다시 봐야 한다. 지금 계산에는 영향이 없다 — 둘 다 정확도 분모에서 빠진다.

## 명단

`phaseA_metadata.csv`의 독립 기록을 나란히 둔다. 판독 결과와 맞는지
대조하려는 것이지 판독을 뒤집으려는 것이 아니다.

| clip_id | `usable_for_phase_B` | `notes` |
|---|---|---|
| `3R1kvNrGJK0` | no | 펜스 너머. 심판/포수를 피사체로 잡음 |
| `3USSmzO001k` | maybe | — |
| `5-jBTNp5IQA` | no | — |
| `6hrcRyIYTrA` | no | — |
| `8gmHKqDxXdg` | no | 실내 티 드릴, 10초에 스윙 여러 번(240x180 10fps) |
| `Atzrde5uGcM` | yes | 유소년 경기. 배경에 관중 다수 |
| `CFjNxCZhn_8` | no | — |
| `Fz16t9SrF3U` | no | 펜스 가림 + 원거리 |
| `IYFifBJ9lH8` | no | 실내 트랙. 라벨 의심(투구로 보임) |
| `IeDin6oB-IY` | no | — |
| `LXjM7nBZcak` | no | — |
| `LhD_fnHt_xg` | no | 네트 뒤 원거리 |
| `N5zWQkoLM3M` | no | — |
| `O2GSaYqH8JY` | no | 공 줍는 코치를 피사체로 잡음 |
| `V_whuvMjg_8` | yes | 세로영상 실내케이지, 스윙 여러 번 |
| `X6dC9pu5H3k` | no | — |
| `ZS-wgeg2qkI` | maybe | — |
| `Zp9aDp2YTBw` | no | — |
| `bh6Cvz2orzQ` | maybe | — |
| `cDRi9AzrapA` | no | 방송 교습영상, 컷 편집 + 반복 |
| `e8uB0GZsVOQ` | no | — |
| `g_wHimPF9o8` | no | — |
| `h_3LqD2Pl-E` | no | 앞 33프레임이 타이틀 카드(사람 없음) |
| `hz-SpF35_BE` | no | — |
| `idueIYDAbZc` | no | — |
| `sGKeqfxwq5E` | yes | 경기 영상, 타자·포수·심판 |
| `sYl2jCqsSKo` | no | — |

27건 중 `usable_for_phase_B = yes` 였던 것: `Atzrde5uGcM`, `V_whuvMjg_8`, `sGKeqfxwq5E`

판독이 기존 기록보다 **엄격했다**는 뜻이다. 판독자가 실제 이미지를 봤고
`usable_for_phase_B`는 다른 목적(Phase B 투입 가능성)으로 매긴 값이라,
어긋남 자체가 오류는 아니다.
