import type { SportCode } from '@/lib/market'

/**
 * 경기장 예약의 **자리 표시 데이터**.
 *
 * 🔴 전부 mock 이다. 계약(`fastapi/docs/api-contract.md`)에 구장 조회·예약은
 * 아직 없다 — 경기 기록의 `place` 는 자유 글자일 뿐 구장을 가리키는 테이블이
 * 아니다. `lib/market.ts` 와 같은 방식으로 **화면이 먼저 가고 그것이 규격의
 * 근거가 된다.**
 *
 * API 가 생기면 이 파일의 상수만 지우고 응답을 흘려 넣으면 된다.
 */

/** 코치 · 상품과 **같은 종목 코드**를 쓴다 — 화면마다 종목이 갈리면 안 된다. */
export type Venue = {
  id: string
  name: string
  region: string
  address: string
  sports: SportCode[]
  /** 목록 카드에 한 줄로 들어간다. */
  tagline: string
  /** 시간당 대여료(원). */
  pricePerHour: number
}

export const VENUES: Venue[] = [
  {
    id: 'gangnam-futsal-2',
    name: '강남 풋살장 2구장',
    region: '서울 강남구',
    address: '서울 강남구 테헤란로 411',
    sports: ['soccer'],
    tagline: '실내 인조 잔디, 야간 조명 완비',
    pricePerHour: 60000,
  },
  {
    id: 'jamsil-baseball-cage',
    name: '잠실 배팅 연습장',
    region: '서울 송파구',
    address: '서울 송파구 올림픽로 25',
    sports: ['baseball'],
    tagline: '실내 타격 케이지 6면, 피칭머신 상시 가동',
    pricePerHour: 40000,
  },
  {
    id: 'suwon-basketball-court',
    name: '수원 실내 농구코트',
    region: '경기 수원시',
    address: '경기 수원시 영통구 광교로 145',
    sports: ['basketball'],
    tagline: '풀코트 1면, 냉난방 완비',
    pricePerHour: 50000,
  },
  {
    id: 'ilsan-multi-sports-park',
    name: '일산 다목적 스포츠파크',
    region: '경기 고양시',
    address: '경기 고양시 일산동구 중앙로 1275',
    sports: ['soccer', 'basketball'],
    tagline: '실외 천연 잔디 구장 + 실내 코트 동시 운영',
    pricePerHour: 70000,
  },
]
