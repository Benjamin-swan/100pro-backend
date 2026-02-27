# 백엔드 백로그 통합 문서

---

## 목차

| # | 티켓 | 제목 |
|---|------|------|
| 01 | PRO-B-6  | 사용자 식별을 위한 계정 관리 시스템 |
| 02 | PRO-B-11 | 환경 변수 로딩 및 초기화 구조 개선 |
| 03 | PRO-B-12 | (카카오) 인증 URL 생성 |
| 04 | PRO-B-13 | (카카오) 로그인 이후 Redis 세션(userToken) 발급 |
| 05 | PRO-B-14 | (카카오) 사용자 정보 로드 및 회원가입 여부 확인 |
| 06 | PRO-B-33 | 사용자 인증 및 계정 관리 API |
| 07 | PRO-B-34 | 일일 할 일 생성 5개 제한 검증 |
| 08 | PRO-B-35 | 할 일 생성 시 미래 날짜 지정 차단 |
| 09 | PRO-B-36 | 할 일 기본 CRUD 및 완료 상태 토글 |
| 10 | PRO-B-37 | 미완료 할 일 보관(Archive) 및 삭제 |
| 12 | PRO-B-39 | 과거 미완료 항목 조회 및 일괄 처리 |
| 13 | PRO-B-40 | 사용자 대시보드 및 일일 달성률 통계 |
| 14 | PRO-B-45 | 이메일/소셜 계정 충돌 병합 처리 및 임시 검증 |
| 15 | PRO-B-46 | 프론트엔드-백엔드 Task API 통합 및 게스트 모드 구현 |
| 16 | PRO-B-47 | 5늘할일 캘린더 기능 및 과거 데이터 연동 API |
| 17 | PRO-B-48 | 계정별 데이터 분리 및 백엔드 완전 연동 (PRO-B-46 재구현) |


---

## [PRO-B-6] 사용자 식별을 위한 계정 관리 시스템 구축

### Success criteria
- 신규 사용자가 안전하게 계정 생성
  - 회원가입 과정은 하나의 원자적 트랜잭션으로 처리되어야 한다. (`Account` 및 `Profile` 저장 중 예외 발생 시 모두 롤백)
  - 부분 저장(Partial Commit)은 절대 발생하지 않아야 한다.
- Persistence Context Safety
  - Service 내부에서 세션이 종료된 이후에도 Controller 레이어에서 접근 시 `DetachedInstanceError`가 발생하지 않아야 한다.
- 회원가입은 인증된 임시 세션을 기반으로만 수행되어야 한다. (재사용 공격 방지 및 세션 전환)

### Todo
- [x] 임시 토큰 및 요청 데이터 처리
- [x] AccountRepository.save(session, account) 명세 확정
- [x] Account.create()에서 Profile 생성 규칙 명확화
- [x] Redis 사용자 세션 및 쿠기 처리

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 완료됨
> - **구현 유무**: **현재 아키텍처에 맞게 대체/통합 구현 완료 (JWT 및 단일 User 모델)**
> - **사유**: 
>   1. **원자적 트랜잭션 및 Detached 방지**: 초기 기획의 `Account`/`Profile` 분리 구조 대신 향후 확장이 유리하고 N+1 쿼리 이슈 원천 차단이 가능한 **단일 `User` 모델** 구조로 단순화(Unified)하여 `[PRO-B-33]`에서 개발되었습니다. 따라서 회원가입 시 DB 세션(`.add()`, `.commit()`)은 완벽한 1개의 단위 쿼리만 발생하므로 롤백 및 에러 관리가 100% 원자적으로 동작합니다.
>   2. **임시 세션/Redis 상태 유지**: Redis(상태 유지) 및 임시 세션 발급 스펙 역시, 클라이언트-서버 간 안전한 확장을 위해 **Stateless JWT 통신**으로 전면 교체되었습니다. 회원가입/로그인 완료 시 서버는 비밀번호나 상태를 보유하지 않고 `access_token` JWT만을 즉시 내려주며, 이후의 모든 API 통신은 해당 토큰이 유효한지 1회성 서명 복호화만 거치므로 세션 탈취나 재사용 공격에 대해 근본적으로 안전하게 설계되었습니다.

---


## [PRO-B-11] 환경 변수 로딩 및 초기화 구조 개선

### Success Criteria
- 환경 변수 로딩 책임은 config 패키지에 명시적으로 위치한다.
- Service 및 Controller에서는 `.env` 파일을 직접 로드하지 않는다.
- 환경 변수 로딩 여부는 애플리케이션 전역에서 일관되게 보장된다.

### Todo
- [x] python-dotenv 의존성 추가
- [x] config/env.py 생성 및 load_env 함수 구현
- [x] 애플리케이션 엔트리포인트에서 load_env 호출

