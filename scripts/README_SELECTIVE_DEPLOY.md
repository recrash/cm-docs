# 선택적 서비스 배포 시스템

기존 `deploy_test_env.ps1`의 모든 서비스 일괄 배포 문제를 해결하기 위해 서비스별 개별 배포가 가능한 시스템으로 개선했습니다.

## 문제점 해결

### 기존 문제점
- **전체 서비스 재시작**: AutoDoc만 변경되어도 프론트엔드, 웹서비스까지 모두 재배포
- **frontend.zip 의존성**: 프론트엔드를 빌드하지 않으면 파이프라인 실패
- **불필요한 리소스 사용**: 변경되지 않은 서비스까지 재배포로 인한 시간 낭비

### 해결 방안
- **모듈화된 배포 시스템**: 서비스별 독립 배포 스크립트
- **선택적 배포**: 필요한 서비스만 선택해서 배포
- **공통 기능 모듈화**: 중복 코드 제거 및 재사용성 향상

## 파일 구조

```
scripts/
├── deploy_common.ps1              # 공통 기능 모듈
├── deploy_frontend_only.ps1       # 프론트엔드 전용 배포
├── deploy_webservice_only.ps1     # 웹서비스 전용 배포  
├── deploy_autodoc_only.ps1        # AutoDoc 전용 배포
├── deploy_test_env_selective.ps1  # 선택적 배포 (기존 스크립트 개선)
└── deploy_test_env.ps1            # 기존 스크립트 (호환성 유지)
```

## 사용 방법

### 1. 개별 서비스 배포

#### 프론트엔드만 배포
```powershell
.\scripts\deploy_frontend_only.ps1 `
  -Bid "feature_auth" `
  -WebSrc "C:\workspace\cm-docs\webservice" `
  -WebFrontDst "C:\nginx\html\tests\feature_auth" `
  -UrlPrefix "/tests/feature_auth/" `
  -PackagesRoot "C:\deploys\tests\feature_auth\packages"
```

#### 웹서비스 백엔드만 배포
```powershell
.\scripts\deploy_webservice_only.ps1 `
  -Bid "feature_auth" `
  -BackPort 8100 `
  -Py "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" `
  -Nssm "C:\tools\nssm\nssm.exe" `
  -Nginx "C:\nginx\nginx.exe" `
  -WebSrc "C:\workspace\cm-docs\webservice" `
  -WebBackDst "C:\deploys\tests\feature_auth\apps\webservice" `
  -PackagesRoot "C:\deploys\tests\feature_auth\packages"
```

#### AutoDoc 서비스만 배포
```powershell
.\scripts\deploy_autodoc_only.ps1 `
  -Bid "feature_auth" `
  -AutoPort 8101 `
  -Py "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" `
  -Nssm "C:\tools\nssm\nssm.exe" `
  -Nginx "C:\nginx\nginx.exe" `
  -AutoSrc "C:\workspace\cm-docs\autodoc_service" `
  -AutoDst "C:\deploys\tests\feature_auth\apps\autodoc_service" `
  -PackagesRoot "C:\deploys\tests\feature_auth\packages"
```

### 2. 선택적 배포 (개선된 메인 스크립트)

#### AutoDoc만 배포 (frontend.zip 없어도 OK)
```powershell
.\scripts\deploy_test_env_selective.ps1 `
  -Bid "feature_auth" -BackPort 8100 -AutoPort 8101 `
  -Py "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" `
  -Nssm "C:\tools\nssm\nssm.exe" -Nginx "C:\nginx\nginx.exe" `
  -NginxConfDir "C:\nginx\conf\conf.d" `
  -WebSrc "C:\workspace\cm-docs\webservice" `
  -AutoSrc "C:\workspace\cm-docs\autodoc_service" `
  -WebBackDst "C:\deploys\tests\feature_auth\apps\webservice" `
  -WebFrontDst "C:\nginx\html\tests\feature_auth" `
  -AutoDst "C:\deploys\tests\feature_auth\apps\autodoc_service" `
  -UrlPrefix "/tests/feature_auth/" `
  -PackagesRoot "C:\deploys\tests\feature_auth\packages" `
  -AutodocOnly
