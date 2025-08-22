## 폐쇄망 운영 환경 시스템 배포 매뉴얼

### 1\. 개요

본 문서는 '변경관리문서 생성 자동화 시스템'을 외부 인터넷이 차단된 폐쇄망 운영 서버(Windows Server)에 배포하고 설정하는 절차를 안내합니다.

#### 시스템 구성 요소

  * **webservice**: 사용자 UI(React) 및 핵심 API(FastAPI, Python 3.13)
  * **autodoc\_service**: 문서 생성 전문 API(FastAPI, Python 3.12)

#### 배포 아키텍처 원칙

본 시스템은 **애플리케이션(`apps`)**, **데이터(`data`)**, \*\*패키지(`packages`)\*\*의 역할을 명확히 분리한 표준 폴더 구조를 따릅니다. 이를 통해 배포와 유지보수의 안정성을 확보합니다.

-----

### 2\. 사전 준비 사항

운영 서버에 아래 항목들이 준비되어 있어야 합니다.

1.  **배포 패키지 (Deployment Package)**

      * 개발 환경의 Jenkins CI 파이프라인을 통해 생성된 **`deploy-package.zip`** 파일 1개.
      * 이 압축 파일에는 아래 모든 구성 요소가 포함되어 있습니다.
          * 설치 파일 (`.whl`)
          * 프론트엔드 빌드 결과물
          * 최초 실행에 필요한 데이터 (템플릿, 모델 등)

2.  **서버 환경**

      * **OS**: Windows Server
      * **Python**: **Python 3.13** 과 **Python 3.12** 가 모두 설치되어 있어야 합니다. (`py -3.13 --version`, `py -3.12 --version` 명령어로 확인)
      * **NSSM**: Windows 서비스를 쉽게 등록/관리해 주는 `nssm.exe` 파일이 서버 내 사용 가능한 경로에 위치해야 합니다.

-----

### 3\. 배포 절차

#### 3.1. 배포 패키지 배치 및 압축 해제

1.  사전 준비한 `deploy-package.zip` 파일을 운영 서버의 **`C:\`** 드라이브로 복사합니다.

2.  `C:\` 위치에서 압축을 해제합니다.

3.  압축 해제 후, 아래와 같은 폴더 구조가 생성되었는지 확인합니다.

    ```
    C:
    └── deploys
        ├── apps/
        ├── data/
        └── packages/
    ```

#### 3.2. Python 가상환경 생성 및 패키지 설치

폐쇄망이므로 인터넷을 통해 패키지를 다운로드할 수 없습니다. `packages` 폴더에 동봉된 `.whl` 파일을 사용하여 설치를 진행합니다.

**PowerShell**을 관리자 권한으로 실행하여 아래 명령어를 순서대로 입력합니다.

1.  **webservice (Python 3.13) 설정**

    ```powershell
    # 1. webservice 앱 폴더 및 가상환경 생성
    New-Item -ItemType Directory -Force -Path "C:\deploys\apps\webservice"
    py -3.13 -m venv "C:\deploys\apps\webservice\.venv"

    # 2. packages 폴더에 있는 webservice .whl 파일 설치
    # (주의: 파일 이름의 버전은 배포 시점에 따라 달라질 수 있음)
    C:\deploys\apps\webservice\.venv\Scripts\pip.exe install C:\deploys\packages\webservice\webservice-*.whl
    ```

2.  **autodoc\_service (Python 3.12) 설정**

    ```powershell
    # 1. autodoc_service 앱 폴더 및 가상환경 생성
    New-Item -ItemType Directory -Force -Path "C:\deploys\apps\autodoc_service"
    py -3.12 -m venv "C:\deploys\apps\autodoc_service\.venv312"

    # 2. packages 폴더에 있는 autodoc_service .whl 파일 설치
    C:\deploys\apps\autodoc_service\.venv312\Scripts\pip.exe install C:\deploys\packages\autodoc_service\autodoc_service-*.whl
    ```

#### 3.3. Windows 서비스 등록 (NSSM)

`nssm.exe`를 사용하여 각 서비스를 Windows 서비스로 등록합니다. 이는 서버 재부팅 시 자동으로 서비스를 시작하게 해줍니다.

**PowerShell**에서 아래 명령어를 실행하여 NSSM GUI를 띄우고, 각 서비스 설정을 정확히 입력합니다.

1.  **webservice 등록**

    ```powershell
    nssm install webservice
    ```

      * **Application 탭**
          * **Path**: `C:\deploys\apps\webservice\.venv\Scripts\python.exe`
          * **Startup directory**: `C:\deploys\apps\webservice`
          * **Arguments**: `-m uvicorn backend.main:app --host 0.0.0.0 --port 8001`
      * **Environment 탭 (가장 중요)**
          * `WEBSERVICE_DATA_PATH=C:\deploys\data\webservice`

2.  **autodoc\_service 등록**

    ```powershell
    nssm install autodoc_service
    ```

      * **Application 탭**
          * **Path**: `C:\deploys\apps\autodoc_service\.venv312\Scripts\python.exe`
          * **Startup directory**: `C:\deploys\apps\autodoc_service`
          * **Arguments**: `-m uvicorn app.main:app --host 0.0.0.0 --port 8000`
      * **Environment 탭 (가장 중요)**
          * `AUTODOC_DATA_PATH=C:\deploys\data\autodoc_service`

3.  **서비스 로그온 계정 설정 (필요시)**

      * `서비스(services.msc)`를 열어 `webservice`와 `autodoc_service`의 속성으로 들어갑니다.
      * `로그온` 탭에서 시스템 환경 변수 접근 권한이 있는 계정(예: Local System 또는 특정 관리자 계정)으로 설정합니다.

#### 3.4. 서비스 시작

모든 설정이 완료되면 서비스를 시작합니다.

```powershell
nssm start webservice
nssm start autodoc_service
```

-----

### 4\. 서비스 확인 및 로그 분석

  * **서비스 상태 확인**: `nssm status webservice` 명령어로 `SERVICE_RUNNING` 상태인지 확인합니다.
  * **로그 파일 위치**:
      * **webservice 로그**: `C:\deploys\data\webservice\logs`
      * **autodoc\_service 로그**: `C:\deploys\data\autodoc_service\logs`
  * **데이터 생성 위치**:
      * **문서/모델/DB**: `C:\deploys\data\webservice` 하위 폴더
      * **템플릿/생성문서**: `C:\deploys\data\autodoc_service` 하위 폴더

-----

### 5\. 시스템 업데이트 절차

새로운 버전 배포 시, 아래 절차를 따릅니다.

1.  **서비스 중지**: `nssm stop webservice`, `nssm stop autodoc_service`
2.  **신규 패키지 압축 해제**: 새로운 `deploy-package.zip` 파일을 `C:\`에 덮어쓰기로 압축 해제합니다. (`apps`, `packages` 폴더가 갱신됩니다.)
3.  **패키지 재설치**: **3.2절**의 `pip install` 명령어만 다시 실행하여 패키지를 업그레이드합니다.
4.  **서비스 시작**: `nssm start webservice`, `nssm start autodoc_service`

**※ 중요: 업데이트 중 `C:\deploys\data` 폴더는 절대 수정하거나 삭제하지 않습니다.**

-----

이 매뉴얼대로만 진행하면, 누구라도 안정적으로 폐쇄망에 시스템을 배포할 수 있을 거야. 우리가 함께 설계한 멋진 아키텍처의 최종 결과물이지\! 수고했어\!