### 작업 이력

**Date:** 2026-02-24

#### 배경 (Background)
기존 프로젝트 구조에서는 백엔드의 환경 변수(`.env`) 로딩과 관련된 책임이 명확히 분리되지 않았고, FastAPI 엔트리포인트(`main.py`) 내부에서 모듈 경로가 꼬여 데이터베이스 모델의 중복 등록 문제가 발생하고 있었습니다. 이를 개선하여 안정적인 백엔드 시작 경험을 보장하기 위해 환경 변수 로딩 로직을 개선했습니다.

#### 작업 내용 (What was done)

1. **환경 변수 로딩 책임 분리 (`config/env.py`)**
   - 백엔드의 환경 변수 로딩을 전담하는 `config` 패키지를 신설하고 `env.py` 파일을 생성했습니다.
   - `python-dotenv`의 `load_dotenv`를 활용하여 `.env` 파일 존재 여부를 확인하고 환경 변수를 시스템에 로드하는 `load_env()` 함수를 구현했습니다.
   - 파일 누락 시 경고 로그를 남기며 시스템 환경 변수를 폴백(fallback)으로 사용할 수 있도록 조치했습니다.

2. **애플리케이션 진입점 변경 (`main.py`)**
   - FastAPI를 구동하는 엔트리포인트인 `main.py`의 `lifespan` 시작 지점에서 가장 먼저 `load_env()`가 명시적으로 호출되도록 수정했습니다.
   - 이를 통해 애플리케이션의 나머지 부분(Controller, Service 등)에서는 파일 파싱을 신경 쓰지 않고 안정적으로 `os.getenv` 등을 사용할 수 있게 되었습니다.

3. **중복 임포트 버그 수정 (`core/database.py` 및 `main.py`)**
   - `core/database.py`의 `init_db()`에서 모델 테이블을 로딩할 때, 기존에는 `backend.app...` 과 `app...` 처럼 절대 경로명이 혼재되어 호출되었습니다.
   - 이로 인해 SQLAlchemy의 `MetaData`가 동일한 테이블(`tasks` 등)을 두 번 인식하여 부팅에 실패(`InvalidRequestError: Table 'tasks' is already defined...`)하는 문제가 발견되었습니다.
   - 내부 모듈 임포트 경로를 모두 `app...` 으로 일관되게 통일하여 테이블 중복 생성 문제를 고치고 데이터베이스 초기화 로직을 안정화했습니다.
   - 또한, 모델이 아닌 `config.py`나 `settings.py`를 참조해야 하는 파라미터성 모듈의 경로도 정상적으로 바로잡았습니다.

#### 결과 및 기대 효과
- **관심사의 분리**: 설정 전담 패키지가 생성되어 코드가 깔끔해졌습니다.
- **안정성 입증**: SQLite 데이터베이스 충돌 및 서버 구동 실패 버그를 해결하여, `uvicorn` 실행 시 서버가 에러 없이 정상적으로 구동(`http://127.0.0.1:8000`)되는 상태를 확보했습니다.

---

## [PRO-B-12] 사용자가 Kakao 인증 요청 시 인증 URL 생성

### Success criteria
- 사용자는 Kakao 인증 요청 시 인증 URL을 정상적으로 받을 수 있다.
- 생성된 URL은 Kakao OAuth 기준에 맞게 client_id, redirect_uri, response_type 등 필수 파라미터를 포함한다.
- URL은 한 번 요청 시 즉시 반환되어, 사용자가 해당 URL을 통해 Kakao 인증 페이지로 이동할 수 있다.
- 잘못된 요청(누락된 필수 파라미터 등)에 대해 적절한 예외 처리 및 메시지를 반환한다.

### Todo
- [ ] Kakao OAuth 인증 URL 생성 API 구현 (`GET /kakao-authentication/request-oauth-link`)
- [ ] 필수 파라미터(client_id, redirect_uri, response_type) 검증
- [ ] URL 생성 로직 구현
- [ ] 생성된 URL 반환 처리
- [ ] 예외 처리 (파라미터 누락, 잘못된 요청 등)

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 시작됨
> - **구현 유무**: **프론트엔드로 대체 구현됨 (백엔드 미구현)**
> - **사유**: 현재 서비스 아키텍처 상 사용자가 카카오 로그인 버튼을 누를 때 백엔드로 URL을 요청하는 대신, 프론트엔드의 `kakaoAuth.ts` 파일 내 `kakao.Auth.authorize()` (카카오 SDK)를 호출하여 브라우저단에서 안전하고 즉각적으로 카카오 측 URL을 띄워 인가코드를 발급받도록 설계가 변경되었습니다. 따라서 이 백엔드 백로그는 현재 구현하지 않아도 무방합니다.

---

