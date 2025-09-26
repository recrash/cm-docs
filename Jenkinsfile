// cm-docs/Jenkinsfile - 통합 멀티브랜치 파이프라인
// Pseudo MSA 아키텍처에 맞춘 스마트 배포 시스템
pipeline { 
    agent any
    
    environment {
        // Python 환경 격리를 위한 환경변수 초기화 (PYTHONHOME 충돌 방지)
        PYTHONHOME = ''
        PYTHONPATH = ''

        // 통합 환경변수 관리
        CM_DOCS_ROOT = 'C:\\deploys\\cm-docs'
        WHEELHOUSE_PATH = 'C:\\deploys\\packages\\wheelhouse'
        BACKUP_ROOT = 'C:\\deploys\\backup'
        
        // 테스트 인스턴스 환경 (브랜치별)
        DEPLOY_ROOT = 'C:\\deploys\\tests'
        PY_PATH = '%LOCALAPPDATA%\\Programs\\Python\\Python39\\python.exe'
        PY_PATH_312 = '%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe'
        NSSM_PATH = 'nssm'
        NGINX_PATH = 'C:\\nginx\\nginx.exe'
        NGINX_CONF_DIR = 'C:\\nginx\\conf\\conf.d'
        
        // 프로젝트 경로
        WEBSERVICE_PATH = "${CM_DOCS_ROOT}\\webservice"
        AUTODOC_PATH = "${CM_DOCS_ROOT}\\autodoc_service"
        CLI_PATH = "${CM_DOCS_ROOT}\\cli"
        
        // 환경변수 기반 데이터 경로 (프로덕션)
        WEBSERVICE_DATA_PATH = 'C:\\deploys\\data\\webservice'
        AUTODOC_DATA_PATH = 'C:\\deploys\\data\\autodoc_service'
        
        // 배포 경로
        WEBSERVICE_DEPLOY_PATH = 'C:\\deploys\\apps\\webservice'
        AUTODOC_DEPLOY_PATH = 'C:\\deploys\\apps\\autodoc_service'
        NGINX_ROOT = 'C:\\nginx\\html'
        
        // Python 실행 경로
        WEBSERVICE_PYTHON = "${WEBSERVICE_DEPLOY_PATH}\\.venv\\Scripts\\python.exe"
        WEBSERVICE_PIP = "${WEBSERVICE_DEPLOY_PATH}\\.venv\\Scripts\\pip.exe"
        AUTODOC_PYTHON = "${AUTODOC_DEPLOY_PATH}\\.venv312\\Scripts\\python.exe"
        AUTODOC_PIP = "${AUTODOC_DEPLOY_PATH}\\.venv312\\Scripts\\pip.exe"
        
        // 서비스 URL
        WEBSERVICE_FRONTEND_URL = 'http://localhost'    
        
        // 헬스체크 URL
        WEBSERVICE_HEALTH_URL = 'http://localhost:8000/api/webservice/health'
        AUTODOC_HEALTH_URL = 'http://localhost:8001/api/autodoc/health'
        
        // 배포 상태 추적
        DEPLOYMENT_STATUS = 'NONE'
        FAILED_SERVICES = ''
        CRITICAL_FAILURE = 'false'
        
        // 기타 설정
        ANONYMIZED_TELEMETRY = 'False'
    }        
    
    stages {
        stage('소스코드 체크아웃 및 변경 감지') {
            steps {
                checkout scm
                script {
                    def changedFiles = []
                    try {
                        // 마지막 성공한 빌드의 커밋과 비교하여 변경 감지
                        def gitCommand
                        def previousCommit = null
                        
                        // Jenkins 내장 환경 변수로 이전 성공한 빌드의 커밋 ID 가져오기
                        if (env.GIT_PREVIOUS_SUCCESSFUL_COMMIT) {
                            previousCommit = env.GIT_PREVIOUS_SUCCESSFUL_COMMIT
                            echo "이전 성공 빌드의 커밋: ${previousCommit}"
                        } else if (env.GIT_PREVIOUS_COMMIT) {
                            // 이전 커밋 정보가 있으면 사용
                            previousCommit = env.GIT_PREVIOUS_COMMIT
                            echo "이전 커밋: ${previousCommit}"
                        }
                        
                        if (previousCommit) {
                            echo "마지막 성공 빌드 기준 변경 감지: ${previousCommit}..${env.GIT_COMMIT}"
                            gitCommand = "git diff --name-only ${previousCommit} ${env.GIT_COMMIT}"
                        } else {
                            // 이전 커밋 정보가 없는 경우 (예: 새 브랜치의 첫 빌드) 최신 커밋 하나만 비교
                            echo "이전 커밋을 찾을 수 없어 최신 커밋만 비교합니다."
                            gitCommand = "git diff --name-only HEAD~1 HEAD"
                        }

                        echo "Git 변경 감지 명령: ${gitCommand}"
                        changedFiles = bat(
                            script: "@echo off && ${gitCommand}",
                            returnStdout: true
                        ).split('\\n').findAll { it.trim() && !it.contains('>git ') && !it.contains('C:\\') }

                    } catch (Exception e) {
                        echo "변경 감지 실패, 전체 빌드 실행: ${e.getMessage()}"
                        changedFiles = ['webservice/', 'autodoc_service/', 'cli/']
                    }

                    // *.md 파일은 제외하고 감지
                    def filteredFiles = changedFiles.findAll { !it.endsWith('.md') }
                    
                    // 서비스별 변경 감지 로직
                    env.AUTODOC_CHANGED = filteredFiles.any { it.startsWith('autodoc_service/') || it == 'autodoc_service/Jenkinsfile' } ? 'true' : 'false'
                    
                    // Webservice Backend 변경 감지 (frontend 및 frontend Jenkinsfile 제외)
                    env.WEBSERVICE_BACKEND_CHANGED = filteredFiles.any { 
                        (it.startsWith('webservice/') && 
                         !it.startsWith('webservice/frontend/') && 
                         it != 'webservice/Jenkinsfile.frontend') || 
                        it == 'webservice/Jenkinsfile.backend'
                    } ? 'true' : 'false'
                    
                    // Webservice Frontend 변경 감지
                    env.WEBSERVICE_FRONTEND_CHANGED = filteredFiles.any { 
                        it.startsWith('webservice/frontend/') || it == 'webservice/Jenkinsfile.frontend'
                    } ? 'true' : 'false'
                    
                    // 하위 호환성 유지 (통합 테스트, 배포 상태 등에서 사용)
                    env.WEBSERVICE_CHANGED = (env.WEBSERVICE_BACKEND_CHANGED == 'true' || 
                                              env.WEBSERVICE_FRONTEND_CHANGED == 'true') ? 'true' : 'false'
                    env.CLI_CHANGED = filteredFiles.any { it.startsWith('cli/') || it == 'cli/Jenkinsfile' } ? 'true' : 'false'
                    
                    // infra 폴더 변경 감지 (전체 배포 트리거)
                    env.INFRA_CHANGED = filteredFiles.any { it.startsWith('infra/') } ? 'true' : 'false'
                    
                    // 루트 파일 정확한 매칭 (utilities/ 폴더는 제외)
                    env.ROOT_CHANGED = filteredFiles.any { 
                        it == 'Jenkinsfile' || 
                        it == 'pyproject.toml' || 
                        it == '.gitignore' ||
                        (it.startsWith('scripts/') && !it.startsWith('utilities/'))
                    } ? 'true' : 'false'

                    echo """
                    ===========================================
                    📊 변경 감지 결과
                    ===========================================
                    • AutoDoc Service: ${env.AUTODOC_CHANGED}
                    • Webservice Backend: ${env.WEBSERVICE_BACKEND_CHANGED}
                    • Webservice Frontend: ${env.WEBSERVICE_FRONTEND_CHANGED}
                    • CLI: ${env.CLI_CHANGED}
                    • Infrastructure: ${env.INFRA_CHANGED}
                    • Root/Config: ${env.ROOT_CHANGED}
                    
                    전체 변경 파일: ${changedFiles.size()}개
                    빌드 대상 파일: ${filteredFiles.size()}개 (*.md 제외)

                    변경된 파일들:
                    ${changedFiles.join('\n')}
                    ===========================================
                    """
                    
                    // 빌드 대상 파일이 없으면 성공으로 종료
                    if (filteredFiles.size() == 0) {
                        env.DEPLOYMENT_STATUS = 'NO_CHANGES_SUCCESS'
                        currentBuild.result = 'SUCCESS'
                        currentBuild.description = '📄 문서 변경만 있음 - 배포 스킵'
                        
                        echo """
                        ℹ️ 빌드 대상 파일이 없어 파이프라인을 성공으로 종료합니다.
                        - 전체 변경 파일: ${changedFiles.size()}개
                        - 빌드 대상 파일: 0개
                        - 파이프라인 상태: SUCCESS
                        """
                        
                        return // 파이프라인 조기 종료
                    }
                }
            }
        }
        
        stage('Wheelhouse 검증') {
            steps {
                script {
                    echo """
                    ===========================================
                    📦 Wheelhouse 검증 및 pip 환경 준비
                    ===========================================
                    """

                    try {
                        bat """
                        chcp 65001 >NUL
                        powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "\$env:PYTHONIOENCODING='utf-8'; & {
                            # Wheelhouse 기본 검증
                            Write-Host '📋 Wheelhouse 상태 확인...'
                            if (-not (Test-Path '${env.WHEELHOUSE_PATH}')) {
                                Write-Host '⚠️  Wheelhouse 디렉토리가 없습니다. 생성합니다: ${env.WHEELHOUSE_PATH}'
                                New-Item -ItemType Directory -Force -Path '${env.WHEELHOUSE_PATH}' | Out-Null
                            }

                            # pip wheel 파일 확인
                            \$pipWheels = Get-ChildItem -Path '${env.WHEELHOUSE_PATH}' -Filter 'pip-*.whl' -ErrorAction SilentlyContinue
                            if (\$pipWheels.Count -eq 0) {
                                Write-Warning '⚠️  pip wheel 파일이 없습니다. pip 업그레이드가 온라인으로 진행됩니다.'
                                Write-Host '권장사항: pip wheel을 wheelhouse에 미리 준비하세요.'
                            } else {
                                Write-Host \"✅ pip wheel 발견: \$(\$pipWheels.Count)개 파일\"
                                \$pipWheels | ForEach-Object { Write-Host \"  - \$(\$_.Name)\" }
                            }

                            # 전체 wheel 개수 확인
                            \$allWheels = Get-ChildItem -Path '${env.WHEELHOUSE_PATH}' -Filter '*.whl' -ErrorAction SilentlyContinue
                            Write-Host \"📊 총 wheel 파일: \$(\$allWheels.Count)개\"

                            # 최소 필수 패키지 확인 (권장사항)
                            \$recommendedPackages = @('setuptools', 'wheel', 'pip', 'torch', 'torchvision', 'torchaudio')
                            \$missingPackages = @()
                            foreach (\$pkg in \$recommendedPackages) {
                                \$found = \$allWheels | Where-Object { \$_.Name -like \"\$pkg-*\" }
                                if (-not \$found) {
                                    \$missingPackages += \$pkg
                                }
                            }

                            if (\$missingPackages.Count -gt 0) {
                                Write-Warning \"⚠️  권장 패키지가 wheelhouse에 없습니다: \$(\$missingPackages -join ', ')\"
                                Write-Host '이는 경고사항이며 빌드는 계속 진행됩니다.'
                            } else {
                                Write-Host '✅ 모든 권장 패키지가 wheelhouse에 준비되었습니다.'
                            }

                            # Wheelhouse 잠금 파일 정리 (이전 빌드 잔존물)
                            if (Test-Path '${env.WHEELHOUSE_PATH}\\.lock') {
                                Remove-Item '${env.WHEELHOUSE_PATH}\\.lock' -Force -ErrorAction SilentlyContinue
                                Write-Host '🧹 이전 빌드의 wheelhouse 잠금 파일 정리'
                            }

                            Write-Host '✅ Wheelhouse 검증 완료'
                        }"
                        """

                        env.WHEELHOUSE_STATUS = 'VERIFIED'
                        echo "✅ Wheelhouse 검증 성공"

                    } catch (Exception e) {
                        env.WHEELHOUSE_STATUS = 'WARNING'
                        echo """
                        ⚠️ Wheelhouse 검증 경고
                        ===========================================
                        경고: ${e.getMessage()}

                        이는 경고사항이며 빌드는 계속 진행됩니다.
                        다만 pip 설치 중 메모리 오류가 발생할 가능성이 있습니다.

                        권장사항:
                        1. pip wheel을 미리 다운로드하여 wheelhouse에 저장
                        2. PyTorch 등 대용량 패키지 wheel 준비
                        3. 폐쇄망 환경에서는 모든 의존성을 사전 다운로드
                        ===========================================
                        """
                    }
                }
            }
        }

        stage('Branch Detect') {
            steps {
                script {
                    env.IS_TEST = (env.BRANCH_NAME.startsWith('feature/') || env.BRANCH_NAME.startsWith('hotfix/') || env.BRANCH_NAME == 'develop') ? 'true' : 'false'
                    env.BID = sanitizeId(env.BRANCH_NAME)
                    
                    // develop 브랜치는 고정 포트 사용
                    if (env.BRANCH_NAME == 'develop') {
                        env.BACK_PORT = '8099'
                        env.AUTO_PORT = '8199'
                    } else {
                        env.BACK_PORT = pickPort(env.BRANCH_NAME, 8100, 200).toString()
                        env.AUTO_PORT = pickPort(env.BRANCH_NAME, 8500, 200).toString()
                    }

                    env.WEB_BACK_DST = "${env.DEPLOY_ROOT}\\${env.BID}\\webservice\\backend"
                    env.WEB_FRONT_DST = "C:\\nginx\\html\\tests\\${env.BID}"
                    env.AUTO_DST = "${env.DEPLOY_ROOT}\\${env.BID}\\autodoc"
                    env.URL_PREFIX = "/tests/${env.BID}/"
                    
                    // AUTODOC_SERVICE_URL 환경변수 설정 (모든 브랜치 통합)
                    if (env.BRANCH_NAME == 'main' || env.BRANCH_NAME == 'master') {
                        env.AUTODOC_SERVICE_URL = "http://localhost:8001"
                    } else {
                        // develop, feature/*, hotfix/* 등은 동적 포트 사용
                        env.AUTODOC_SERVICE_URL = "http://localhost:${env.AUTO_PORT}"
                    }
                    
                    echo """
                    ===========================================
                    🔧 브랜치 설정
                    ===========================================
                    • 브랜치: ${env.BRANCH_NAME}
                    • 테스트 인스턴스: ${env.IS_TEST}
                    • BID: ${env.BID}
                    • Backend Port: ${env.BACK_PORT}
                    • AutoDoc Port: ${env.AUTO_PORT}
                    • AutoDoc Service URL: ${env.AUTODOC_SERVICE_URL}
                    • URL Prefix: ${env.URL_PREFIX}
                    ===========================================
                    """
                }
            }
        }
        
        stage('🚀 1단계: 독립 서비스 병렬 빌드') {
            parallel {
                stage('🔧 AutoDoc Service CI/CD') {
                    when {
                        expression { env.AUTODOC_CHANGED == 'true' || env.ROOT_CHANGED == 'true' || env.INFRA_CHANGED == 'true' }
                    }
                    steps {
                        script {
                            try {
                                echo "AutoDoc Service 빌드/배포 시작"
                                build job: 'autodoc_service-pipeline', 
                                      parameters: [string(name: 'BRANCH', value: env.BRANCH_NAME)]
                                
                                env.AUTODOC_DEPLOY_STATUS = 'SUCCESS'
                                echo "AutoDoc Service 배포 성공"
                                
                            } catch (Exception e) {
                                env.AUTODOC_DEPLOY_STATUS = 'FAILED'
                                env.FAILED_SERVICES += 'AutoDoc '
                                echo "AutoDoc Service 배포 실패: ${e.getMessage()}"
                                // AutoDoc 빌드 실패 시 파이프라인 실패
                                error("AutoDoc Service 빌드/배포 실패: ${e.getMessage()}")
                            }
                        }
                    }
                }
                
                stage('🌐 Webservice Backend CI/CD') {
                    when {
                        expression { env.WEBSERVICE_BACKEND_CHANGED == 'true' || env.ROOT_CHANGED == 'true' || env.INFRA_CHANGED == 'true' }
                    }
                    steps {
                        script {
                            try {
                                echo "Webservice Backend 빌드/배포 시작"
                                build job: 'webservice-backend-pipeline',
                                      parameters: [
                                          string(name: 'BRANCH', value: env.BRANCH_NAME),
                                          string(name: 'AUTODOC_SERVICE_URL', value: env.AUTODOC_SERVICE_URL)
                                      ]
                                
                                env.WEBSERVICE_BACKEND_STATUS = 'SUCCESS'
                                echo "Webservice Backend 배포 성공"
                                
                            } catch (Exception e) {
                                env.WEBSERVICE_BACKEND_STATUS = 'FAILED'
                                env.FAILED_SERVICES += 'WebBackend '
                                env.CRITICAL_FAILURE = 'true'  // Critical 서비스 실패
                                echo "Webservice Backend 배포 실패: ${e.getMessage()}"
                                // Webservice Backend 빌드 실패 시 파이프라인 실패
                                error("Webservice Backend 빌드/배포 실패: ${e.getMessage()}")
                            }
                        }
                    }
                }
                
                stage('🎨 Webservice Frontend CI/CD') {
                    when {
                        expression { env.WEBSERVICE_FRONTEND_CHANGED == 'true' || env.ROOT_CHANGED == 'true' || env.INFRA_CHANGED == 'true' }
                    }
                    steps {
                        script {
                            try {
                                echo "Webservice Frontend 빌드/배포 시작"
                                def frontendBuild = build job: "webservice-frontend-pipeline",
                                      parameters: [string(name: 'BRANCH', value: env.BRANCH_NAME)]
                                
                                env.WEBSERVICE_FRONTEND_STATUS = 'SUCCESS'
                                echo "Webservice Frontend 배포 성공"
                                
                                // 테스트 인스턴스용 프론트엔드 아티팩트 복사
                                if (env.IS_TEST == 'true') {
                                    echo "테스트 인스턴스용 프론트엔드 아티팩트 복사 시작..."
                                    
                                    copyArtifacts(
                                        projectName: 'webservice-frontend-pipeline',
                                        selector: lastSuccessful(),
                                        // selector: [$class: 'LastSuccessfulBuildSelector'],
                                        target: 'webservice/',
                                        flatten: true,
                                        fingerprintArtifacts: true
                                    )
                                    
                                    // 아티팩트 존재 확인
                                    bat '''
                                    if exist "%WORKSPACE%\\webservice\\frontend.zip" (
                                        echo "frontend.zip 복사 성공: %WORKSPACE%\\webservice\\frontend.zip"
                                    ) else (
                                        echo "frontend.zip 복사 실패"
                                        exit 1
                                    )
                                    '''
                                    
                                    echo "테스트 인스턴스용 프론트엔드 아티팩트 복사 완료"
                                }
                                
                            } catch (Exception e) {
                                env.WEBSERVICE_FRONTEND_STATUS = 'FAILED'
                                env.FAILED_SERVICES += 'WebFrontend '
                                echo "Webservice Frontend 배포 실패: ${e.getMessage()}"
                                // Webservice Frontend 빌드 실패 시 파이프라인 실패
                                error("Webservice Frontend 빌드/배포 실패: ${e.getMessage()}")
                            }
                        }
                    }
                }
                
                stage('⚡ CLI CI/CD') {
                    when {
                        expression { env.CLI_CHANGED == 'true' || env.ROOT_CHANGED == 'true' || env.INFRA_CHANGED == 'true' }
                    }
                    steps {
                        script {
                            try {
                                echo "CLI 빌드/패키징 시작 (독립 파이프라인 호출)"
                                
                                def cliBaseUrl = 'https://cm-docs.cloud' // 기본값은 프로덕션 URL
                                if (env.IS_TEST == 'true') {
                                    // is_test가 true이면 브랜치별 테스트 URL 생성
                                    cliBaseUrl += "/tests/${env.BID}"
                                }
                                echo "🚀 CLI에 주입할 Base URL: ${cliBaseUrl}"
                                // CLI 전용 파이프라인 호출
                                build job: 'cli-pipeline',
                                      parameters: [
                                        string(name: 'BRANCH', value: env.BRANCH_NAME),
                                        string(name: 'BASE_URL', value: cliBaseUrl)
                                    ],
                                    wait: true
                                
                                env.CLI_BUILD_STATUS = 'SUCCESS'
                                echo "CLI 빌드/패키징 성공"
                                
                            } catch (Exception e) {
                                env.CLI_BUILD_STATUS = 'FAILED'
                                env.FAILED_SERVICES += 'CLI '
                                echo "CLI 빌드/패키징 실패: ${e.getMessage()}"
                                // Non-Critical 서비스이므로 다른 서비스는 계속 진행
                            }
                        }
                    }
                } 
            } 
        }
        
        
        stage('🔍 2단계: 통합 테스트') {
            when {
                expression { 
                    (env.WEBSERVICE_CHANGED == 'true' || 
                     env.AUTODOC_CHANGED == 'true' || 
                     env.ROOT_CHANGED == 'true' || 
                     env.INFRA_CHANGED == 'true') &&
                    env.CRITICAL_FAILURE == 'false'  // Critical 서비스 성공 시에만 실행
                }
            }
            parallel {
                stage('E2E 테스트') {
                    when {
                        allOf {
                            expression { env.WEBSERVICE_FRONTEND_CHANGED == 'true' }
                            expression { env.WEBSERVICE_BACKEND_STATUS == 'SUCCESS' }
                            expression { env.WEBSERVICE_FRONTEND_STATUS == 'SUCCESS' }
                        }
                    }
                    steps {
                        script {
                            try {
                                echo "Webservice E2E 테스트 시작 (Backend + Frontend 성공 확인됨)"
                                
                                // E2E 테스트 실행 전 서비스 준비 대기
                                sleep(time: 30, unit: 'SECONDS')
                                
                                dir("${WORKSPACE}\\webservice\\frontend") {
                                    bat 'npm run test:e2e'
                                }
                                
                                env.E2E_TEST_STATUS = 'SUCCESS'
                                echo "E2E 테스트 성공"
                                
                            } catch (Exception e) {
                                env.E2E_TEST_STATUS = 'FAILED'
                                echo "E2E 테스트 실패: ${e.getMessage()}"
                            }
                        }
                    }
                }
                
                stage('서비스 간 통신 테스트') {
                    steps {
                        script {
                            try {
                                echo "서비스 간 통신 테스트 시작"
                                
                                // 서비스 안정화 대기
                                sleep(time: 15, unit: 'SECONDS')
                                
                                // 각 서비스 헬스체크 (개선된 테스트)
                                def services = [:]
                                if (env.AUTODOC_DEPLOY_STATUS == 'SUCCESS') {
                                    services['AutoDoc'] = env.AUTODOC_HEALTH_URL
                                }
                                if (env.WEBSERVICE_BACKEND_STATUS == 'SUCCESS') {
                                    services['Backend'] = env.WEBSERVICE_HEALTH_URL
                                }
                                if (env.WEBSERVICE_FRONTEND_STATUS == 'SUCCESS') {
                                    services['Frontend'] = env.WEBSERVICE_FRONTEND_URL
                                }
                                
                                def allHealthy = true
                                def healthyCount = 0
                                def totalCount = services.size()
                                
                                services.each { name, url ->
                                    def servicePassed = false
                                    for (int i = 0; i < 3; i++) {
                                        try {
                                            def response = powershell(
                                                script: """
                                                    \$env:PYTHONIOENCODING='utf-8'
                                                    try {
                                                        \$result = Invoke-WebRequest -Uri '${url}' -UseBasicParsing -TimeoutSec 10
                                                        Write-Output \$result.StatusCode
                                                    } catch {
                                                        Write-Output "500"
                                                    }
                                                """,
                                                returnStdout: true
                                            ).trim()
                                            
                                            if (response == "200") {
                                                echo "${name} 서비스 정상 (HTTP 200, ${i+1}번째 시도)"
                                                servicePassed = true
                                                healthyCount++
                                                break
                                            } else {
                                                echo "${name} 서비스 응답 이상 (HTTP ${response}, ${i+1}번째 시도)"
                                            }
                                        } catch (Exception e) {
                                            echo "${name} 서비스 접근 불가: ${e.getMessage()} (${i+1}번째 시도)"
                                        }
                                        
                                        if (i < 2) sleep(time: 5, unit: 'SECONDS')
                                    }
                                    
                                    if (!servicePassed) {
                                        allHealthy = false
                                    }
                                }
                                
                                if (allHealthy && healthyCount == totalCount) {
                                    env.INTEGRATION_TEST_STATUS = 'SUCCESS'
                                    echo "모든 배포된 서비스 정상 동작 확인 (${healthyCount}/${totalCount})"
                                } else if (healthyCount > 0) {
                                    env.INTEGRATION_TEST_STATUS = 'PARTIAL'
                                    echo "부분 성공: ${healthyCount}/${totalCount} 서비스 정상"
                                } else {
                                    env.INTEGRATION_TEST_STATUS = 'FAILED'
                                    echo "모든 서비스 헬스체크 실패"
                                }
                                
                            } catch (Exception e) {
                                env.INTEGRATION_TEST_STATUS = 'FAILED'
                                echo "통합 테스트 실패: ${e.getMessage()}"
                            }
                        }
                    }
                }
            }
        }
        
        stage('🚀 4단계: 스마트 배포 완료') {
            steps {
                script {
                    // 배포 상태 종합 분석
                    def successfulServices = []
                    def failedServices = []
                    def skippedServices = []
                    
                    // 각 서비스 상태 분석
                    if (env.AUTODOC_CHANGED == 'true') {
                        if (env.AUTODOC_DEPLOY_STATUS == 'SUCCESS') {
                            successfulServices.add('AutoDoc Service (Port 8001)')
                        } else {
                            failedServices.add('AutoDoc Service')
                        }
                    } else {
                        skippedServices.add('AutoDoc Service (변경 없음)')
                    }
                    
                    if (env.WEBSERVICE_CHANGED == 'true') {
                        if (env.WEBSERVICE_BACKEND_STATUS == 'SUCCESS') {
                            successfulServices.add('Webservice Backend (Port 8000)')
                        } else {
                            failedServices.add('Webservice Backend')
                        }
                        
                        if (env.WEBSERVICE_FRONTEND_STATUS == 'SUCCESS') {
                            successfulServices.add('Webservice Frontend (Port 80)')
                        } else if (env.WEBSERVICE_FRONTEND_STATUS == 'FAILED') {
                            failedServices.add('Webservice Frontend')
                        } else {
                            skippedServices.add('Webservice Frontend (Backend 실패로 스킵)')
                        }
                    } else {
                        skippedServices.add('Webservice (변경 없음)')
                    }
                    
                    if (env.CLI_CHANGED == 'true') {
                        if (env.CLI_BUILD_STATUS == 'SUCCESS') {
                            successfulServices.add('CLI Build (실행파일 생성)')
                        } else {
                            failedServices.add('CLI Build')
                        }
                    } else {
                        skippedServices.add('CLI (변경 없음)')
                    }
                    
                    // 최종 배포 상태 결정
                    if (env.CRITICAL_FAILURE == 'true') {
                        env.DEPLOYMENT_STATUS = 'CRITICAL_FAILURE'
                        echo """
                        ❌ CRITICAL FAILURE - Webservice 핵심 서비스 실패
                        ===========================================
                        """
                    } else if (failedServices.size() > 0) {
                        env.DEPLOYMENT_STATUS = 'PARTIAL_SUCCESS'
                        echo """
                        ⚠️ PARTIAL SUCCESS - 일부 서비스 실패
                        ===========================================
                        """
                    } else if (successfulServices.size() > 0) {
                        env.DEPLOYMENT_STATUS = 'SUCCESS'
                        echo """
                        ✅ DEPLOYMENT SUCCESS
                        ===========================================
                        """
                    } else {
                        env.DEPLOYMENT_STATUS = 'NO_CHANGES'
                        echo """
                        ℹ️ NO DEPLOYMENT NEEDED - 변경사항 없음
                        ===========================================
                        """
                    }
                    
                    // 상세 결과 출력
                    if (successfulServices.size() > 0) {
                        echo "✅ 성공한 서비스:"
                        successfulServices.each { service ->
                            echo "  • ${service}"
                        }
                    }
                    
                    if (failedServices.size() > 0) {
                        echo "❌ 실패한 서비스:"
                        failedServices.each { service ->
                            echo "  • ${service}"
                        }
                    }
                    
                    if (skippedServices.size() > 0) {
                        echo "⏭️ 스킵된 서비스:"
                        skippedServices.each { service ->
                            echo "  • ${service}"
                        }
                    }
                    
                    // 테스트 결과
                    echo ""
                    echo "🧪 테스트 결과:"
                    echo "  • 통합 테스트: ${env.INTEGRATION_TEST_STATUS ?: 'SKIPPED'}"
                    echo "  • E2E 테스트: ${env.E2E_TEST_STATUS ?: 'SKIPPED'}"
                    
                    echo "==========================================="
                }
            }
        }        
        
        stage('🧪 Deploy Test Instance') {
            when { 
                expression { env.IS_TEST == 'true' } 
            }
            steps {
                script {
                    echo """
                    ===========================================
                    🚀 테스트 인스턴스 병렬 배포 시작
                    ===========================================
                    • 브랜치: ${env.BRANCH_NAME}
                    • BID: ${env.BID}
                    • 변경된 서비스 감지:
                      - Frontend: ${env.WEBSERVICE_FRONTEND_CHANGED}
                      - Backend: ${env.WEBSERVICE_BACKEND_CHANGED}
                      - AutoDoc: ${env.AUTODOC_CHANGED}
                    ===========================================
                    """
                    
                    // 배포 상태 공유를 위한 Map
                    def deployResults = [:]
                    def servicesChanged = []
                    
                    // 각 서비스 변경 여부와 빌드 성공 여부 확인
                    def deployFrontend = (env.WEBSERVICE_FRONTEND_CHANGED == 'true' && env.WEBSERVICE_FRONTEND_STATUS == 'SUCCESS')
                    def deployBackend = (env.WEBSERVICE_BACKEND_CHANGED == 'true' && env.WEBSERVICE_BACKEND_STATUS == 'SUCCESS')
                    def deployAutodoc = (env.AUTODOC_CHANGED == 'true' && env.AUTODOC_DEPLOY_STATUS == 'SUCCESS')
                    
                    // 전체 재배포가 필요한 경우 (인프라 또는 루트 변경)
                    if (env.INFRA_CHANGED == 'true' || env.ROOT_CHANGED == 'true') {
                        echo "인프라 또는 루트 설정 변경 감지 - 모든 서비스 재배포"
                        deployFrontend = true
                        deployBackend = true
                        deployAutodoc = true
                        servicesChanged = ['Frontend', 'Backend', 'AutoDoc']
                    } else {
                        if (deployFrontend) servicesChanged.add('Frontend')
                        if (deployBackend) servicesChanged.add('Backend')
                        if (deployAutodoc) servicesChanged.add('AutoDoc')
                    }
                    
                    if (servicesChanged.size() == 0) {
                        echo """
                        테스트 인스턴스 배포 스킵
                        - 변경된 서비스가 없거나 빌드가 실패한 서비스만 있습니다.
                        - Frontend 빌드 상태: ${env.WEBSERVICE_FRONTEND_STATUS ?: 'N/A'}
                        - Backend 빌드 상태: ${env.WEBSERVICE_BACKEND_STATUS ?: 'N/A'}
                        - AutoDoc 빌드 상태: ${env.AUTODOC_DEPLOY_STATUS ?: 'N/A'}
                        """
                        return
                    }
                    
                    echo "병렬 배포할 서비스: ${servicesChanged.join(', ')}"
                    
                    // Frontend 아티팩트 확인 (Frontend 배포 시에만)
                    if (deployFrontend) {
                        def frontendZipExists = fileExists("${WORKSPACE}/webservice/frontend.zip")
                        if (!frontendZipExists) {
                            echo """
                            경고: frontend.zip 파일이 없습니다.
                            Frontend 배포를 스킵합니다.
                            """
                            deployFrontend = false
                            servicesChanged.remove('Frontend')
                        } else {
                            echo "✓ frontend.zip 아티팩트 확인 완료"
                        }
                    }
                    
                    // 포트 유효성 검사 제거 - 각 배포 스크립트에서 서비스 정리를 이미 수행함
                    // deploy_webservice_only.ps1과 deploy_autodoc_only.ps1이 기존 서비스를 자동으로 정리하므로
                    // 사전 포트 검사는 불필요하며 오히려 충돌을 일으킴
                    
                    // 공통 초기화 수행 (병렬 배포 전)
                    echo "📋 공통 초기화 작업 수행 중..."
                    try {
                        bat """
                        chcp 65001 >NUL
powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "\$env:PYTHONIOENCODING='utf-8'; & {. '.\\scripts\\deploy_common.ps1' -Bid '%BID%' -Nssm '%NSSM_PATH%' -Nginx '%NGINX_PATH%' -PackagesRoot 'C:\\deploys\\tests\\%BID%\\packages'; Cleanup-OldBranchFolders -Bid '%BID%' -Nssm '%NSSM_PATH%'}"
                        """
                        echo "✓ 공통 초기화 완료"
                    } catch (Exception initError) {
                        error("공통 초기화 실패: ${initError.getMessage()}")
                    }
                    
                    // 병렬 배포 실행
                    def parallelDeployments = [:]
                    
                    // Frontend 배포 작업
                    if (deployFrontend) {
                        parallelDeployments['Frontend'] = {
                            echo "🎨 Frontend 배포 시작..."
                            try {
                                bat """
                                chcp 65001 >NUL
                                powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "scripts\\deploy_frontend_only.ps1" ^
                                    -Bid "%BID%" ^
                                    -WebSrc "%WORKSPACE%\\webservice" ^
                                    -WebFrontDst "%WEB_FRONT_DST%" ^
                                    -UrlPrefix "%URL_PREFIX%" ^
                                    -PackagesRoot "C:\\deploys\\tests\\%BID%\\packages"
                                """
                                deployResults['Frontend'] = 'SUCCESS'
                                echo "✅ Frontend 배포 성공"
                            } catch (Exception e) {
                                deployResults['Frontend'] = 'FAILED'
                                echo """
                                ❌ Frontend 배포 실패
                                ===========================================
                                에러: ${e.getMessage()}
                                
                                📋 Frontend 배포 문제 해결:
                                1. frontend.zip 파일 확인:
                                   - 경로: ${WORKSPACE}\\webservice\\frontend.zip
                                   - 파일 존재 여부와 크기 확인
                                
                                2. 배포 디렉토리 권한:
                                   - 대상: ${env.WEB_FRONT_DST}
                                   - nginx 프로세스 접근 권한 확인
                                
                                3. 디스크 공간 확인:
                                   - C: 드라이브 여유 공간 확인
                                ===========================================
                                """
                                throw e
                            }
                        }
                    }
                    
                    // Backend 배포 작업
                    if (deployBackend) {
                        parallelDeployments['Backend'] = {
                            echo "⚙️ Backend 배포 시작..."
                            try {
                                bat """
                                chcp 65001 >NUL
powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "\$env:PYTHONIOENCODING='utf-8'; & '.\\scripts\\deploy_webservice_only.ps1' -Bid '%BID%' -BackPort %BACK_PORT% -Py '%PY_PATH%' -Nssm '%NSSM_PATH%' -Nginx '%NGINX_PATH%' -WebSrc '%WORKSPACE%\\webservice' -WebBackDst '%WEB_BACK_DST%' -PackagesRoot 'C:\\deploys\\tests\\%BID%\\packages' -AutoDocServiceUrl '%AUTODOC_SERVICE_URL%' -UrlPrefix '%URL_PREFIX%'"
                                """
                                deployResults['Backend'] = 'SUCCESS'
                                echo "✅ Backend 배포 성공"
                            } catch (Exception e) {
                                deployResults['Backend'] = 'FAILED'
                                echo """
                                ❌ Backend 배포 실패
                                ===========================================
                                에러: ${e.getMessage()}
                                포트: ${env.BACK_PORT}
                                
                                📋 Backend 배포 문제 해결:
                                1. 포트 충돌 확인:
                                   - 포트 ${env.BACK_PORT} 사용 확인: netstat -ano | findstr ${env.BACK_PORT}
                                   - 기존 서비스 중지: nssm stop cm-web-${env.BID}
                                
                                2. 프로세스 정리:
                                   - Python 프로세스 확인: tasklist | findstr python
                                   - 강제 종료: taskkill /f /im python.exe
                                
                                3. 서비스 상태 확인:
                                   - 서비스 조회: sc query cm-web-${env.BID}
                                   - 수동 제거: nssm remove cm-web-${env.BID} confirm
                                
                                4. 권한 문제:
                                   - 배포 경로: ${env.WEB_BACK_DST}
                                   - NSSM 실행 권한 확인
                                ===========================================
                                """
                                throw e
                            }
                        }
                    }
                    
                    // AutoDoc 배포 작업
                    if (deployAutodoc) {
                        parallelDeployments['AutoDoc'] = {
                            echo "📄 AutoDoc 배포 시작..."
                            try {
                                bat """
                                chcp 65001 >NUL
powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "\$env:PYTHONIOENCODING='utf-8'; & '.\\scripts\\deploy_autodoc_only.ps1' -Bid '%BID%' -AutoPort %AUTO_PORT% -Py '%PY_PATH_312%' -Nssm '%NSSM_PATH%' -Nginx '%NGINX_PATH%' -AutoSrc '%WORKSPACE%\\autodoc_service' -AutoDst '%AUTO_DST%' -PackagesRoot 'C:\\deploys\\tests\\%BID%\\packages'"
                                """
                                deployResults['AutoDoc'] = 'SUCCESS'
                                echo "✅ AutoDoc 배포 성공"
                            } catch (Exception e) {
                                deployResults['AutoDoc'] = 'FAILED'
                                echo """
                                ❌ AutoDoc 배포 실패
                                ===========================================
                                에러: ${e.getMessage()}
                                포트: ${env.AUTO_PORT}
                                
                                📋 AutoDoc 배포 문제 해결:
                                1. 포트 충돌 확인:
                                   - 포트 ${env.AUTO_PORT} 사용 확인: netstat -ano | findstr ${env.AUTO_PORT}
                                   - 기존 서비스 중지: nssm stop cm-autodoc-${env.BID}
                                
                                2. 템플릿 파일 확인:
                                   - 템플릿 경로: C:\\deploys\\data\\autodoc_service\\templates\\
                                   - 템플릿 파일 존재 여부 확인
                                
                                3. Python 환경:
                                   - Python 3.12 설치 확인
                                   - 가상환경 경로: ${env.AUTO_DST}\\.venv312
                                
                                4. 서비스 상태:
                                   - 서비스 조회: sc query cm-autodoc-${env.BID}
                                   - 수동 제거: nssm remove cm-autodoc-${env.BID} confirm
                                ===========================================
                                """
                                throw e
                            }
                        }
                    }
                    
                    if (parallelDeployments.size() > 0) {
                        try {
                            // 병렬 실행
                            parallel parallelDeployments

                            // Nginx 설정은 각 서비스 배포 스크립트에서 개별적으로 처리됨
                            // deploy_webservice_only.ps1과 deploy_autodoc_only.ps1이 각각
                            // 서비스별 분리된 nginx 설정 파일을 생성하므로 충돌 없음
                            echo "✅ 병렬 배포 완료 - 각 서비스별 nginx 설정 적용됨"
                            
                            // 배포 후 포트 상태 검증도 제거 - 서비스 헬스체크로 충분함
                            // Test-ServiceHealth가 이미 포트 상태를 확인하므로 중복 검사 불필요
                            
                            // 최종 서비스 상태 확인
                            echo "🔍 최종 서비스 상태 확인 중..."
                            
                            // 서비스 헬스체크 파라미터 구성
                            def healthCheckCmd = ". '.\\scripts\\deploy_common.ps1' -Bid '%BID%' -Nssm '%NSSM_PATH%' -Nginx '%NGINX_PATH%' -PackagesRoot 'C:\\deploys\\tests\\%BID%\\packages'; Test-ServiceHealth"
                            
                            if (deployBackend && env.BACK_PORT) {
                                healthCheckCmd += " -BackPort ${env.BACK_PORT}"
                            }
                            // BackPort가 없으면 파라미터 자체를 전달하지 않음

                            if (deployAutodoc && env.AUTO_PORT) {
                                healthCheckCmd += " -AutoPort ${env.AUTO_PORT}"
                            }
                            // AutoPort가 없으면 파라미터 자체를 전달하지 않음
                            
                            healthCheckCmd += " -Bid '%BID%' -Nssm '%NSSM_PATH%'"
                            
                            bat """
                            chcp 65001 >NUL
powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "\$env:PYTHONIOENCODING='utf-8'; & {${healthCheckCmd}}"
                            """
                            
                            // 성공한 서비스들 로그
                            def successfulServices = []
                            def failedServices = []
                            deployResults.each { service, status ->
                                if (status == 'SUCCESS') {
                                    successfulServices.add(service)
                                } else {
                                    failedServices.add(service)
                                }
                            }
                            
                            def deploymentSummary = """
                            ===========================================
                            ✅ 병렬 배포 완료
                            ===========================================
                            • 성공한 서비스: ${successfulServices.join(', ')}
                            ${failedServices.size() > 0 ? "• 실패한 서비스: ${failedServices.join(', ')}" : ""}
                            • 배포 시간: 병렬 처리로 단축
                            """
                            
                            // 포트 정보 추가
                            if (deployBackend && env.BACK_PORT) {
                                deploymentSummary += "\n• Backend 포트: ${env.BACK_PORT}"
                            }
                            if (deployAutodoc && env.AUTO_PORT) {
                                deploymentSummary += "\n• AutoDoc 포트: ${env.AUTO_PORT}"
                            }
                            
                            deploymentSummary += """
                            ===========================================
                            """
                            
                            echo deploymentSummary
                            
                        } catch (Exception e) {
                            // 구체적인 에러 분석 및 해결 가이드 제공
                            def errorMessage = e.getMessage()
                            def errorAnalysis = analyzeDeploymentError(errorMessage, deployResults)
                            
                            echo """
                            ❌ 병렬 배포 실패 - 상세 분석
                            ===========================================
                            에러 메시지: ${errorMessage}
                            실패한 배포 단계: ${deployResults}
                            
                            ${errorAnalysis.diagnosis}
                            
                            해결 방법:
                            ${errorAnalysis.solution}
                            
                            ⚠️ 배포가 중단되었습니다. 위 해결 방법을 적용한 후 다시 시도해주세요.
                            ===========================================
                            """
                            
                            // 즉시 실패 처리 (폴백 없음)
                            error("테스트 인스턴스 배포 실패: ${errorMessage}")
                        }
                    } else {
                        echo "배포할 서비스가 없습니다."
                    }
                }
                
                echo "TEST URL: https://<YOUR-DOMAIN>${env.URL_PREFIX}"
            }
        }
        

        
        stage('🔍 배포 상태 확인') {
            steps {
                script {
                    echo "최종 배포 상태 확인 중..."
                    
                    // 배포된 서비스들의 최종 상태 점검
                    def finalReport = []
                    
                    if (env.AUTODOC_CHANGED == 'true') {
                        def autodocStatus = env.AUTODOC_DEPLOY_STATUS ?: 'UNKNOWN'
                        finalReport.add("AutoDoc Service: ${autodocStatus}")
                    }
                    
                    if (env.WEBSERVICE_CHANGED == 'true') {
                        def backendStatus = env.WEBSERVICE_BACKEND_STATUS ?: 'UNKNOWN'
                        def frontendStatus = env.WEBSERVICE_FRONTEND_STATUS ?: 'UNKNOWN'
                        finalReport.add("Webservice Backend: ${backendStatus}")
                        finalReport.add("Webservice Frontend: ${frontendStatus}")
                    }
                    
                    if (env.CLI_CHANGED == 'true') {
                        def cliStatus = env.CLI_BUILD_STATUS ?: 'UNKNOWN'
                        finalReport.add("CLI Build: ${cliStatus}")
                    }
                    
                    echo """
                    ===========================================
                    📊 최종 배포 리포트
                    ===========================================
                    ${finalReport.join('\n')}
                    
                    통합 테스트: ${env.INTEGRATION_TEST_STATUS ?: 'SKIPPED'}
                    E2E 테스트: ${env.E2E_TEST_STATUS ?: 'SKIPPED'}
                    
                    실패한 서비스: ${env.FAILED_SERVICES ?: 'NONE'}
                    ===========================================
                    """
                }
            }
        }
    }
    
    post {
        success {
            script {
                def successMessage = """
                🎉 CM-Docs 통합 배포 성공!
                
                📅 빌드: ${BUILD_NUMBER}
                🌿 브랜치: ${env.BRANCH_NAME}
                ⏰ 시간: ${new Date()}
                
                배포된 서비스:
                ${env.AUTODOC_CHANGED == 'true' ? '• AutoDoc Service (Port 8001)' : ''}
                ${env.WEBSERVICE_CHANGED == 'true' ? '• Webservice Backend (Port 8000)\n• Webservice Frontend (Port 80)' : ''}
                ${env.CLI_CHANGED == 'true' ? '• CLI Tools (빌드 완료)' : ''}
                """
                
                echo successMessage
                
                // 슬랙 알림 (옵션)
                // slackSend channel: '#deployment', message: successMessage
            }
        }
        
        failure {
            script {
                def failureMessage = """
                ❌ CM-Docs 통합 배포 실패
                
                📅 빌드: ${BUILD_NUMBER}
                🌿 브랜치: ${env.BRANCH_NAME}
                ⏰ 시간: ${new Date()}
                
                실패한 서비스: ${env.FAILED_SERVICES ?: 'UNKNOWN'}
                
                로그를 확인하여 문제를 해결해주세요.
                """
                
                echo failureMessage
                
                // 슬랙 알림 (옵션)
                // slackSend channel: '#alerts', message: failureMessage, color: 'danger'
            }
        }
        
        always {
            script {
                // 리소스 사용량 모니터링
                echo "=== 빌드 리소스 사용량 리포트 ==="
                try {
                    // Windows 시스템 리소스 확인
                    powershell """
                        Write-Host "메모리 사용량:"
                        Get-WmiObject -Class Win32_OperatingSystem | Select-Object @{Name="사용률(%)";Expression={[math]::Round(((\$_.TotalVisibleMemorySize - \$_.FreePhysicalMemory) / \$_.TotalVisibleMemorySize) * 100, 2)}}
                        
                        Write-Host "디스크 공간 (C 드라이브):"
                        Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'" | Select-Object @{Name="사용률(%)";Expression={[math]::Round(((\$_.Size - \$_.FreeSpace) / \$_.Size) * 100, 2)}}
                        
                        Write-Host "활성 Jenkins 워크스페이스:"
                        Get-ChildItem -Path "${WORKSPACE}" -Directory | Measure-Object | Select-Object Count
                    """
                } catch (Exception e) {
                    echo "리소스 모니터링 실패: ${e.getMessage()}"
                }
                
                // 휠하우스 잠금 해제 및 정리
                try {
                    powershell """
                        # 휠하우스 잠금 파일 제거
                        if (Test-Path "${env.WHEELHOUSE_PATH}\\.lock") {
                            Remove-Item "${env.WHEELHOUSE_PATH}\\.lock" -Force -ErrorAction SilentlyContinue
                            Write-Host "휠하우스 잠금 해제 완료"
                        }
                        
                        # 임시 빌드 파일 정리
                        Get-ChildItem -Path "${env.BACKUP_ROOT}" -Filter "*BUILD_${BUILD_NUMBER}*" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
                        Write-Host "임시 빌드 파일 정리 완료"
                    """
                } catch (Exception e) {
                    echo "리소스 정리 실패: ${e.getMessage()}"
                }
                
                // 아티팩트 보관 (향상된 패턴)
                try {
                    archiveArtifacts artifacts: '''
                        **/dist/*.whl,
                        **/dist/*.zip, 
                        **/dist/*.exe,
                        **/htmlcov/**,
                        **/coverage/**
                    ''', 
                    allowEmptyArchive: true, 
                    fingerprint: true,
                    onlyIfSuccessful: false
                    
                    echo "아티팩트 보관 완료 (빌드 ${BUILD_NUMBER})"
                } catch (Exception e) {
                    echo "아티팩트 보관 실패: ${e.getMessage()}"
                }
            }
            
            // 워크스페이스 정리 (폐쇄망 환경 고려)
            cleanWs(patterns: [
                [pattern: '**/node_modules', type: 'EXCLUDE'],  // 폐쇄망에서 재다운로드 어려움
                [pattern: '**/.venv*', type: 'EXCLUDE'],        // Python 환경 보존
                [pattern: '**/wheelhouse', type: 'EXCLUDE'],    // 휠하우스 보존
                [pattern: '**/logs', type: 'EXCLUDE'],          // 로그 보존
                [pattern: '**/.pytest_cache', type: 'INCLUDE'], // 임시 캐시 삭제
                [pattern: '**/temp*', type: 'INCLUDE'],         // 임시 파일 삭제
                [pattern: '**/*.tmp', type: 'INCLUDE']          // 임시 파일 삭제
            ])
            
            echo "워크스페이스 정리 완료 (폐쇄망 환경 고려)"
        }
    }
}

