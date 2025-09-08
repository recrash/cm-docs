# Utilities

이 폴더에는 개발자와 운영자가 사용하는 유틸리티 스크립트들이 포함되어 있습니다.
**이 폴더의 파일 변경은 Jenkins 빌드를 트리거하지 않습니다.**

## 포함된 스크립트

### 배포 패키지 생성
- **create-deploy-package.ps1** - Windows용 배포 패키지 생성 스크립트
- **create-deploy-package.sh** - Linux/macOS용 배포 패키지 생성 스크립트

### 의존성 다운로드
- **Download-All-Dependencies.ps1** - Windows용 Python/npm 의존성 일괄 다운로드
- **download-all-dependencies.sh** - Linux/macOS용 Python/npm 의존성 일괄 다운로드

### 환경 정리
- **cleanup_test_env.ps1** - 테스트 환경 정리 스크립트 (수동 실행용)

## 주의사항

- `scripts/deploy_test_env.ps1`은 Jenkins에서 직접 사용하므로 scripts 폴더에 유지됩니다
- 이 폴더의 스크립트들은 빌드 시스템과 독립적으로 실행됩니다
- Jenkins 빌드가 필요한 스크립트는 scripts/ 폴더에 위치해야 합니다