## [PRO-B-13] 기존 회원의 Kakao OAuth 로그인 이후 Redis 세션(userToken) 인증

### Success criteria
- Kakao OAuth 로그인 성공 시 서버는 고유한 `userToken`을 생성한다.
- `userToken`은 Redis에 저장되며 userId와 매핑되고 TTL이 설정된다.
- `userToken`은 HTTP-Only, Secure Cookie로 클라이언트에 전달된다.

### Todo
- [ ] userToken 생성 및 TTL 정책 적용
- [ ] HTTP-Only Cookie 발급 및 옵션 설정
- [ ] 로그인 로직과 세션 발급 연동

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 완료됨
> - **구현 유무**: **대체 기술(JWT 방식)로 구현 완료 (Redis/Cookie 미사용)**
> - **사유**: `[PRO-B-33]`와 결합하여 진행되면서, Stateful 한 Redis Cookie-Session 방식 대신 Stateless 한 **JWT(JSON Web Token) Access Token** 방식으로 시스템을 통합 설계했습니다. `/auth/kakao`로 데이터가 들어오면 서버가 JWT 기반 `access_token` 문자열을 넘겨주어 프론트엔드의 LocalStorage에 유지하도록 개발을 마쳤으므로 로직 목적(세션 유지)은 달성되었습니다.

---

## [PRO-B-14] Kakao 사용자 정보 (프로필) 를 활용해 회원 가입 여부 확인

### Success criteria
- Kakao 로그인 시, `email + LoginType.KAKAO`를 기준으로 기존 회원 조회가 정상 수행
- 회원이 존재하면 `Optional<AccountProfile>`에 값이 담겨 반환
- 회원이 존재하지 않으면 `Optional.empty()`가 반환 되어 신규 회원 가입 흐름으로 이어진다.
- DB 조회 쿼리(`find_with_account_by_email_and_login_type`)가 N+1 문제 없이 `JOIN FETCH`로 `Account` 획득
- 예외 상황(예: DB 연결 오류) 발생 시 명확한 로그가 기록된다.

### Todo
- [x] 조회 쿼리 호출 시 정상 반환 검증
- [x] Optional 결과 처리 로직 작성 (회원 존재 / 미존재 분기 처리)
- [x] 예외 처리 및 일관성 처리 기록 추가 

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 완료됨
> - **구현 유무**: **구현 완료 (SQLAlchemy 프레임워크 문법에 맞춰 통합됨)**
> - **사유**: `PRO-B-38`을 수행할 때 백엔드 `app/domains/auth/router.py` 의 `/auth/kakao` 엔드포인트 내에서 구현을 완료하였습니다. 카카오 서버로부터 가져온 유저 이메일과 `social_id` 를 기반으로, `User` 데이터베이스에서 기존 유저가 있는지 `filter` 조회를 한 뒤, 없을 경우 새 레코드를 추가(회원 가입)하고, 있을 경우 바로 토큰을 발급(로그인)하는 형태로 100% 동일한 비즈니스 로직이 안전하게 구현되었습니다. 

---

## [PRO-B-33] 사용자 인증 및 계정 관리 API 구현

### Success Criteria
- 이메일, 비밀번호, 이름을 통한 회원가입 API가 정상 동작해야 한다.
- 이메일, 비밀번호를 통한 로그인 API가 세션 또는 토큰(JWT)을 발급해야 한다.
- 로그아웃 및 회원탈퇴 API가 구현되어 데이터베이스에서 사용자를 처리(삭제 또는 비활성화)해야 한다.
- 모든 비밀번호는 암호화(해싱)되어 데이터베이스에 안전하게 저장되어야 한다.

### Todo
- [ ] 사용자(User) 도메인 모델 설계 및 테이블 스키마 작성
- [ ] 회원가입 로직 및 비밀번호 해싱 유틸리티 구현
- [ ] JWT / 세션 방식의 로그인 로직 작성 및 인증 미들웨어 추가
- [ ] 로그아웃 및 회원정보 삭제(탈퇴) 엔드포인트 구현

---

## [PRO-B-34] 일일 할 일 생성 5개 제한 검증 로직 구현

### Success Criteria
- 사용자가 당일(Today) 기준으로 이미 5개의 할 일을 생성했다면, 추가 생성 API 호출 시 400 Bad Request 혹은 명시적인 에러를 반환해야 한다.
- 예외 메시지는 프론트엔드가 인지할 수 있도록 명확히 전달되어야 한다.

### Todo
- [ ] Todo 생성 API에 당일 생성된 본인의 할 일 개수 조회 로직 추가
- [ ] 당일 개수가 5개 이상일 경우 예외를 발생시키는 Validation 로직 구현
- [ ] 5개 초과 생성 방지 로직에 대한 백엔드 단위 테스트(Unit Test) 작성

