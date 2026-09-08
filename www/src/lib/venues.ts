import type { SportCode } from '@/lib/market'

/**
 * 경기장 예약 데이터.
 *
 * 🔴 목록 자체는 **서울시 공공서비스예약**(yeyak.seoul.go.kr) 열린데이터
 * "서울시 체육시설 공공서비스예약 정보"에서 뽑은 실제 시설·시간대 스냅샷이다
 * (풋살장·축구장·야구장·농구장만, 서울 25개 자치구 소재로 한정 — 원본에
 * 섞여 있던 고양시·과천시 소재 시설은 제외했다). `open`(접수중 여부)은
 * **내려받은 시점 기준**이라 실시간이 아니다 — 매번 최신 상태를 보려면
 * `reserveUrl`로 들어가야 한다.
 *
 * 🔴 우리 시스템은 예약을 **중개하지 않는다.** `reserveUrl`은 서울시 공식
 * 예약 사이트로 나가는 외부 링크이고, 실제 결제·접수는 전부 그쪽에서
 * 이루어진다 — 예약 도메인(DB·결제)을 우리 쪽에 새로 만들지 않기로 한
 * 결정(미결 7번, 2026-09-04, 박민호)을 그대로 지킨다.
 *
 * 🔴 원본 CSV에 도로명주소·시간당 요금 컬럼이 없다 — `address`는 시설명을
 * 그대로 옮긴 것이고(실제 도로명주소 아님), 요금은 자유 텍스트 설명 안에만
 * 있어 안정적으로 파싱할 수 없어서 뺐다. 필요해지면 상세정보 파싱을 다시
 * 시도하거나 시설별로 수동 보완한다.
 *
 * API가 생기면 이 파일의 상수만 지우고 응답을 흘려 넣으면 된다.
 */

/** 코치 · 상품과 **같은 종목 코드**를 쓴다 — 화면마다 종목이 갈리면 안 된다. */
export type VenueSlot = {
  /** "평일 · 야간"처럼 요일·시간대 구분. 원본 서비스명에서 뽑았다. */
  label: string
  /** "09:00~17:00" 형식. */
  hours: string
  /** 스냅샷 시점의 접수중 여부 — 실시간 아님. */
  open: boolean
  /** 서울시 공식 예약 페이지로 가는 외부 링크. 실제 예약·결제는 여기서 이루어진다. */
  reserveUrl: string
}

export type Venue = {
  id: string
  name: string
  region: string
  /** 도로명주소가 아니라 원본 시설명 표기 그대로다 — 위 주석 참고. */
  address: string
  sports: SportCode[]
  /** 목록 카드에 한 줄로 들어간다. */
  tagline: string
  slots: VenueSlot[]
}

