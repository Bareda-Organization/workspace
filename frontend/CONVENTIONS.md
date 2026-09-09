# 프론트엔드 코드 컨벤션

출처: [우아한테크코스 2025-ah-madda — ⚒️ FE 코드 컨벤션](https://github.com/woowacourse-teams/2025-ah-madda/wiki/%E2%9A%92%EF%B8%8F-FE-%EC%BD%94%EB%93%9C-%EC%BB%A8%EB%B2%A4%EC%85%98) (Version 1.1, 2025-07-14)
2026-09-10 사용자 지시로 이 저장소의 프론트엔드 규칙으로 채택.

**적용 범위 — 이 문서는 React/TypeScript 규칙이므로 `apps/academy-web`(Next.js) 에만 걸린다.**
`apps/parent-app` · `apps/manager-app` 은 Flutter/Dart 라 이 문서가 다루지 않는다
(Dart 규칙은 별도 문서 — 아직 미작성).

---

## 변수

| 규칙 | 근거 |
| --- | --- |
| `var` 금지 (`const` 우선, 재할당만 `let`) | 호이스팅이 예측 불가한 동작과 찾기 어려운 결함을 만든다 |
| 문자열 결합에 `+` 금지 — 템플릿 리터럴 | 가독성 |
| 상수는 대문자 스네이크 — `API_KEY` | |
| 약어 금지 | 코드 자체가 문서 역할을 해야 한다 |
| 자료구조 이름을 변수명에 넣지 않는다 — `fruitsArr` ✗ `fruits` ✓ | |
| 불리언은 `is` 접두 | |
| 순서가 바뀌는 목록을 `map` 할 때 진짜 고유한 `key` 를 준다 | 인덱스를 키로 쓰면 재정렬 시 상태가 엉뚱한 행에 붙는다 |

## 함수

- **화살표 함수만 쓴다.** `function` 키워드 금지 — `this` 바인딩 문제를 없애고 형태를 하나로 고정한다
  ```ts
  const validateEmail = (email: string) => /\S+@\S+\.\S+/.test(email);   // ✓
  function validateEmail(email) { … }                                     // ✗
  ```
- **동사 + 명사로 이름 짓는다.** `user` · `validation` · `data` ✗ → `getCurrentUser` · `validateEmail` · `fetchUserData` ✓
- **핸들러 접두**: 컴포넌트가 직접 실행하는 것은 `handle`, props 로 넘겨 받는 것은 `on`
  ```tsx
  const handleSubmitClick = () => { … };
  <ChildrenForm onSubmitClick={handleSubmitClick} />
  ```
- 중복되는 함수는 `utils` 폴더로 뺀다

## 컴포넌트

- **`PascalCase` 는 React 컴포넌트와 도메인 요소(폴더)에만.** 타입·`.d.ts`·`.ts` 파일은 `camelCase`
- 루트에 의미 없는 `div` 대신 **fragment(`<>`)** 를 쓴다 — 불필요한 DOM 노드가 CSS 레이아웃을 어긋나게 한다
- 자식이 없으면 **self-closing**, 닫는 슬래시 앞에 공백 한 칸
  ```tsx
  <Button onClick={onClick} />   // ✓
  <Button onClick={onClick}/>    // ✗
  ```

## 타입

- **`interface` 대신 `type` 으로 통일한다** — 유니온과 복합 타입을 다루기 쉽다
- **컴포넌트 props 타입은 그 컴포넌트 파일 맨 위**에 선언한다
- 그 밖의 타입은 전부 `types` 폴더에 둔다 (props 안에서 쓰는 배열·객체 타입 포함)
- 이름: props 는 `OOOProps`, API 응답은 `OOOResponseTypes`

## 스타일

- **의미 태그를 우선한다** — `section` · `article` · `main` · `aside`. `div` 는 구조용으로만
- **div 위계를 고정한다**: `Layout` → `Container` → `Wrapper` → `Style`
  ```tsx
  <div css={applicantLayout}>
    <div css={applicantContainer}>
      <div css={applicantWrapper}>…</div>
    </div>
  </div>
  ```
- 스타일 코드는 **`컴포넌트.styled.ts`** 로 분리한다
- **`@emotion/styled`** — 구조 수준의 컴포넌트 스타일링. 그렇게 만든 컴포넌트는 `Styled` 접두
  ```ts
  const StyledButton = styled.button``;
  ```
- **`@emotion/react`** — 조건부 스타일, css 객체 합성, 임시 스타일
- SVG 파일명은 `PascalCase` — `LeftArrow.svg`

---

## 디자인 시스템 이식 — Emotion 으로 통일 (2026-09-10 확정)

`frontend/design-system/` 의 컴포넌트 29개는 **인라인 `style={{}}` + CSS 변수**로 작성돼 있어
위 스타일 절과 충돌했다. **컨벤션 쪽을 따르고 29개를 Emotion 으로 이식**하는 것으로 정했다.

- **토큰(CSS 변수)은 그대로 둔다.** `design-system/tokens/*.css` 를 전역으로 링크하고
  `styled` 안에서 `var(--accent-primary)` 로 참조한다 — 값을 Emotion 객체로 복사하지 않는다.
  복사하면 디자인 시스템이 갱신될 때 따라오지 않는다
- **상태 색 매핑을 화면에서 직접 고르지 않는다** — `boarded` 그린 · `moving` 앰버 ·
  `missed` 레드 · `idle` 스톤은 `StatusPill` 안에 고정돼 있고, 세 제품이 같은 상태에
  같은 색을 쓰는 것이 디자인 시스템의 1번 원칙이다
- 이식본은 `src/shared/ui/` 에 두고 **원본(`design-system/`)은 읽기 전용 사본으로 유지**한다

---

## 디렉터리 — feature-first, 기능이 확장 단위

```
apps/academy-web/src/
├── app/                     Next.js App Router — 라우팅과 레이아웃만
│   ├── (auth)/              로그인 · 가입 · 승인 대기
│   ├── (staff)/             학원 관계자 (A-01~17)
│   └── (admin)/             메인 관리자 (O-01~07)
├── features/                도메인 하나 = 폴더 하나
│   └── <기능>/
│       ├── api/             그 기능의 엔드포인트 호출만
│       ├── components/
│       ├── hooks/
│       ├── types/
│       └── index.ts         공개 창구 — 밖에서는 이것만 import
├── shared/
│   ├── ui/                  디자인 시스템 Emotion 이식본 29개
│   ├── lib/                 http 클라이언트 · 토큰 저장 · 에러 코드 매핑
│   ├── hooks/
│   ├── styles/              design-system 토큰 링크 · 전역 스타일
│   └── types/
└── types/                   전역 타입
```

기능 이름은 `docs/FEATURE_SPEC` 의 도메인을 따른다 —
`auth` · `run` · `route` · `student` · `manager` · `bus` · `schedule` · `approval` ·
`notification` · `emergency` · `report` · `admin`.

### 지켜야 할 의존 방향

- **기능끼리 서로 import 하지 않는다.** 필요하면 `shared/` 로 올린다
  — 이것 하나가 무너지면 기능을 떼어낼 수 없게 되고, 그때는 이미 늦다
- 기능 밖에서는 **`features/<기능>/index.ts` 만** import 한다. 내부 파일을 직접 가리키지 않는다
- `app/` 은 라우팅과 조립만 한다. 화면 로직을 `app/` 에 두지 않는다
- `shared/` 는 어느 기능도 import 하지 않는다 (단방향)

### API 호출은 기능 안에서만

`shared/lib` 의 http 클라이언트가 **토큰 재발급(`API_SPEC §2.6`) · 멱등 키(`§1.7`) ·
에러 코드 매핑(`§8`)** 을 한곳에서 처리하고, 각 기능의 `api/` 는 그 클라이언트를 쓴다.
컴포넌트가 `fetch` 를 직접 부르지 않는다.