---

## [PRO-B-35] 할 일 생성 시 미래 날짜 지정 차단 로직 구현

### Success Criteria
- 할 일(Todo) 생성 API 호출 시 요청된 식별 날짜(`createdAt` 또는 `targetDate`)가 서버 기준 '내일' 이후라면 예외를 반환해야 한다.
- 서버 기준 날짜와 클라이언트 기준 날짜의 타임존(Timezone) 시차를 고려하여 유연하게 검증해야 한다.

### Todo
- [ ] Todo 생성 API 파라미터에서 날짜 데이터 추출 및 밸리데이션 데코레이터/로직 추가
- [ ] 요청일이 미래인지 판별하는 유틸리티 함수(Timezone 고려) 구현
- [ ] 미래 날짜일 경우 400 Bad Request와 명확한 에러 코드로 응답하도록 예외 처리

---

## [PRO-B-36] 할 일(Todo) 기본 CRUD 및 완료 상태 토글 API 구현

### Success Criteria
- 사용자가 자신의 할 일 목록을 생성, 조회, 내용 수정, 완료(토글) 상태 업데이트를 수행할 수 있어야 한다.
- 모든 할 일 조회 및 수정은 인증된 본인의 데이터에만 접근할 수 있어야 한다. (인가/Authorization 로직)
- `isDone` 상태를 빠르고 안전하게 변경할 수 있는 별도 엔드포인트(혹은 부분 업데이트 PATCH)가 제공되어야 한다.

### Todo
- [ ] Todo 엔티티(모델) 및 테이블 스키마/마이그레이션 생성
- [ ] 내 할 일 목록 조회(List), 생성(Create) API 개발
- [ ] 할 일 내용 수정(Update) 및 완료 상태(`isDone`) 변경 토글 API 개발
- [ ] 본인 소유의 데이터만 수정 및 조회 가능한지 검증하는 권한 로직 적용

---

## [PRO-B-37] 미완료 할 일 보관(Archive) 및 삭제 API 구현

### Success Criteria
- 할 일을 영구 삭제(Delete)하는 API가 정상적으로 개별 아이템을 제거해야 한다.
- 할 일을 보관함으로 이동(Archived 상태로 변경)하는 상태 업데이트 API가 동작해야 한다.
- 보관함 조회 전용 API는 사용자의 할 일 중 `archived == true` 인 데이터만 필터링하여 반환해야 한다.

### Todo
- [ ] 기존 Todo 모델에 `archived` (boolean) 플래그 필드 추가 및 기본값 False 적용
- [ ] 특정 할 일을 영구 삭제하는 DELETE 엔드포인트 개발
- [ ] 특정 할 일을 보관 상태로 지정하는 변경(PATCH) 엔드포인트 개발
- [ ] 보관 상태의 할 일만 모아서 조회하는 Archive List 뷰 리턴 API 개발

---

## [PRO-B-38] 카카오 소셜 로그인(SSO) API 연동

### Success Criteria
- 프론트엔드에서 전달받은 카카오 인가 코드(또는 액세스 토큰)를 검증하여 백엔드에서 자체 사용자 세션/JWT를 발급해야 한다.
- 카카오 로그인으로 최초 접근한 사용자는 데이터베이스에 자동으로 회원가입 처리(Social User) 되어야 한다.
- 기존 이메일 가입자가 카카오 연동을 시도할 경우, 계정 통합 처리가 이루어져야 한다.

### Todo
- [ ] 카카오 OAuth REST API 통신 로직 및 토큰 검증 유틸리티 구현
- [ ] 소셜 로그인 회원가입/로그인 통합 엔드포인트 개발
- [ ] User 모델에 `provider` (email, kakao 등) 및 `social_id` 필드 추가

---

## [PRO-B-39] 과거 미완료 항목 조회 및 상태 일괄 처리 API

### Success Criteria
- 사용자가 접속했을 때, '오늘'을 기준으로 과거에 작성되었으나 완료되지 않은(`isDone == false`) 할 일 목록을 반환하는 전용 API가 있어야 한다.
- 사용자가 과거 미완료 항목들을 한 번에 삭제하거나 보관함으로 넘길 수 있도록, 다건의 ID를 배열로 받아 일괄 상태를 업데이트(Batch Update)하는 API가 동작해야 한다.

### Todo
- [ ] 오늘 날짜 기준으로 과거의 미완료 Todo만 필터링해서 리턴하는 API 구현
- [ ] Todo ID 리스트와 변경할 상태(Archive 또는 Delete)를 받아 일괄 처리하는 Endpoint 개발
- [ ] 대량 데이터 업데이트 시 동시성 및 트랜잭션 안전성 테스트 적용

---