```

#### 프론트엔드 + 웹서비스만 배포 (AutoDoc 제외)
```powershell
.\scripts\deploy_test_env_selective.ps1 `
  [모든 필수 파라미터] `
  -DeployFrontend -DeployWebservice -DeployAutodoc:$false
```

#### 모든 서비스 배포 (기존 동작과 동일)
```powershell
.\scripts\deploy_test_env_selective.ps1 `
  [모든 필수 파라미터]
```

## Jenkins 파이프라인 통합

### Jenkinsfile 예시
```groovy
stage('Deploy Test Environment') {
    steps {
        script {
            def deployCommand = ""
            
            // 변경된 서비스 감지
            def frontendChanged = bat(
                script: 'git diff HEAD~1 HEAD --name-only | findstr /C:"webservice/frontend"',
                returnStatus: true
            ) == 0
            
            def webserviceChanged = bat(
                script: 'git diff HEAD~1 HEAD --name-only | findstr /C:"webservice/" | findstr /V /C:"webservice/frontend"',
                returnStatus: true
            ) == 0
            
            def autodocChanged = bat(
                script: 'git diff HEAD~1 HEAD --name-only | findstr /C:"autodoc_service"',
                returnStatus: true
            ) == 0
            
            // 선택적 배포 옵션 결정
            def deployOptions = ""
            if (frontendChanged && !webserviceChanged && !autodocChanged) {
                deployOptions = "-FrontendOnly"
            } else if (!frontendChanged && webserviceChanged && !autodocChanged) {
                deployOptions = "-WebserviceOnly"
            } else if (!frontendChanged && !webserviceChanged && autodocChanged) {
                deployOptions = "-AutodocOnly"
            }
            // 여러 서비스 변경 또는 기본: 모든 서비스 배포
            
            // 배포 실행
            bat """
                powershell -File scripts/deploy_test_env_selective.ps1 `
                  -Bid "${params.BRANCH}" `
                  -BackPort 8100 -AutoPort 8101 `
                  [기타 파라미터...] `
                  ${deployOptions}
            """
        }
    }
}
```

## 주요 기능

### 1. 공통 모듈 (deploy_common.ps1)
- `Initialize-CommonDirectories`: 공통 디렉토리 생성
- `Cleanup-OldBranchFolders`: 기존 브랜치 정리
- `Copy-MasterData`: 마스터 데이터 복사
- `Update-NginxConfig`: Nginx 설정 업데이트
- `Test-ServiceHealth`: 서비스 상태 확인

### 2. 에러 처리 및 롤백
- 개별 서비스 배포 실패 시 해당 서비스만 롤백
- 다른 서비스 배포는 계속 진행 (선택적 배포 모드)
- 상세한 에러 메시지 및 디버깅 정보 제공

### 3. 개발 편의성
- develop 브랜치 특별 처리 (서비스 재사용)
- 휠하우스 기반 오프라인 설치 지원
- UTF-8 인코딩 지원으로 한글 로그 정상 출력

## 마이그레이션 가이드

### 기존 사용자
```powershell
# 기존 방식 (여전히 동작)
.\scripts\deploy_test_env.ps1 [파라미터들...]

# 새로운 방식 (동일한 결과, 선택적 배포 가능)
.\scripts\deploy_test_env_selective.ps1 [파라미터들...]
```

### Jenkins 파이프라인
1. 기존 `deploy_test_env.ps1` 호출을 `deploy_test_env_selective.ps1`로 변경
2. 변경 감지 로직 추가하여 선택적 배포 옵션 적용
3. frontend.zip 의존성 문제 해결을 위해 `copyArtifacts` 조건부 실행

## 장점

1. **효율성**: 변경된 서비스만 배포하여 시간 단축
2. **안정성**: 하나의 서비스 배포 실패가 다른 서비스에 영향 없음
3. **유연성**: 필요에 따라 개별 또는 조합 배포 가능
4. **호환성**: 기존 스크립트와 완전 호환
5. **디버깅**: 서비스별 독립된 로그 및 에러 처리