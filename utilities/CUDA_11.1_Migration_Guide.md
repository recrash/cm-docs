# CUDA 11.1 마이그레이션 가이드

## 개요
이 문서는 webservice를 CUDA 12.1에서 CUDA 11.1로 다운그레이드하는 과정을 설명합니다.
RTX 3090 GPU 환경에서 CUDA 11.1 사용이 필수인 폐쇄망 환경을 위한 가이드입니다.

## 주요 변경 사항

### 1. Python 버전 변경
- **기존**: Python 3.12
- **변경**: Python 3.10
- **이유**: PyTorch 1.10.2 (CUDA 11.1 지원 버전)은 Python 3.10까지만 지원

### 2. 주요 패키지 버전 변경
```
torch==2.5.1 → torch==1.10.2+cu111
torchvision==0.16.1 → torchvision==0.11.3+cu111
torchaudio==2.5.1 → torchaudio==0.10.2+cu111
transformers==4.55.4 → transformers==4.17.0
onnxruntime-gpu==1.14.0 → onnxruntime-gpu==1.12.1
```

### 3. 수정된 파일들
- `requirements.txt`: CUDA 11.1 호환 패키지 버전으로 수정
- `pyproject.toml`: Python 3.10 호환성 명시
- `Jenkinsfile.backend`: Python 3.10 및 CUDA 11.1 URL 참조

## Wheelhouse 재생성 가이드

### 1. 사전 준비
```powershell
# Python 3.10이 설치되어 있는지 확인
py -3.10 --version  # Python 3.10.11

# 작업 디렉토리로 이동
cd C:\Users\recrash1325\Documents\cm-docs\webservice
```

### 2. 새로운 가상환경 생성 (필요시)
```powershell
# 기존 가상환경 백업 (선택사항)
Rename-Item .venv .venv_backup

# Python 3.10으로 새 가상환경 생성
py -3.10 -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate
```

### 3. pip 업그레이드
```powershell
python -m pip install --upgrade pip
```

### 4. Wheelhouse 디렉토리 생성
```powershell
# wheelhouse 디렉토리 생성
New-Item -ItemType Directory -Force -Path wheelhouse

# 기존 wheelhouse 백업 (있는 경우)
if (Test-Path "C:\deploys\packages\wheelhouse") {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Rename-Item "C:\deploys\packages\wheelhouse" "C:\deploys\packages\wheelhouse_backup_$timestamp"
}
```

### 5. 의존성 패키지 다운로드
```powershell
# CUDA 11.1 호환 패키지 다운로드
pip download --extra-index-url https://download.pytorch.org/whl/cu111 `
    -r requirements.txt `
    -c pip.constraints.txt `
    -d wheelhouse

# 다운로드 확인
Get-ChildItem wheelhouse | Measure-Object
# 예상: 약 100개 이상의 .whl 파일
```

### 6. 특정 CUDA 패키지 확인
```powershell
# CUDA 11.1 버전 패키지 확인
Get-ChildItem wheelhouse | Where-Object {$_.Name -match "cu111"}
# 출력 예시:
# torch-1.10.2+cu111-cp310-cp310-win_amd64.whl
# torchaudio-0.10.2+cu111-cp310-cp310-win_amd64.whl
# torchvision-0.11.3+cu111-cp310-cp310-win_amd64.whl
```

### 7. Wheelhouse 배포
```powershell
# 배포 디렉토리 생성
New-Item -ItemType Directory -Force -Path "C:\deploys\packages\wheelhouse"

# wheelhouse 내용 복사
Copy-Item -Path "wheelhouse\*" -Destination "C:\deploys\packages\wheelhouse\" -Force
```

### 8. 오프라인 설치 테스트
```powershell
# 새로운 테스트 환경 생성
cd C:\temp
py -3.10 -m venv test_env
.\test_env\Scripts\activate

# 오프라인 설치 (인터넷 연결 없이)
pip install --no-index --find-links=C:\deploys\packages\wheelhouse `
    -r C:\Users\recrash1325\Documents\cm-docs\webservice\requirements_no_version.txt `
    -c C:\Users\recrash1325\Documents\cm-docs\webservice\pip.constraints.txt

# CUDA 확인
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}')"
# 예상 출력:
# PyTorch: 1.10.2+cu111
# CUDA Available: True (RTX 3090이 있는 경우)
```

## 운영 환경 배포

### 1. 운영 서버 준비
```powershell
# 운영 서버에서 Python 3.10 설치 확인
python --version  # Python 3.10.x

# 배포 경로 생성
New-Item -ItemType Directory -Force -Path "C:\deploys\apps\webservice"
New-Item -ItemType Directory -Force -Path "C:\deploys\packages\wheelhouse"
New-Item -ItemType Directory -Force -Path "C:\deploys\data\webservice"
```

### 2. Wheelhouse 파일 전송
- `wheelhouse` 폴더의 모든 `.whl` 파일을 USB 또는 안전한 파일 전송 방법으로 운영 서버의 `C:\deploys\packages\wheelhouse\`로 복사

### 3. 운영 환경 설치
```powershell
cd C:\deploys\apps\webservice

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 환경변수 설정
$env:WEBSERVICE_DATA_PATH = "C:\deploys\data\webservice"
$env:ANONYMIZED_TELEMETRY = "False"

# 오프라인 설치
pip install --no-index --find-links=C:\deploys\packages\wheelhouse `
    -r requirements.txt `
    -c pip.constraints.txt
```

### 4. 서비스 재시작
```powershell
# NSSM 서비스 재시작
nssm restart webservice
```

## 트러블슈팅

### Q1: CUDA 버전 확인 방법
```powershell
# NVIDIA 드라이버 및 CUDA 정보 확인
nvidia-smi

# Python에서 CUDA 확인
python -c "import torch; print(torch.version.cuda)"
```

### Q2: ImportError 발생시
```powershell
# 캐시 정리
pip cache purge

# 가상환경 재생성
Remove-Item -Recurse -Force .venv
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install --no-index --find-links=C:\deploys\packages\wheelhouse -r requirements.txt -c pip.constraints.txt
```

### Q3: ChromaDB 오류 발생시
- ChromaDB 1.0.20과 sentence-transformers 2.2.2는 호환되므로 문제없음
- 단, 네트워크 통신 차단을 위해 `ANONYMIZED_TELEMETRY=False` 환경변수 필수

## 검증 체크리스트

- [ ] Python 3.10 설치 확인
- [ ] CUDA 11.1 드라이버 설치 확인 (RTX 3090)
- [ ] requirements.txt의 CUDA URL이 `cu111`로 변경됨
- [ ] pyproject.toml의 Python 버전이 `>=3.10,<3.11`로 변경됨
- [ ] Jenkinsfile.backend의 Python 및 CUDA 참조 변경됨
- [ ] Wheelhouse에 `cu111` 버전 패키지 포함 확인
- [ ] 오프라인 설치 테스트 성공
- [ ] `torch.cuda.is_available()` True 반환 확인

## 롤백 가이드

만약 문제가 발생하여 이전 버전으로 롤백이 필요한 경우:

1. Git에서 이전 커밋으로 되돌리기
2. `.venv_backup` 가상환경 복원
3. `wheelhouse_backup_*` 폴더 복원
4. NSSM 서비스 재시작

## 문의사항
- 폐쇄망 환경에서 추가 패키지가 필요한 경우, 개발 환경에서 먼저 다운로드하여 wheelhouse에 추가
- CUDA 관련 문제는 NVIDIA 드라이버 버전과 CUDA Runtime 버전 호환성 확인 필요