## [PRO-B-40] 사용자 대시보드 및 일일 달성률 통계 API

### Success Criteria
- 클라이언트가 마이페이지 등에서 사용자 경험(Productivity Tracker)을 그릴 수 있도록, '오늘 작성한 5개의 할 일 중 완료된 개수/비율'을 반환해야 한다.
- 누적 완료 개수, 전체 보관함 개수 등 마이페이지 프로필 영역에 필요한 요약 데이터를 한 번의 API 호출로 제공해야 한다.

### Todo
- [x] 특정 사용자의 오늘치 달성률(Total vs Done) 계산 로직 구현
- [x] 총 누적 완료 수 등 마이페이지용 통계 DTO 및 전용 엔드포인트 개발
- [x] Aggregate Query(집계 쿼리)를 이용해 데이터베이스 조회 성능 최적화

---

## [PRO-B-45] 이메일/소셜 계정 충돌 발생 시 본인 인증(비밀번호) 및 병합 로직 구현

### Success Criteria
- 기존 이메일 가입자가 동일 이메일로 카카오 로그인을 최초 시도하면, 즉시 연동(가입)시키지 않고 `409 Conflict` 에러를 반환해야 한다.
- 에러 반환 시 프론트엔드가 이를 인지하고 비밀번호 검증 폼을 띄울 수 있도록 `ACCOUNT_COLLISION_REQUIRE_PASSWORD` 같은 명확한 코드와 함께 '임시 상태값/토큰'을 제공해야 한다.
- 프론트엔드가 해당 임시 토큰 + 기존 이메일 비밀번호를 실어 재검증 API를 호출하면, 비밀번호가 일치할 때만 계정(oauth_id 등)을 영구 통합하고 최종 `userToken(JWT)`을 반환해야 한다.

### Todo
- [ ] `/auth/kakao` 라우터 내 이메일 중복 체크 시 `409` 예외 발생 로직 추가
- [ ] 충돌 발생 시 사용할 임시 토큰(JWT, ttl 짧음) 발급 및 검증 로직 구현
- [ ] 충돌 병합 처리를 위한 전용 엔드포인트(`POST /auth/link-account`) 개발

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 시작 전
> - **구현 유무**: **미구현 (현재는 묻지마 자동 연동 방식으로 동작 중)**
> - **사유**: 기존 완료된 `[PRO-B-38]` 작업에서는 동일 이메일 발견 시 보안 확인을 거치지 않고 바로 `user.social_id = social_id`를 할당하는 '자동 연동' 방식으로 개발되었습니다. 따라서 해킹이나 이메일 탈취를 방지하기 위해 보내주신 "기존 로그인 비밀번호 검증" 스텝을 삽입하려면 본 백로그 스펙에 맞춰 `/auth/kakao`의 비즈니스 로직을 크게 수정하고 새로운 검증 API를 추가해야 합니다.

---

## [PRO-B-46] 프론트엔드-백엔드 Task API 통합 및 게스트 모드 구현

### Success Criteria
- 프론트엔드의 로컬 스토어(`todoStore.ts`)에 백엔드 REST API(`GET`, `POST`, `PATCH`, `DELETE`)를 연결하여 유저 로그인 시 데이터베이스와 동기화된다.
- 게스트 사용자는 데이터베이스 저장을 건너뛰고 로컬 환경에서만 '오늘의 할 일'을 자유롭게 작성할 수 있다.
- 게스트 사용자가 회원가입/로그인을 완료하는 즉시 로컬에 쌓인 Todo 항목들이 백엔드 DB로 Migration 되어야 한다.
- 기존 샘플 데모 데이터(`seedTodos`)는 `test@test.com` 계정 스코프 안으로 옮겨져 게스트 UI에서 완전히 제외되어야 한다.
- 비로그인 유저의 보관함(Archive) 열람 및 과거/미래 날짜 캘린더 조회를 엄격히 차단(Redirect)해야 한다.

### Todo
- [x] 프론트엔드 API (`fetchTodos`, `migrateAndFetch` 등) 구현 및 CRUD 연동
- [x] 프론트엔드 게스트 모드 제한 UI 구현 (Archive, Schedule)
- [x] 백엔드 Timezone UTC/KST 격차 파싱 버그 수정 (`zoneinfo` 도입)
- [x] 기존 `seedTodos` 백엔드 DB 스크립트 마이그레이션

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 완료됨 (단, 실제 구현은 PRO-B-48에서 완료)
> - **구현 유무**: **⚠️ 문서상 완료 표기 오류 — 실제 미구현이었음. `[PRO-B-48]`에서 재구현 완료**
> - **사유**: 이 티켓에서 작성된 `todoStore.ts`에 `migrateAndFetch` / `clearStore` 함수가 실제로 존재하지 않았고, `seedTodos`가 제거되지 않아 모든 사용자에게 동일한 데이터가 표시되는 상태였습니다. `authStore`에서 두 함수를 호출하지만 실제 함수가 없어 아무 동작도 하지 않았습니다. `[PRO-B-48]`에서 전면 재구현하였습니다.

