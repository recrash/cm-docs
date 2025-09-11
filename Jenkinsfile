// cm-docs/Jenkinsfile - 통합 멀티브랜치 파이프라인
// Pseudo MSA 아키텍처에 맞춘 스마트 배포 시스템
pipeline {
    agent any
    
    environment {
        // 통합 환경변수 관리
        CM_DOCS_ROOT = 'C:\\deploys\\cm-docs'
        WHEELHOUSE_PATH = 'C:\\deploys\\packages\\wheelhouse'
        BACKUP_ROOT = 'C:\\deploys\\backup'
        
        // 테스트 인스턴스 환경 (브랜치별)
        DEPLOY_ROOT = 'C:\\deploys\\tests'
        PY_PATH = '%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe'
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
        WEBSERVICE_BACKEND_URL = 'http://localhost:8000'
        WEBSERVICE_FRONTEND_URL = 'http://localhost'
        AUTODOC_SERVICE_URL = 'http://localhost:8001'
        
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
                    
                    // Webservice Backend 변경 감지 (frontend 제외)
                    env.WEBSERVICE_BACKEND_CHANGED = filteredFiles.any { 
                        (it.startsWith('webservice/') && !it.startsWith('webservice/frontend/')) || it == 'webservice/Jenkinsfile.backend'
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
                    
                    echo """
                    ===========================================
                    🔧 브랜치 설정
                    ===========================================
                    • 브랜치: ${env.BRANCH_NAME}
                    • 테스트 인스턴스: ${env.IS_TEST}
                    • BID: ${env.BID}
                    • Backend Port: ${env.BACK_PORT}
                    • AutoDoc Port: ${env.AUTO_PORT}
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
                                // Non-Critical 서비스이므로 다른 서비스는 계속 진행
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
                                      parameters: [string(name: 'BRANCH', value: env.BRANCH_NAME)]
                                
                                env.WEBSERVICE_BACKEND_STATUS = 'SUCCESS'
                                echo "Webservice Backend 배포 성공"
                                
                            } catch (Exception e) {
                                env.WEBSERVICE_BACKEND_STATUS = 'FAILED'
                                env.FAILED_SERVICES += 'WebBackend '
                                env.CRITICAL_FAILURE = 'true'  // Critical 서비스 실패
                                echo "Webservice Backend 배포 실패: ${e.getMessage()}"
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
                bat '''
                chcp 65001 >NUL
                powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "scripts\\deploy_test_env.ps1" ^
                    -Bid "%BID%" ^
                    -BackPort %BACK_PORT% ^
                    -AutoPort %AUTO_PORT% ^
                    -Py "%PY_PATH%" ^
                    -Nssm "%NSSM_PATH%" ^
                    -Nginx "%NGINX_PATH%" ^
                    -NginxConfDir "%NGINX_CONF_DIR%" ^
                    -WebSrc "%WORKSPACE%\\webservice" ^
                    -AutoSrc "%WORKSPACE%\\autodoc_service" ^
                    -WebBackDst "%WEB_BACK_DST%" ^
                    -WebFrontDst "%WEB_FRONT_DST%" ^
                    -AutoDst "%AUTO_DST%" ^
                    -UrlPrefix "%URL_PREFIX%" ^
                    -PackagesRoot "C:\\deploys\\tests\\%BID%\\packages"
                '''
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