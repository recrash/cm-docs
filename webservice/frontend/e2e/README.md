# Full Generation WebSocket E2E 테스트 가이드

이 문서는 Full Generation WebSocket 연결 E2E 테스트의 실행 방법과 테스트 시나리오에 대해 설명합니다.

## 테스트 개요

`full-generation-websocket.spec.ts`는 다음과 같은 Full Generation 워크플로우를 테스트합니다:

1. **HTML 파일 업로드 및 파싱**
2. **Full Generation 시작 및 CLI 커스텀 URL 호출**
3. **WebSocket 연결 및 진행상황 수신**
4. **완료 상태 및 결과 파일 검증**

## 사전 준비사항

### 1. 테스트 파일 준비
```bash
# HTML 테스트 파일이 다음 경로에 있어야 합니다:
/Users/recrash/Downloads/0_FW_ Hub HTML_250813/Drum 재고 관리.html
```

### 2. 서비스 실행
```bash
# 터미널 1: Frontend 서버
cd webservice/frontend
npm run dev

# 터미널 2: Backend 서버 (webservice)
cd webservice
source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m uvicorn app.main:app --reload --port 8000

# 터미널 3: AutoDoc 서비스 (선택사항)
cd autodoc_service
source .venv312/bin/activate
python run_autodoc_service.py
```

### 3. Repository 경로 설정
테스트에서 사용하는 Repository 경로:
```
/Users/recrash/Documents/Workspace/cm-docs
```

## 테스트 실행 방법

### 전체 테스트 실행
```bash
cd webservice/frontend
npm run test:e2e -- full-generation-websocket.spec.ts
```

### 특정 테스트만 실행
```bash
# HTML 업로드 및 Full Generation 워크플로우만
npx playwright test "HTML 파일 업로드 및 Full Generation 워크플로우"

# WebSocket 연결 테스트만
npx playwright test "WebSocket 연결 및 진행상황 수신 테스트"

# CLI URL 프로토콜 검증만
npx playwright test "CLI URL 프로토콜 파라미터 검증"
```

### 헤드리스 모드 해제 (브라우저 UI 확인)
```bash
npx playwright test full-generation-websocket.spec.ts --headed
```

### 디버그 모드 실행
```bash
npx playwright test full-generation-websocket.spec.ts --debug
```

## 테스트 시나리오 상세

### 1. HTML 파일 업로드 및 Full Generation 워크플로우
- ✅ 웹페이지 접속 확인
- ✅ HTML 업로드 탭으로 이동
- ✅ HTML 파일 업로드 및 파싱
- ✅ Full Generation 버튼 확인
- ✅ Custom URL Protocol 호출 감지
- ✅ CLI 대기 상태 UI 표시 확인

### 2. WebSocket 연결 및 진행상황 수신 테스트
- ✅ WebSocket 연결 설정
- ✅ 연결 성공/실패 확인
- ✅ 메시지 수신 기능 테스트
- ✅ 타임아웃 처리 확인

### 3. CLI URL 프로토콜 파라미터 검증
- ✅ URL 형식 검증 (`testscenariomaker://full-generate`)
- ✅ 필수 파라미터 확인 (`sessionId`, `repoPath`)
- ✅ URL 파싱 및 디코딩 테스트

### 4. 백엔드 API 엔드포인트 확인
- ✅ Webservice API 헬스 체크
- ✅ AutoDoc API 헬스 체크
- ✅ API 응답 형식 검증

### 5. HTML 파일 메타데이터 파싱 API 테스트
- ✅ HTML 파일 업로드 및 파싱
- ✅ 메타데이터 추출 확인
- ✅ API 응답 데이터 검증

### 6. WebSocket 엔드포인트 접근성 테스트
- ✅ Full Generation WebSocket 엔드포인트 접근
- ✅ Progress WebSocket 엔드포인트 접근
- ✅ 오류 처리 및 타임아웃 테스트

## 예상 결과