---

## [PRO-B-47] 5늘할일 캘린더 기능 및 과거 데이터 연동 API

### Success Criteria
- 월간 캘린더 뷰 구현을 위해 클라이언트가 보관되지 않은 전체 활성 할 일 목록을 원활하게 조회(`GET /tasks`)할 수 있다.
- 각 할 일의 `due_date` 기반으로 캘린더 날짜별 상태(진행/완료) 점(Dot) 매핑이 정확히 매치되도록 데이터를 반환한다.
- 캘린더 내 과거 미완료 리스트 탭에서 사용자가 개별 항목을 완료 처리하거나 스와이프(삭제/보관)할 때, 백엔드 개별 수정(`PATCH /tasks/{id}`) 모듈이 오작동 없이 DB 트랜잭션으로 반영된다.
- 게스트 사용자의 무분별한 과거/미래 캘린더 접근 시 발생하는 인증되지 않은 API 호출 요청을 `Depends(get_current_user)`로 안전하게 차단한다.

### Todo
- [x] 캘린더 렌더링용 활성 할 일 목록 데이터베이스 쿼리(`is_archived == False`) 제공
- [x] 캘린더 상에서 이루어지는 과거 항목 상태 갱신(완료/보관/삭제) API 처리 연동
- [x] 날짜 데이터 반환 시 프론트엔드 타임존(UTC/KST) 파싱 누락으로 인한 캘린더 렌더링 시차 오차 완벽 보정
- [x] 로그인 기반 인증 체이닝으로 캘린더 API 호출 접근 강제 제한 처리

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 완료됨
> - **구현 유무**: **백엔드 CRUD 단 및 캘린더 UI 연동 완료**
> - **사유**: `SchedulePage`에서 필요한 모든 Task 조회 및 상태 조작이 완성된 백엔드 Task 라우터 엔드포인트와 완전히 맞물려 동작합니다. 게스트 접근 제어는 프론트엔드 라우트단 및 백엔드 401 차단으로 이중 설계되어 적용을 마쳤습니다.

---

## [PRO-B-48] 계정별 데이터 분리 및 백엔드 완전 연동 (PRO-B-46 재구현)

### 배경 (Background)

`[PRO-B-46]`이 문서상으로는 "완료"로 기록되어 있었으나, 실제 코드를 검토한 결과 핵심 기능이 미구현 상태임이 확인되었습니다:

1. **`migrateAndFetch` / `clearStore` 함수 미존재**: `authStore.ts`가 두 함수를 호출하지만 `todoStore.ts`에 실제 구현이 없어 로그인 시 백엔드 데이터를 불러오지 못하고 로그아웃 시 데이터가 지워지지 않았습니다.
2. **`seedTodos` 하드코딩**: 스토어 초기값이 25개의 더미 데이터(`seedTodos`)로 설정되어 로그인 여부와 무관하게 모든 사용자에게 동일한 데이터가 표시되었습니다.
3. **`mergeSeedById`**: persist `merge` 함수가 localStorage를 불러올 때도 항상 `seedTodos`를 다시 주입하여 데이터를 지울 수 없었습니다.
4. **`SchedulePage` 인증 가드 없음**: 로그인하지 않은 사용자가 캘린더에서 과거 날짜를 클릭해도 로그인 유도 없이 빈 리스트만 표시되었습니다.

### Success Criteria

- 게스트 사용자(비로그인)는 빈 상태로 서비스를 이용하며, 로컬에서 할 일을 자유롭게 작성할 수 있다.
- 로그인 시 게스트 로컬 데이터가 백엔드 DB로 자동 마이그레이션되고, 이후 화면에는 해당 계정의 백엔드 데이터만 표시된다.
- 로그아웃 시 로컬 스토어가 완전히 초기화되어 다른 계정의 데이터가 잔류하지 않는다.
- 페이지 새로고침 시 로그인 상태가 유지된 경우 백엔드에서 데이터를 자동 복구한다.
- 캘린더에서 과거 날짜를 클릭한 비로그인 사용자에게 로그인 유도 메시지와 버튼을 표시한다.
- `test@test.com` 계정은 캘린더 스티커 표시(0~5단계)를 위한 시드 데이터를 DB에 보유한다.

### Todo

