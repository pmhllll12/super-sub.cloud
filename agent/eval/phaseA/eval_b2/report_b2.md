## 3. Pose quality
  정의: mean(17 keypoint confidences) from ViTPose
  valid_joint_count: count(conf >= 0.3)  (관측용, production 임계값 아님)
  model: usyd-community/vitpose-base-simple  det_threshold: 0.5  max_batch: 24
  총 후보: 20677   총 시간 6.1분
  clip당 mean 8.8s  median 6.2s
  OOM 발생: 0회
  후보밀도 ~2/frame   clip 17개  20 ms/cand
  후보밀도 2-4/frame  clip  5개  18 ms/cand
  후보밀도 4+/frame   clip 17개  16 ms/cand

## 4. Main result
| Metric | Baseline | A-geometry | B-geometry | A-pose | B-pose |
|---|---:|---:|---:|---:|---:|
| Correct | 68 | 82 | 83 | 83 | 85 |
| Wrong | 29 | 15 | 14 | 14 | 12 |
| Wrong-person rate | 29.9% | 15.5% | 14.4% | 14.4% | 12.4% |
| Accuracy | 70.1% | 84.5% | 85.6% | 85.6% | 87.6% |
| Multi-cand correct | 35/64 | 49/64 | 50/64 | 50/64 | 52/64 |
| Multi-cand wrong-rate | 45.3% | 23.4% | 21.9% | 21.9% | 18.8% |
| Multi-cand accuracy | 54.7% | 76.6% | 78.1% | 78.1% | 81.2% |
| Clip-level accuracy | 61.1% (22/36) | 75.0% (27/36) | 77.8% (28/36) | 77.8% (28/36) | 83.3% (30/36) |
| Switching median | 1.3% | 1.3% | 0.0% | 1.3% | 0.0% |
| Switching mean | 5.7% | 4.3% | 1.3% | 4.2% | 1.4% |
| Clips >10% switching | 9/39 | 5/39 | 1/39 | 6/39 | 1/39 |

## 5. Error transition
  Baseline     -> A-geometry    recovery 17   regression  3   net +14
  Baseline     -> B-geometry    recovery 18   regression  3   net +15
  Baseline     -> A-pose        recovery 19   regression  4   net +15
  Baseline     -> B-pose        recovery 20   regression  3   net +17
  A-geometry   -> A-pose        recovery  2   regression  1   net +1
  B-geometry   -> B-pose        recovery  2   regression  0   net +2
  A-pose       -> B-pose        recovery  4   regression  2   net +2
  A-geometry   -> B-geometry    recovery  4   regression  3   net +1

## 6. Continuity 고착 분석 (continuity 구간별)
  [B-geometry]
    <0.3      n=  2  correct   1  wrong   1  (50.0% wrong)   A 대비 regression 0
    0.3-0.6   n=  2  correct   2  wrong   0  ( 0.0% wrong)   A 대비 regression 0
    0.6-0.8   n=  7  correct   6  wrong   1  (14.3% wrong)   A 대비 regression 1
    >=0.8     n= 86  correct  74  wrong  12  (14.0% wrong)   A 대비 regression 2
  [B-pose]
    <0.3      n=  2  correct   1  wrong   1  (50.0% wrong)   A_pose 대비 regression 0
    0.3-0.6   n=  2  correct   2  wrong   0  ( 0.0% wrong)   A_pose 대비 regression 0
    0.6-0.8   n=  7  correct   7  wrong   0  ( 0.0% wrong)   A_pose 대비 regression 0
    >=0.8     n= 86  correct  75  wrong  11  (12.8% wrong)   A_pose 대비 regression 2