// 브랜치별 테스트 인스턴스 유틸 함수
@NonCPS
def sanitizeId(String s) {
    return s.replaceAll(/[^a-zA-Z0-9_-]/, '_')
}

@NonCPS
def pickPort(String b, int base, int span) {
    // Jenkins 보안 정책으로 CRC32 사용 불가, 간단한 해시 대체
    int hash = b.hashCode()
    if (hash < 0) hash = -hash  // 음수 처리
    return (int)(base + (hash % span))
}

@NonCPS
def analyzeDeploymentError(String errorMessage, Map deployResults) {
    def diagnosis = ""
    def solution = ""
    
    // AutoPort null 에러 분석
    if (errorMessage.contains("AutoPort") || errorMessage.contains("BackPort")) {
        diagnosis = """
        📌 포트 파라미터 전달 문제 감지
        - PowerShell에 잘못된 포트 값이 전달되었습니다
        - 'null' 문자열이 실제 null 대신 전달되어 발생한 문제입니다
        """
        solution = """
        1. PowerShell 파라미터에서 \$null 사용을 확인하세요
        2. Jenkins 환경변수가 올바르게 설정되었는지 확인하세요
        3. Port 할당 로직을 점검하세요 (pickPort 함수)
        """
    }
    
    // Permission denied 에러 분석
    else if (errorMessage.contains("Access is denied") || errorMessage.contains("Permission denied")) {
        diagnosis = """
        📌 파일 접근 권한 문제 감지
        - 서비스 프로세스가 완전히 종료되지 않아 파일이 잠겨있습니다
        - NSSM 서비스 중지 후 프로세스가 남아있는 상황입니다
        """
        solution = """
        1. NSSM 서비스를 수동으로 중지: nssm stop [서비스명]
        2. 프로세스 강제 종료: taskkill /f /im python.exe
        3. 잠금 파일 삭제 후 재시도하세요
        4. 서비스 중지 후 10초 이상 대기를 고려하세요
        """
    }
    
    // 서비스 등록 실패 분석
    else if (errorMessage.contains("service") && (errorMessage.contains("install") || errorMessage.contains("start"))) {
        diagnosis = """
        📌 NSSM 서비스 등록/시작 실패
        - 동일한 이름의 서비스가 이미 존재하거나
        - 서비스 설정에 문제가 있습니다
        """
        solution = """
        1. 기존 서비스 확인: sc query [서비스명]
        2. 기존 서비스 삭제: nssm remove [서비스명] confirm
        3. Windows 이벤트 로그를 확인하세요
        4. NSSM 로그를 확인하세요
        """
    }
    
    // 일반적인 배포 실패
    else {
        diagnosis = """
        📌 일반적인 배포 실패
        - 예상하지 못한 오류가 발생했습니다
        - 배포 단계별 상세 로그를 확인이 필요합니다
        """
        solution = """
        1. PowerShell 실행 정책을 확인하세요: Get-ExecutionPolicy
        2. UTF-8 인코딩 설정을 확인하세요
        3. 배포 스크립트 경로와 권한을 확인하세요
        4. Windows 서비스 상태를 확인하세요
        """
    }
    
    // 실패한 서비스별 추가 정보
    def failedServices = deployResults.findAll { key, value -> value == 'FAILED' }.keySet()
    if (failedServices.size() > 0) {
        diagnosis += """
        
        📊 실패한 서비스: ${failedServices.join(', ')}
        """
        solution += """
        
        실패한 서비스별 로그 확인:
        ${failedServices.collect { "- ${it}: C:\\deploys\\tests\\%BID%\\logs\\${it.toLowerCase()}-*.log" }.join('\n        ')}
        """
    }
    
    return [
        diagnosis: diagnosis.trim(),
        solution: solution.trim()
    ]
}