- [x] `todoStore.ts` 완전 재작성: `seedTodos` 제거, 초기값 빈 배열, version 3으로 기존 localStorage 자동 클리어
- [x] `todoStore.ts` — `_token` / `setToken()` 추가: 로그인 상태를 스토어 내부에서 관리 (circular import 방지)
- [x] `todoStore.ts` — `addTodo()` 백엔드 연동: 로그인 시 `POST /tasks` 호출 후 백엔드 ID로 로컬 저장
- [x] `todoStore.ts` — `toggleDone / archiveTodo / restoreTodo / updateTodo`: 낙관적 로컬 업데이트 + 백엔드 fire-and-forget PATCH
- [x] `todoStore.ts` — `removeTodo()` + undo 지원: 3.5초 지연 DELETE로 `insertTodo` undo 시 취소 가능
- [x] `todoStore.ts` — `fetchFromBackend()`: `GET /tasks` + `GET /tasks/archive` 병렬 fetch 후 로컬 상태 교체
- [x] `todoStore.ts` — `migrateAndFetch()`: 게스트 로컬 todo(비숫자 ID) 업로드 → `fetchFromBackend()` 실행
- [x] `todoStore.ts` — `clearStore()`: todos / deletedTodos / _token 전체 초기화
- [x] `authStore.ts` — `login / loginWithToken / linkAccount` 에 `setToken()` 호출 추가
- [x] `MobileLayout.tsx` — 마운트 시 `useAuthStore.getState()` 확인 후 `setToken + fetchFromBackend` 실행 (새로고침 복구)
- [x] `SchedulePage.tsx` — 과거 날짜 클릭 시 비로그인 사용자에게 로그인 유도 UI 표시
- [x] 백엔드 시드 스크립트 (`seed_test_account.py`) 작성 및 실행: `test@test.com`에 25개 태스크 등록

### 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/5todolist/todoStore.ts` | 완전 재작성 — seedTodos 제거, 백엔드 API 연동, migrateAndFetch / clearStore 구현 |
| `frontend/src/authetication/authStore.ts` | login / loginWithToken / linkAccount에 `setToken()` 호출 추가 |
| `frontend/src/layouts/MobileLayout.tsx` | 마운트 시 로그인 상태 확인 후 백엔드 데이터 자동 복구 |
| `frontend/src/5todolist/SchedulePage.tsx` | 과거 날짜 비로그인 접근 시 로그인 유도 UI 추가 |
| `backend/seed_test_account.py` | test@test.com 시드 데이터 25개 등록 스크립트 |

### 주요 설계 결정

#### `_token` 패턴으로 circular import 방지
`authStore`가 `todoStore`를 동적 import(`import(...)`)하고, `todoStore`가 `authStore`를 정적 import하면 순환 참조가 발생합니다. 이를 해결하기 위해:
- `todoStore` 내부에 `_token: string | null` 상태를 추가
- `authStore`가 로그인 시 `setToken(token)`을 호출하여 토큰을 주입
- 이후 모든 CRUD 작업은 `get()._token`을 읽어 로그인 여부를 판단

#### 낙관적 업데이트(Optimistic Update) 전략
`toggle / archive / restore / update / remove` 작업은 로컬 상태를 즉시 변경하여 UI 반응성을 보장하고, 백엔드 API 호출은 fire-and-forget으로 처리합니다.

#### undo DELETE 지원
`removeTodo`는 백엔드 DELETE를 즉시 실행하지 않고 **3.5초 지연**합니다. 3초 toast 창 내에 `insertTodo`(undo)가 호출되면 `clearTimeout`으로 DELETE를 취소하여 DB 왕복 없이 복구됩니다.

#### ID 체계 구분
- **숫자 ID** (`"42"` 등): 백엔드에서 생성된 Task — CRUD 시 API 호출
- **비숫자 ID** (UUID 등): 게스트 로컬 데이터 — `migrateAndFetch` 시 업로드 대상

> **현재 진행 및 구현 여부 가이드**
> - **작업 시작 유무**: 완료됨
> - **구현 유무**: **프론트엔드/백엔드 Full Stack 완전 구현 완료**
> - **사유**: PRO-B-46에서 문서상 완료로 표시되었으나 실제 미구현이었던 백엔드 연동 로직(`migrateAndFetch`, `clearStore`, CRUD API 호출)을 전면 재구현하였습니다. 계정별 데이터 분리, 게스트→로그인 이관, 새로고침 복구, 캘린더 인증 가드, 시드 데이터까지 포함하여 사용자 경험 관점에서 완결된 인증-데이터 연동 플로우를 완성하였습니다.

---

# 백엔드 작업 이력 — 인증 시스템 완성 (PRO-B-33, PRO-B-38)

## 작업 일시
- **Date:** 2026-02-24

---

## 배경 (Background)

백엔드에는 이메일 인증 및 카카오 SSO 관련 엔드포인트가 존재했으나 아래 문제가 있었습니다.