export const VENUES: Venue[] = [
  {
    id: 'mapo-01',
    name: '서울특별시 산악문화체험센터 난지천인조잔디축구장',
    region: '서울 마포구',
    address: '서울 마포구 · 서울특별시 산악문화체험센터 난지천인조잔디축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간',
        hours: '06:00~20:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S210401100008601453',
      },
    ],
  },
  {
    id: 'mapo-02',
    name: '서울특별시 산악문화체험센터 난지천 공원 풋살장',
    region: '서울 마포구',
    address: '서울 마포구 · 서울특별시 산악문화체험센터 난지천 공원 풋살장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '공휴일 · 주말 · 오후',
        hours: '07:20~17:30',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260811101457933943',
      },
      {
        label: '평일 · 오후',
        hours: '09:30~17:30',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260811100606264496',
      },
    ],
  },
  {
    id: 'songpa-01',
    name: '잠실종합운동장 풋살경기장',
    region: '서울 송파구',
    address: '서울 송파구 · 잠실종합운동장 풋살경기장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '토/일/공휴일 · 조기',
        hours: '07:00~09:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211141846313201',
      },
      {
        label: '평일 · 조기',
        hours: '07:00~09:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211145700584544',
      },
      {
        label: '토/일/공휴일 · 주간',
        hours: '09:00~17:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S241210100011131040',
      },
      {
        label: '평일 · 주간',
        hours: '09:00~17:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S241210100804518772',
      },
      {
        label: '토/일/공휴일 · 주간',
        hours: '09:00~19:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211140953971656',
      },
      {
        label: '평일 · 주간',
        hours: '09:00~19:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211143413155816',
      },
      {
        label: '토/일/공휴일 · 야간',
        hours: '17:00~23:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211135036404614',
      },
      {
        label: '평일 · 야간',
        hours: '17:00~23:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211142516076364',
      },
    ],
  },
  {
    id: 'songpa-02',
    name: '잠실종합운동장 제2풋살경기장',
    region: '서울 송파구',
    address: '서울 송파구 · 잠실종합운동장 제2풋살경기장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '토/일/공휴일 · 조기',
        hours: '07:00~09:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211154832527615',
      },
      {
        label: '평일 · 조기',
        hours: '07:00~09:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211162130632748',
      },
      {
        label: '토/일/공휴일 · 주간',
        hours: '09:00~17:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S241210101736010607',
      },
      {
        label: '평일 · 주간',
        hours: '09:00~17:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S241210102322341002',
      },
      {
        label: '평일 · 주간',
        hours: '09:00~19:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211161518896767',
      },
      {
        label: '토/일/공휴일 · 주간',
        hours: '09:00~19:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211152740425147',
      },
      {
        label: '토/일/공휴일 · 주간',
        hours: '09:00~21:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250113102713871746',
      },
      {
        label: '토/일/공휴일 · 야간',
        hours: '17:00~23:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211151711427451',
      },
      {
        label: '평일 · 야간',
        hours: '17:00~23:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250211160815177979',
      },
    ],
  },
  {
    id: 'yeongdeungpo-01',
    name: '영등포공원 풋살경기장',
    region: '서울 영등포구',
    address: '서울 영등포구 · 영등포공원 풋살경기장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260821160342456803',
      },
      {
        label: '공휴일 · 주간',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260821161514769084',
      },
      {
        label: '야간',
        hours: '18:00~20:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260821160925482469',
      },
    ],
  },
  {
    id: 'dongjak-01',
    name: '보라매공원 관리사무소. 인조잔디축구장',
    region: '서울 동작구',
    address: '서울 동작구 · 보라매공원 관리사무소. 인조잔디축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간',
        hours: '06:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251209095024061685',
      },
      {
        label: '토/일/공휴일 · 주간',
        hours: '06:00~18:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251209133301887008',
      },
      {
        label: '이용',
        hours: '16:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251209090453675144',
      },
      {
        label: '평일 · 야간',
        hours: '18:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251209100846015400',
      },
      {
        label: '토/일/공휴일 · 야간',
        hours: '18:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251209131904970635',
      },
    ],
  },
  {
    id: 'gangdong-01',
    name: '광나루한강공원 어린이야구장',
    region: '서울 강동구',
    address: '서울 강동구 · 광나루한강공원 어린이야구장',
    sports: ['baseball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122105737711565',
      },
    ],
  },
  {
    id: 'gangdong-02',
    name: '광나루한강공원 성인야구장',
    region: '서울 강동구',
    address: '서울 강동구 · 광나루한강공원 성인야구장',
    sports: ['baseball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일',
        hours: '08:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251121171853868569',
      },
      {
        label: '토/일/공휴일',
        hours: '08:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122083847480833',
      },
    ],
  },
  {
    id: 'gangdong-03',
    name: '광나루한강공원 축구장 2',
    region: '서울 강동구',
    address: '서울 강동구 · 광나루한강공원 축구장 2',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123131225200695',
      },
    ],
  },
  {
    id: 'gangdong-04',
    name: '광나루한강공원 농구장 1, 2',
    region: '서울 강동구',
    address: '서울 강동구 · 광나루한강공원 농구장 1, 2',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123111855916611',
      },
    ],
  },
  {
    id: 'gangdong-05',
    name: '광나루한강공원 축구장 3',
    region: '서울 강동구',
    address: '서울 강동구 · 광나루한강공원 축구장 3',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123131441208582',
      },
    ],
  },
  {
    id: 'gwangjin-01',
    name: '뚝섬한강공원 농구장 2',
    region: '서울 광진구',
    address: '서울 광진구 · 뚝섬한강공원 농구장 2',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123111027894852',
      },
    ],
  },
  {
    id: 'gwangjin-02',
    name: '뚝섬한강공원 농구장 3(장애인농구장)',
    region: '서울 광진구',
    address: '서울 광진구 · 뚝섬한강공원 농구장 3(장애인농구장)',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123110754815198',
      },
    ],
  },
  {
    id: 'gwangjin-03',
    name: '뚝섬한강공원 축구장 1',
    region: '서울 광진구',
    address: '서울 광진구 · 뚝섬한강공원 축구장 1',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123125544716776',
      },
      {
        label: '야간',
        hours: '17:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123130111480765',
      },
    ],
  },
  {
    id: 'gwangjin-04',
    name: '뚝섬한강공원 축구장 2',
    region: '서울 광진구',
    address: '서울 광진구 · 뚝섬한강공원 축구장 2',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123124116353220',
      },
      {
        label: '야간',
        hours: '17:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123125811658485',
      },
    ],
  },
  {
    id: 'gwangjin-05',
    name: '뚝섬한강공원 농구장 1',
    region: '서울 광진구',
    address: '서울 광진구 · 뚝섬한강공원 농구장 1',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123111230387929',
      },
    ],
  },
  {
    id: 'seocho-01',
    name: '잠원한강공원 축구장',
    region: '서울 서초구',
    address: '서울 서초구 · 잠원한강공원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123130842289825',
      },
    ],
  },
  {
    id: 'seocho-02',
    name: '잠원한강공원 농구장(1,2,3,4)',
    region: '서울 서초구',
    address: '서울 서초구 · 잠원한강공원 농구장(1,2,3,4)',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123101131914502',
      },
    ],
  },
  {
    id: 'seocho-03',
    name: '반포한강공원 축구장',
    region: '서울 서초구',
    address: '서울 서초구 · 반포한강공원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251119173904566376',
      },
    ],
  },
  {
    id: 'seocho-04',
    name: '반포한강공원 농구장(1,2)',
    region: '서울 서초구',
    address: '서울 서초구 · 반포한강공원 농구장(1,2)',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123100255050953',
      },
    ],
  },
  {
    id: 'yongsan-01',
    name: '이촌한강공원 축구장',
    region: '서울 용산구',
    address: '서울 용산구 · 이촌한강공원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123130354516934',
      },
    ],
  },
  {
    id: 'yongsan-02',
    name: '이촌한강공원 풋살경기장(옥수역하부)',
    region: '서울 용산구',
    address: '서울 용산구 · 이촌한강공원 풋살경기장(옥수역하부)',
    sports: ['soccer'],
    tagline: '무료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251119173155750607',
      },
    ],
  },
  {
    id: 'yeongdeungpo-02',
    name: '양화한강공원 축구장',
    region: '서울 영등포구',
    address: '서울 영등포구 · 양화한강공원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123130625642294',
      },
    ],
  },
  {
    id: 'mapo-03',
    name: '망원한강공원 농구장(1,2)',
    region: '서울 마포구',
    address: '서울 마포구 · 망원한강공원 농구장(1,2)',
    sports: ['basketball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123112746788237',
      },
    ],
  },
  {
    id: 'mapo-04',
    name: '망원한강공원 축구장',
    region: '서울 마포구',
    address: '서울 마포구 · 망원한강공원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~20:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251123123837907338',
      },
    ],
  },
  {
    id: 'mapo-05',
    name: '망원한강공원 야구장',
    region: '서울 마포구',
    address: '서울 마포구 · 망원한강공원 야구장',
    sports: ['baseball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '07:00~19:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122111311922757',
      },
    ],
  },
  {
    id: 'mapo-06',
    name: '난지한강공원 야구장 1',
    region: '서울 마포구',
    address: '서울 마포구 · 난지한강공원 야구장 1',
    sports: ['baseball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일',
        hours: '08:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122091737898557',
      },
      {
        label: '토/일/공휴일',
        hours: '08:00~19:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122092723682460',
      },
    ],
  },
  {
    id: 'mapo-07',
    name: '난지한강공원 야구장 2',
    region: '서울 마포구',
    address: '서울 마포구 · 난지한강공원 야구장 2',
    sports: ['baseball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일',
        hours: '08:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122103026141880',
      },
      {
        label: '토/일/공휴일',
        hours: '08:00~19:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251122104451968917',
      },
    ],
  },
  {
    id: 'guro-01',
    name: '계남근린공원 인조잔디축구장',
    region: '서울 구로구',
    address: '서울 구로구 · 계남근린공원 인조잔디축구장',
    sports: ['soccer'],
    tagline: '무료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260813170542380261',
      },
    ],
  },
  {
    id: 'guro-02',
    name: '안양천 체육시설 풋살경기장(구일역 하부)',
    region: '서울 구로구',
    address: '서울 구로구 · 안양천 체육시설 풋살경기장(구일역 하부)',
    sports: ['soccer'],
    tagline: '무료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '08:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S190522144836251426',
      },
      {
        label: '이용',
        hours: '08:00~24:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S250521110752802541',
      },
    ],
  },
  {
    id: 'seongdong-01',
    name: '중랑물재생센터 축구장',
    region: '서울 성동구',
    address: '서울 성동구 · 중랑물재생센터 축구장',
    sports: ['soccer'],
    tagline: '무료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '09:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251125110424950524',
      },
    ],
  },
  {
    id: 'yangcheon-01',
    name: '서서울호수공원',
    region: '서울 양천구',
    address: '서울 양천구 · 서서울호수공원',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간 · 오후',
        hours: '06:00~08:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260730153750703793',
      },
      {
        label: '평일 · 야간 · 주말 · 공휴일 · 오후',
        hours: '06:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260730160251089306',
      },
      {
        label: '평일 · 주간 · 오후',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260730154544287793',
      },
    ],
  },
  {
    id: 'mapo-08',
    name: '서울월드컵경기장 보조구장',
    region: '서울 마포구',
    address: '서울 마포구 · 서울월드컵경기장 보조구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간',
        hours: '06:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260108145359423543',
      },
      {
        label: '주간',
        hours: '09:00~17:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260219095038243778',
      },
      {
        label: '평일 · 야간',
        hours: '18:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260219094704927269',
      },
      {
        label: '야간',
        hours: '18:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260219095505315646',
      },
    ],
  },
  {
    id: 'gwangjin-06',
    name: '서울어린이대공원 잔디축구장',
    region: '서울 광진구',
    address: '서울 광진구 · 서울어린이대공원 잔디축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간',
        hours: '06:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260808161233310052',
      },
      {
        label: '공휴일 · 주간',
        hours: '06:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260808164953191603',
      },
      {
        label: '공휴일 · 야간',
        hours: '18:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260808165908950581',
      },
      {
        label: '평일 · 야간',
        hours: '20:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260808163903084513',
      },
    ],
  },
  {
    id: 'mapo-09',
    name: '서울월드컵경기장 풋살구장',
    region: '서울 마포구',
    address: '서울 마포구 · 서울월드컵경기장 풋살구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '02:00~12:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260904165157813628',
      },
      {
        label: '평일 · 야간',
        hours: '06:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251201134611894288',
      },
      {
        label: '야간',
        hours: '06:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251201135610838044',
      },
      {
        label: '평일 · 주간',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251201134005842787',
      },
      {
        label: '주간',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S251201135417916472',
      },
    ],
  },
  {
    id: 'guro-03',
    name: '고척스카이돔',
    region: '서울 구로구',
    address: '서울 구로구 · 고척스카이돔',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 야간',
        hours: '06:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260622104623512626',
      },
      {
        label: '야간',
        hours: '06:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260622131318569609',
      },
      {
        label: '평일 · 주간',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260622103128958995',
      },
      {
        label: '주간',
        hours: '08:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260622130237257613',
      },
    ],
  },
  {
    id: 'seocho-05',
    name: '인재개발원 축구장',
    region: '서울 서초구',
    address: '서울 서초구 · 인재개발원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '07:00~19:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S151223153002877769',
      },
    ],
  },
  {
    id: 'yangcheon-02',
    name: '신월야구공원',
    region: '서울 양천구',
    address: '서울 양천구 · 신월야구공원',
    sports: ['baseball'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '09:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260826150114243269',
      },
    ],
  },
  {
    id: 'seocho-06',
    name: '방배배수지체육공원',
    region: '서울 서초구',
    address: '서울 서초구 · 방배배수지체육공원',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '14:00~16:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S240911090012102103',
      },
      {
        label: '이용',
        hours: '14:00~18:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S240911090754004562',
      },
    ],
  },
  {
    id: 'mapo-10',
    name: '망원유수지 풋살장 망원유수지 풋살구장',
    region: '서울 마포구',
    address: '서울 마포구 · 망원유수지 풋살장 망원유수지 풋살구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '평일 · 주간',
        hours: '06:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260311134818986944',
      },
      {
        label: '주말 · 공휴일 · 주간',
        hours: '06:00~18:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260313152406066399',
      },
      {
        label: '평일 · 야간',
        hours: '18:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260311165902515011',
      },
      {
        label: '주말 · 공휴일 · 야간',
        hours: '18:00~22:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260521150329835813',
      },
    ],
  },
  {
    id: 'seocho-07',
    name: '양재근린공원 축구장',
    region: '서울 서초구',
    address: '서울 서초구 · 양재근린공원 축구장',
    sports: ['soccer'],
    tagline: '유료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '15:00~17:00',
        open: false,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S240911091215262623',
      },
    ],
  },
  {
    id: 'dongjak-02',
    name: '노들나루공원(노들배수지공원)',
    region: '서울 동작구',
    address: '서울 동작구 · 노들나루공원(노들배수지공원)',
    sports: ['soccer'],
    tagline: '무료 대관 · 서울시 공공서비스예약(yeyak.seoul.go.kr) 등록 시설',
    slots: [
      {
        label: '이용',
        hours: '06:00~22:00',
        open: true,
        reserveUrl: 'https://yeyak.seoul.go.kr/web/reservation/selectReservView.do?rsv_svc_id=S260821142440359268',
      },
    ],
  },
]