### 성공적인 테스트 실행 시
```
🧪 Full Generation 전체 워크플로우 테스트 시작
✅ 1. 웹페이지 접속 성공
✅ 2. HTML 업로드 탭으로 이동
✅ 3. 테스트 HTML 파일 존재 확인
✅ 4. HTML 파일 업로드 완료
✅ 5. HTML 파싱 시작
✅ 6. HTML 파싱 완료
✅ 7. Full Generation 버튼 확인
✅ 8. CLI 대기 상태 UI 표시 확인
✅ 9. Custom URL 호출 확인: testscenariomaker://full-generate?sessionId=xxx&repoPath=...
📋 세션 ID: test_full_gen_1234567890
🎉 HTML 업로드 및 Full Generation 기본 흐름 테스트 완료!
```

### WebSocket 연결 테스트 결과
```
🧪 WebSocket 연결 및 진행상황 수신 테스트 시작
📋 테스트 세션 ID: test_full_gen_1234567890
🔌 WebSocket 연결 성공 (또는 예상된 연결 실패)
📊 WebSocket 테스트 결과: { connected: true/false, messages: [...], error: null }
🎉 WebSocket 연결 테스트 완료!
```

## 주의사항

### 1. CLI 애플리케이션 없이 테스트
- 실제 CLI 애플리케이션이 설치되지 않은 환경에서도 테스트가 실행됩니다
- Custom URL 호출은 감지되지만 실제 CLI는 실행되지 않습니다
- WebSocket 연결은 시도되지만 CLI에서 연결하지 않으므로 메시지는 수신되지 않을 수 있습니다

### 2. 파일 경로 의존성
- HTML 테스트 파일이 지정된 경로에 없으면 해당 테스트는 스킵됩니다
- Repository 경로는 실제 존재하는 경로여야 합니다

### 3. 서비스 의존성
- Frontend (포트 3000)와 Backend (포트 8000)가 실행 중이어야 합니다
- AutoDoc 서비스 (포트 8001)는 선택사항이지만 관련 테스트에 영향을 줍니다

### 4. 브라우저 보안 정책
- WebSocket 연결 및 파일 업로드 테스트를 위해 특별한 브라우저 플래그가 설정되어 있습니다
- 일부 보안 기능이 비활성화되어 테스트 환경에서만 사용해야 합니다

## 문제 해결

### 테스트 실패 시 확인사항

1. **서비스 실행 상태 확인**
   ```bash
   # Frontend 확인
   curl http://localhost:3000

   # Backend 확인
   curl http://localhost:8000/api/webservice/health

   # AutoDoc 확인 (선택사항)
   curl http://localhost:8001/api/autodoc/health
   ```

2. **HTML 파일 존재 확인**
   ```bash
   ls -la "/Users/recrash/Downloads/0_FW_ Hub HTML_250813/Drum 재고 관리.html"
   ```

3. **Repository 경로 확인**
   ```bash
   ls -la /Users/recrash/Documents/Workspace/cm-docs
   ```

4. **로그 확인**
   ```bash
   # Playwright 테스트 로그
   npx playwright show-report

   # 브라우저 콘솔 로그 확인 (디버그 모드에서)
   npx playwright test --debug
   ```

### 일반적인 오류와 해결책

| 오류 | 원인 | 해결책 |
|------|------|--------|
| `ECONNREFUSED` | 서버가 실행되지 않음 | Frontend/Backend 서버 재시작 |
| `File not found` | HTML 파일 경로 오류 | 파일 경로 확인 및 수정 |
| `WebSocket timeout` | CLI가 실행되지 않음 | 예상된 동작 (CLI 없음) |
| `Page load timeout` | Frontend 서버 응답 없음 | Frontend 서버 상태 확인 |

## 추가 기능

### 테스트 커스터마이징
테스트 파일의 상단 상수들을 수정하여 다른 환경에서 테스트 가능:

```typescript
const TEST_HTML_FILE = '/path/to/your/test.html'
const TEST_REPO_PATH = '/path/to/your/repository'
const FRONTEND_URL = 'http://your-frontend:3000'
const BACKEND_URL = 'http://your-backend:8000'
```

### 성능 모니터링
테스트 실행 시간 및 리소스 사용량을 모니터링하려면:
```bash
npx playwright test full-generation-websocket.spec.ts --reporter=line
```

### 스크린샷 및 비디오 녹화
테스트 실행 과정을 기록하려면:
```bash
npx playwright test full-generation-websocket.spec.ts --video=on --screenshot=only-on-failure
```