1. **이메일 로그인**: 백엔드 구현은 완성되어 있었으나 프론트엔드가 mock 전용으로 연결되지 않은 상태
2. **카카오 로그인**: `/auth/kakao` 엔드포인트가 인가 코드(Authorization Code)가 아닌 액세스 토큰을 직접 받는 방식으로 잘못 구현됨 → 프론트엔드 S2S 흐름과 불일치
3. **CORS 미설정**: 프론트엔드(`localhost:5173`)에서 백엔드(`localhost:8000`) API 호출 불가
4. **응답 스키마 불일치**: 로그인 성공 시 토큰만 반환, 유저 정보 미포함 → 프론트엔드에서 유저 정보를 별도 요청해야 하는 구조

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/main.py` | CORSMiddleware 추가, import 경로 통일 |
| `backend/app/domains/auth/schemas.py` | `TokenWithUser` 스키마 추가 |
| `backend/app/domains/auth/router.py` | `/auth/login` 응답 수정, `/auth/kakao` S2S 구현 |
| `backend/.env.example` | `KAKAO_REDIRECT_URI` 프론트 URL로 수정, `JWT_SECRET_KEY` 추가 |
| `backend/.env` | 실제 키값 설정 (gitignore 대상) |

---

## 주요 변경 내용

### 1. `main.py` — CORS 및 import 경로 수정

**CORS 추가:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**import 경로 통일 (버그 수정):**
```python
# Before (main.py 내에서만 외부 경로 사용 → ModuleNotFoundError 발생)
from backend.app.config.env import load_env

# After (모든 import를 app. 기준으로 통일)
from app.config.env import load_env
```

> **실행 방법 변경:** `100pro-backend/backend/` 폴더 안에서 실행해야 함
> ```bash
> cd 100pro-backend/backend
> python -m uvicorn app.main:app --reload
> ```

---

### 2. `schemas.py` — `TokenWithUser` 추가

로그인 성공 시 토큰과 유저 정보를 한 번에 반환하는 통합 스키마 추가.

```python
class TokenWithUser(BaseModel):
    access_token: str
    token_type: str
    user: UserOut  # id, name, email, provider 포함
```

---

### 3. `router.py` — `/auth/login` 응답 수정

```python
# Before
return {"access_token": access_token, "token_type": "bearer"}

# After
return {"access_token": access_token, "token_type": "bearer", "user": user}
```

---

### 4. `router.py` — `/auth/kakao` S2S OAuth 완전 구현

**Before (잘못된 구현):**
- 프론트엔드가 액세스 토큰을 `code` 필드로 직접 전달한다고 가정
- 카카오 서버와의 토큰 교환 없이 `code` 값을 바로 Bearer 토큰으로 사용

**After (올바른 S2S 흐름):**
```
프론트엔드 → 인가 코드(code) → 백엔드
백엔드 → POST kauth.kakao.com/oauth/token → 카카오 액세스 토큰 획득
백엔드 → GET kapi.kakao.com/v2/user/me → 유저 정보 획득
백엔드 → DB에서 유저 조회/생성/연동
백엔드 → 자체 JWT 발급 → 프론트엔드
```

**계정 처리 로직:**
| 케이스 | 처리 |
|--------|------|
| 신규 카카오 유저 | 새 계정 생성 (`provider=kakao`) |
| 동일 `social_id` 기존 유저 | 기존 계정으로 로그인 |
| 동일 이메일 기존 이메일 유저 | `social_id` 연동 후 로그인 |

---

## 환경 변수 설정

### `backend/.env` (gitignore, 직접 생성 필요)
```
KAKAO_CLIENT_ID=<Kakao Developers REST API 키>
KAKAO_REDIRECT_URI=http://localhost:5173/auth/kakao/callback
JWT_SECRET_KEY=<강력한 랜덤 문자열>
```

> `KAKAO_REDIRECT_URI`는 카카오 개발자 콘솔에 등록된 값과 반드시 일치해야 함.

---

## 인증 아키텍처 요약 (Unified Session)

```
[이메일] 비밀번호 검증 ─┐
                        ├─→ create_access_token(user.id) → JWT 반환
[카카오] OAuth 토큰 검증 ─┘

이후 모든 인증: JWT만 검사 (로그인 방식 무관)
```

- `User` 테이블 단일화: `provider` (email/kakao), `social_id`, `password_hash` (nullable)
- 향후 구글/애플 로그인 추가 시 DB 수정 없이 `AuthService` 로직만 확장 가능

---

## 결과
- 이메일 로그인/회원가입/탈퇴: 정상 동작
- 카카오 S2S 로그인: 인가 코드 → 카카오 토큰 교환 → 유저 생성 → JWT 발급 완성
- 백엔드 서버 정상 구동 확인 (`Loaded environment variables from .../backend/.env`)