## 7. Centrality failure analysis
  GT centrality 분포 (n=96): p10 0.55 median 0.77 p90 0.91  min 0.20
  GT가 중앙성 1위인 대상: 67/96 (70%)
  GT 중앙성 순위 분포: {1: 67, 2: 18, 3: 2, 4: 2, 5: 3, 6: 1}
  후보 2개 이상 중 GT가 중앙성 1위가 아닌 대상: 29/57
  clip@ratio               cand  GT cen max cen rank  base/A/B/Ap/Bp
  3R1kvNrGJK0@0.50            7   0.205   0.669    7  XXXXX
  LXjM7nBZcak@0.20            7   0.253   0.572    7  OOOOO
  LXjM7nBZcak@0.50            8   0.276   0.863    8  XXXXX
  X6dC9pu5H3k@0.80            5   0.417   0.671    5  XXXXO
  ZS-wgeg2qkI@0.50            8   0.459   0.794    6  OOOOO
  ZS-wgeg2qkI@0.20            8   0.476   0.776    5  OOOOO
  ZS-wgeg2qkI@0.80            9   0.502   0.801    5  OOOOO
  sGKeqfxwq5E@0.50            7   0.577   0.706    2  XXXXX
  idueIYDAbZc@0.80            6    0.58   0.662    3  XOXOO
  5-jBTNp5IQA@0.50            5   0.585   0.859    4  OXOXO
  LhD_fnHt_xg@0.80            2   0.666   0.868    2  OXXXX
  6hrcRyIYTrA@0.50           10   0.667   0.699    2  OOOOO
  LhD_fnHt_xg@0.50            2   0.671   0.878    2  OXXXX
  Atzrde5uGcM@0.50           12   0.675   0.839    4  OOOOO
  [GT centrality < median] n=28
      Baseline     14/28 = 50.0%
      A-geometry   16/28 = 57.1%
      B-geometry   18/28 = 64.3%
      A-pose       18/28 = 64.3%
      B-pose       20/28 = 71.4%
  [GT centrality >= median] n=29
      Baseline     15/29 = 51.7%
      A-geometry   27/29 = 93.1%
      B-geometry   26/29 = 89.7%
      A-pose       26/29 = 89.7%
      B-pose       26/29 = 89.7%

## 독립성 민감도 (known 4클립 제외)
  Baseline     전체 68/97=70.1%  제외 59/86=68.6%   multi 35/64=54.7%  제외 31/58=53.4%
  A-geometry   전체 82/97=84.5%  제외 72/86=83.7%   multi 49/64=76.6%  제외 44/58=75.9%
  B-geometry   전체 83/97=85.6%  제외 73/86=84.9%   multi 50/64=78.1%  제외 45/58=77.6%
  A-pose       전체 83/97=85.6%  제외 73/86=84.9%   multi 50/64=78.1%  제외 45/58=77.6%
  B-pose       전체 85/97=87.6%  제외 75/86=87.2%   multi 52/64=81.2%  제외 47/58=81.0%

## Known clips
  3R1kvNrGJK0    0.20 cand=11 GT=   0 picks=1/0/0/0/0    XOOOO
  3R1kvNrGJK0    0.50 cand= 7 GT=   1 picks=0/0/0/0/0    XXXXX
  3R1kvNrGJK0    0.80 cand= 6 GT=null picks=0/0/0/0/0    -----
  O2GSaYqH8JY    0.20 cand= 1 GT=   0 picks=0/0/0/0/0    OOOOO
  O2GSaYqH8JY    0.50 cand= 1 GT=   0 picks=0/0/0/0/0    OOOOO
  O2GSaYqH8JY    0.80 cand= 2 GT=   0 picks=0/0/0/0/0    OOOOO
  gg5xRWjw3f8    0.20 cand= 1 GT=   0 picks=0/0/0/0/0    OOOOO
  gg5xRWjw3f8    0.50 cand= 1 GT=   0 picks=0/0/0/0/0    OOOOO
  gg5xRWjw3f8    0.80 cand= 1 GT=   0 picks=0/0/0/0/0    OOOOO
  xMIUw5mi3Eo    0.20 cand= 8 GT=   0 picks=0/0/0/0/0    OOOOO
  xMIUw5mi3Eo    0.50 cand= 8 GT=   0 picks=0/0/0/0/0    OOOOO
  xMIUw5mi3Eo    0.80 cand= 4 GT=   0 picks=0/0/0/0/0    OOOOO
