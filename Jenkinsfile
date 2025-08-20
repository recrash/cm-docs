// cm-docs/Jenkinsfile - 통합 멀티브랜치 파이프라인
// Pseudo MSA 아키텍처에 맞춘 스마트 배포 시스템
pipeline {
    agent any
    
    environment {
        // 프로젝트 경로
        CM_DOCS_ROOT = 'C:\\Users\\recrash1325\\Documents\\deploys\\cm-docs'
        WEBSERVICE_PATH = "${CM_DOCS_ROOT}\\webservice"
        AUTODOC_PATH = "${CM_DOCS_ROOT}\\autodoc_service"
        
        // 서비스 URL
        WEBSERVICE_BACKEND_URL = 'http://localhost:8000'
        WEBSERVICE_FRONTEND_URL = 'http://localhost'
        AUTODOC_SERVICE_URL = 'http://localhost:8001'
        
        // 배포 상태 추적
        DEPLOYMENT_STATUS = 'NONE'
        FAILED_SERVICES = ''
    }
    
    stages {
        stage('소스코드 체크아웃 및 변경 감지') {
            steps {
                checkout scm
                script {
                    // 변경된 파일 분석
                    def changedFiles = []
                    try {
                        changedFiles = bat(
                            script: 'git diff HEAD~1 HEAD --name-only',
                            returnStdout: true
                        ).split('\n').findAll { it.trim() }
                    } catch (Exception e) {
                        echo "변경 감지 실패, 전체 빌드 실행: ${e.getMessage()}"
                        changedFiles = ['webservice/', 'autodoc_service/', 'cli/']
                    }
                    
                    // 서비스별 변경 감지
                    env.AUTODOC_CHANGED = changedFiles.any { it.contains('autodoc_service/') } ? 'true' : 'false'
                    env.WEBSERVICE_CHANGED = changedFiles.any { it.contains('webservice/') } ? 'true' : 'false'
                    env.CLI_CHANGED = changedFiles.any { it.contains('cli/') } ? 'true' : 'false'
                    env.ROOT_CHANGED = changedFiles.any { 
                        it.contains('Jenkinsfile') || it.contains('README.md') || it.contains('CLAUDE.md')
                    } ? 'true' : 'false'
                    
                    echo """
                    ===========================================
                    📊 변경 감지 결과
                    ===========================================
                    • AutoDoc Service: ${env.AUTODOC_CHANGED}
                    • Webservice: ${env.WEBSERVICE_CHANGED}
                    • CLI: ${env.CLI_CHANGED}
                    • Root/Config: ${env.ROOT_CHANGED}
                    
                    변경된 파일들:
                    ${changedFiles.join('\n')}
                    ===========================================
                    """
                }
            }
        }
        
        stage('🔧 AutoDoc Service CI/CD') {
            when {
                expression { env.AUTODOC_CHANGED == 'true' || env.ROOT_CHANGED == 'true' }
            }
            steps {
                script {
                    try {
                        echo "AutoDoc Service 빌드/배포 시작"
                        build job: 'autodoc-service-pipeline', 
                              parameters: [string(name: 'BRANCH', value: env.BRANCH_NAME)]
                        
                        env.AUTODOC_DEPLOY_STATUS = 'SUCCESS'
                        echo "AutoDoc Service 배포 성공"
                        
                    } catch (Exception e) {
                        env.AUTODOC_DEPLOY_STATUS = 'FAILED'
                        env.FAILED_SERVICES += 'AutoDoc '
                        echo "AutoDoc Service 배포 실패: ${e.getMessage()}"
                        // 실패해도 다른 서비스는 계속 진행
                    }
                }
            }
        }
        
        stage('🌐 Webservice CI/CD') {
            when {
                expression { env.WEBSERVICE_CHANGED == 'true' || env.ROOT_CHANGED == 'true' }
            }
            parallel {
                stage('Backend 빌드/배포') {
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
                                echo "Webservice Backend 배포 실패: ${e.getMessage()}"
                            }
                        }
                    }
                }
                
                stage('Frontend 빌드/배포') {
                    steps {
                        script {
                            try {
                                echo "Webservice Frontend 빌드/배포 시작"
                                build job: 'webservice-frontend-pipeline',
                                      parameters: [string(name: 'BRANCH', value: env.BRANCH_NAME)]
                                
                                env.WEBSERVICE_FRONTEND_STATUS = 'SUCCESS'
                                echo "Webservice Frontend 배포 성공"
                                
                            } catch (Exception e) {
                                env.WEBSERVICE_FRONTEND_STATUS = 'FAILED'
                                env.FAILED_SERVICES += 'WebFrontend '
                                echo "Webservice Frontend 배포 실패: ${e.getMessage()}"
                            }
                        }
                    }
                }
            }
        }
        
        stage('⚡ CLI CI/CD') {
            when {
                expression { env.CLI_CHANGED == 'true' || env.ROOT_CHANGED == 'true' }
            }
            steps {
                script {
                    try {
                        echo "CLI 빌드/패키징 시작"
                        
                        dir("${env.CM_DOCS_ROOT}\\cli") {
                            // CLI는 서비스 배포가 아닌 빌드만 실행
                            bat 'powershell -Command "& .\\.venv\\Scripts\\python.exe -m pytest --cov=ts_cli --cov-report=html"'
                            bat 'powershell -Command "& .\\.venv\\Scripts\\python.exe scripts/build.py"'
                        }
                        
                        env.CLI_BUILD_STATUS = 'SUCCESS'
                        echo "CLI 빌드 성공"
                        
                    } catch (Exception e) {
                        env.CLI_BUILD_STATUS = 'FAILED'
                        env.FAILED_SERVICES += 'CLI '
                        echo "CLI 빌드 실패: ${e.getMessage()}"
                    }
                }
            }
        }
        
        stage('🔍 통합 테스트') {
            when {
                expression { 
                    env.WEBSERVICE_CHANGED == 'true' || 
                    env.AUTODOC_CHANGED == 'true' || 
                    env.ROOT_CHANGED == 'true' 
                }
            }
            parallel {
                stage('E2E 테스트') {
                    when {
                        expression { env.WEBSERVICE_CHANGED == 'true' }
                    }
                    steps {
                        script {
                            try {
                                echo "Webservice E2E 테스트 시작"
                                
                                dir("${env.WEBSERVICE_PATH}\\frontend") {
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
                                
                                // 각 서비스 헬스체크
                                def services = [
                                    'AutoDoc': env.AUTODOC_SERVICE_URL,
                                    'Backend': env.WEBSERVICE_BACKEND_URL,
                                    'Frontend': env.WEBSERVICE_FRONTEND_URL
                                ]
                                
                                def allHealthy = true
                                services.each { name, url ->
                                    try {
                                        def response = bat(
                                            script: "curl -s -o nul -w \"%{http_code}\" ${url}/health || curl -s -o nul -w \"%{http_code}\" ${url}",
                                            returnStdout: true
                                        ).trim()
                                        
                                        if (response == "200") {
                                            echo "${name} 서비스 정상 (HTTP 200)"
                                        } else {
                                            echo "${name} 서비스 이상 (HTTP ${response})"
                                            allHealthy = false
                                        }
                                    } catch (Exception e) {
                                        echo "${name} 서비스 접근 불가: ${e.getMessage()}"
                                        allHealthy = false
                                    }
                                }
                                
                                if (allHealthy) {
                                    env.INTEGRATION_TEST_STATUS = 'SUCCESS'
                                    echo "모든 서비스 정상 동작 확인"
                                } else {
                                    env.INTEGRATION_TEST_STATUS = 'PARTIAL'
                                    echo "일부 서비스에 문제가 있습니다"
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
        
        stage('🚀 스마트 배포') {
            when {
                expression { 
                    env.FAILED_SERVICES == null || env.FAILED_SERVICES.trim() == ''
                }
            }
            steps {
                script {
                    echo """
                    ===========================================
                    🎯 배포 완료 요약
                    ===========================================
                    """
                    
                    if (env.AUTODOC_CHANGED == 'true') {
                        echo "✅ AutoDoc Service: 배포 완료 (Port 8001)"
                    }
                    
                    if (env.WEBSERVICE_CHANGED == 'true') {
                        echo "✅ Webservice Backend: 배포 완료 (Port 8000)"
                        echo "✅ Webservice Frontend: 배포 완료 (Port 80)"
                    }
                    
                    if (env.CLI_CHANGED == 'true') {
                        echo "✅ CLI: 빌드 완료 (dist/에서 실행파일 확인 가능)"
                    }
                    
                    env.DEPLOYMENT_STATUS = 'SUCCESS'
                    echo "===========================================\n스마트 배포 성공!"
                }
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
            // 아티팩트 보관
            script {
                try {
                    archiveArtifacts artifacts: '**/dist/*.whl, **/dist/*.zip, **/dist/*.exe', 
                                   allowEmptyArchive: true, followSymlinks: false
                } catch (Exception e) {
                    echo "아티팩트 보관 실패: ${e.getMessage()}"
                }
            }
            
            // 워크스페이스 정리
            cleanWs(patterns: [
                [pattern: '**/node_modules', type: 'EXCLUDE'],
                [pattern: '**/.venv*', type: 'EXCLUDE'],
                [pattern: '**/logs', type: 'EXCLUDE']
            ])
        }
    }
}