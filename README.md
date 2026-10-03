# Samsung Electronics DART Financial Dashboard

[![Dashboard](https://img.shields.io/badge/%F0%9F%94%97%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C%20%EB%B0%94%EB%A1%9C%EA%B0%80%EA%B8%B0-2F81F7?style=for-the-badge&logo=github&logoColor=white)](https://hsc-class02.github.io/ys_samsung/)

삼성전자(005930, DART corp_code `00126380`)의 사업·반기·분기보고서를 OpenDART API로 수집하고 주요 재무수치와 재무비율을 자동 계산해 GitHub Pages로 보여주는 프로젝트입니다.

## 자동화

- 매월 1일 자동 실행
- 코드 푸시 또는 수동 실행도 가능
- 정기보고서 접수정보와 DART 원문 링크 저장
- 2015년 이후 구조화 재무데이터 자동 갱신
- 결과를 `data/`에 저장하고 같은 실행에서 GitHub Pages로 배포

## 2010–2014 데이터

OpenDART의 단일회사 전체 재무제표 API(`fnlttSinglAcntAll`)는 2015년 이후 구조화 재무정보를 제공합니다. 따라서 2010–2014는 DART 공시검색 API로 사업/반기/분기보고서 접수정보를 보존하고, 구조화 금액은 별도의 원문/XBRL 수집이 필요한 구간으로 구분합니다.

## API Key

GitHub → **Settings → Secrets and variables → Actions → New repository secret**

- Name: `OPENDART_API_KEY`
- Value: OpenDART에서 발급받은 40자리 인증키

코드에 키를 직접 입력하지 않습니다. 이 프로젝트에서 사용하는 환경변수/Secret 이름은 **`OPENDART_API_KEY`** 입니다.

## 분석 지표

첨부된 「재무제표 및 재무비율 실무 가이드」를 기준으로 총자산, 현금, 매출채권, 재고, 유형자산, 총부채, 이자부차입금, 자본, 매출, 매출총이익, 판관비, 영업이익, 세전이익, 순이익, 지배주주순이익, EBITDA, CFO, CFI, CFF, CAPEX, FCF, 순차입금과 다음 비율을 계산합니다.

수익성: 매출총이익률, 영업이익률, 순이익률, EBITDA 마진, ROA, ROE, ROIC

유동성/안정성: 유동비율, 당좌비율, 부채비율, 자기자본비율, 차입금의존도, 이자보상배율, 순차입금/EBITDA

활동성/성장성: 총자산회전율, DSO, DIO, DPO, CCC, 매출증가율, CFO/순이익

시장주가가 필요한 PER/PBR/EV/EBITDA는 별도 시세 API가 필요하므로 기본 DART 대시보드 계산에서는 제외합니다.

## Domestic peer firms

삼성전자는 반도체·디스플레이·모바일·가전 등 복수 사업을 영위하므로 사업 중첩도가 높은 국내 상장사를 비교군으로 구성했습니다.

| Peer | Ticker | 비교 이유 |
|---|---:|---|
| SK hynix | 000660 | 메모리 반도체/HBM |
| LG Electronics | 066570 | TV·가전·스마트 디바이스 |
| LG Display | 034220 | 디스플레이 패널 |
| Samsung Electro-Mechanics | 009150 | 전자부품 |
| DB HiTek | 000990 | 파운드리/반도체 제조 |

Peer 선정은 공식 분류가 아니라 분석 목적의 비교군입니다.

## 파일 구조

- `data/financials.csv` — 표준화 재무데이터
- `data/metrics.json` — 대시보드 데이터
- `data/filings.json` — DART 정기보고서 접수정보
- `data/raw/YYYY/` — OpenDART 원시 응답
- `docs/` — GitHub Pages 화면
- `.github/workflows/monthly_dart_update.yml` — 수집·분석·Pages 자동화

## GitHub Pages

**Settings → Pages → Source = GitHub Actions**

대시보드: https://hsc-class02.github.io/ys_samsung/

저장소 About의 Website에도 위 주소를 넣으면 저장소 오른쪽에서 바로 접근할 수 있습니다.
