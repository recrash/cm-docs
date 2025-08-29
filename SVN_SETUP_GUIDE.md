# SVN 클라이언트 설치 가이드

TestscenarioMaker CLI가 SVN 저장소를 지원하기 위한 SVN 클라이언트 설치 안내서입니다.

## 개요

SVN (Subversion) 지원 기능이 추가되어 CLI에서 SVN 저장소의 변경사항을 분석할 수 있습니다. 이 기능을 사용하기 위해서는 SVN 클라이언트 툴이 설치되어 있어야 합니다.

### 지원 기능
- **Working Directory vs HEAD 비교**: 현재 작업 중인 파일과 마지막 커밋 비교
- **자동 VCS 감지**: Git과 SVN 저장소를 자동으로 구분하여 처리
- **한국어 에러 메시지**: SVN 특화 에러 상황에 대한 친화적 안내

## Windows 서버 환경 설치

### 1. TortoiseSVN + Command Line Tools 설치 (권장)

**다운로드**: https://tortoisesvn.net/downloads.html

1. **TortoiseSVN 설치 파일 다운로드**
   - 64bit: `TortoiseSVN-x.x.x.xxxxx-x64-svn-1.14.x.msi`
   - 32bit: `TortoiseSVN-x.x.x.xxxxx-win32-svn-1.14.x.msi`

2. **설치 중 중요 옵션**
   ```
   ✅ Command line client tools
   ```
   **반드시 체크하여 설치해야 CLI에서 `svn` 명령어 사용 가능**

3. **설치 확인**
   ```cmd
   svn --version
   ```
   
   예상 출력:
   ```
   svn, version 1.14.x (r.....)
   compiled ...
   ```

### 2. Apache Subversion CLI Tools (대안)

**다운로드**: https://subversion.apache.org/packages.html#windows

1. **Win32Svn 또는 SlikSVN 설치**
2. **PATH 환경변수 설정**
   - 시스템 속성 → 고급 → 환경변수
   - Path에 SVN 설치 경로 추가 (예: `C:\Program Files\SlikSvn\bin`)

### 3. Jenkins 서버 환경 설정

**Jenkinsfile 수정 필요사항**:

```groovy
environment {
    // SVN Path 추가
    PATH = "${env.PATH};C:\\Program Files\\TortoiseSVN\\bin"
}

stage('SVN 상태 확인') {
    steps {
        script {
            try {
                bat 'svn --version'
                echo "SVN 클라이언트 설치 확인됨"
            } catch (Exception e) {
                error "SVN 클라이언트가 설치되지 않았습니다: ${e.getMessage()}"
            }
        }
    }
}
```

## macOS 환경 설치

### Homebrew를 통한 설치 (권장)

```bash
# SVN 클라이언트 설치
brew install subversion

# 설치 확인
svn --version
```

### MacPorts를 통한 설치 (대안)

```bash
# MacPorts로 설치
sudo port install subversion

# PATH 설정 (필요시)
echo 'export PATH=/opt/local/bin:$PATH' >> ~/.zshrc
source ~/.zshrc
```

## Linux 환경 설치

### Ubuntu/Debian

```bash
# 패키지 업데이트
sudo apt-get update

# SVN 클라이언트 설치
sudo apt-get install subversion

# 설치 확인
svn --version
```

### CentOS/RHEL

```bash
# SVN 클라이언트 설치
sudo yum install subversion

# 또는 dnf 사용 (최신 버전)
sudo dnf install subversion

# 설치 확인
svn --version
```

## 설치 확인 및 테스트

### 1. CLI 명령어 테스트

```bash
# SVN 저장소 경로로 이동
cd /path/to/your/svn/repository

# SVN 상태 확인
svn status

# SVN 정보 확인  
svn info

# 변경사항 확인
svn diff
```

### 2. TestscenarioMaker CLI 테스트

```bash
# 로컬 SVN 저장소 테스트
ts-cli analyze /Users/recrash/Documents/Workspace/TmSVN

# 지원 VCS 타입 확인
ts-cli --help
# 출력에서 "지원되는 VCS: git, svn" 확인
```

## 자주 발생하는 문제 및 해결

### Windows 환경

**문제**: `'svn'은(는) 내부 또는 외부 명령, 실행할 수 있는 프로그램, 또는 배치 파일이 아닙니다.`

**해결**:
1. TortoiseSVN 재설치 시 "Command line client tools" 체크
2. 환경변수 PATH에 `C:\Program Files\TortoiseSVN\bin` 추가
3. 시스템 재시작 또는 새 터미널 세션 시작

**문제**: `svn: E155007: Working copy not found`

**해결**:
- 올바른 SVN 저장소 경로인지 확인
- `.svn` 디렉토리가 존재하는지 확인

### Linux/macOS 환경

**문제**: `bash: svn: command not found`

**해결**:
```bash
# 패키지 매니저로 설치 확인
which svn  # 경로 확인
echo $PATH  # PATH 환경변수 확인

# 패키지 재설치
brew reinstall subversion  # macOS
sudo apt-get reinstall subversion  # Ubuntu
```

## 운영 환경 권장사항

### 1. 버전 호환성
- **SVN 클라이언트**: 1.8.x 이상 권장
- **TortoiseSVN**: 1.14.x 이상 권장

### 2. 보안 설정
- HTTPS 프로토콜 사용 권장
- 인증서 검증 활성화
- 접근 권한 최소한으로 제한

### 3. 성능 최적화
```bash
# SVN 클라이언트 설정 최적화
svn config --global config:miscellany:use-commit-times yes
svn config --global servers:global:store-passwords no
svn config --global servers:global:store-plaintext-passwords no
```

## 개발 서버 환경 확인

### 현재 상태
- **개발 서버 (GCP)**: SVN 클라이언트 **미설치**
- **운영 서버 (Windows)**: SVN 클라이언트 **미설치**

### 설치 계획
1. **개발 서버 (Ubuntu)**: `sudo apt-get install subversion`
2. **운영 서버 (Windows)**: TortoiseSVN + Command Line Tools
3. **Jenkins 파이프라인**: SVN PATH 환경변수 설정

## 문의 및 지원

SVN 설치 및 설정 관련 문의사항은 개발팀에 문의해주세요.

### 지원 정보
- **지원 OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **SVN 버전**: 1.8+ (1.14+ 권장)
- **CLI 버전**: v2.0+ (SVN 지원)