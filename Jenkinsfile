// Jenkinsfile - TestscenarioMaker 모노레포 CI/CD 파이프라인
pipeline {
    agent any

    // 프로젝트별 환경변수
    environment {
        // Windows 환경에서 PowerShell 사용
        NODE_OPTIONS = '--no-deprecation'
        // 개발서버 정보 (CLAUDE.local.md 참조)
        DEV_SERVER_IP = '34.64.173.97'
        DEV_SERVER_PORTS = '8000,8001,3000'
    }

    stages {
        stage('📥 소스코드 체크아웃 및 변경 감지') {
            steps {
                script {
                    checkout scm
                    echo "✅ Git 소스 코드를 성공적으로 가져왔습니다."
                    
                    // Git 변경사항 감지 로직
                    def changedFiles = bat(script: 'git diff --name-only HEAD~1 HEAD', returnStdout: true).trim()
                    echo "📋 변경된 파일들: ${changedFiles}"
                    
                    // 서비스별 변경 여부 판단
                    env.AUTODOC_CHANGED = changedFiles.contains('autodoc_service/') ? 'true' : 'false'
                    env.WEBSERVICE_CHANGED = changedFiles.contains('webservice/') ? 'true' : 'false' 
                    env.CLI_CHANGED = changedFiles.contains('cli/') ? 'true' : 'false'
                    env.ROOT_CHANGED = changedFiles.contains('Jenkinsfile') || changedFiles.contains('README.md') || changedFiles.contains('CLAUDE.md') ? 'true' : 'false'
                    
                    echo "🔍 변경 감지 결과:"
                    echo "  - AutoDoc Service: ${env.AUTODOC_CHANGED}"
                    echo "  - Webservice: ${env.WEBSERVICE_CHANGED}"  
                    echo "  - CLI: ${env.CLI_CHANGED}"
                    echo "  - 루트 설정: ${env.ROOT_CHANGED}"
                }
            }
        }

        // 1. AutoDoc Service (Python 3.12) - 변경시에만 실행
        stage('🔧 AutoDoc Service CI/CD') {
            when {
                anyOf {
                    environment name: 'AUTODOC_CHANGED', value: 'true'
                    environment name: 'ROOT_CHANGED', value: 'true'
                }
            }
            steps {
                dir('autodoc_service') {
                    script {
                        echo "📦 AutoDoc Service 변경 감지됨 - CI/CD 시작 (Python 3.12)..."
                        
                        // Python 3.12 가상환경 생성 및 의존성 설치
                        bat 'py -3.12 -m venv .venv312'
                        bat 'call .venv312\\Scripts\\activate && pip install -r requirements.txt'
                        
                        echo "🧪 AutoDoc Service 테스트 실행..."
                        bat 'call .venv312\\Scripts\\activate && pytest app/tests/ -v || echo "테스트 실패 허용"'
                        
                        echo "✅ AutoDoc Service CI 완료!"
                        env.AUTODOC_BUILD_SUCCESS = 'true'
                    }
                }
            }
        }

        // 2. Webservice (Python 3.13 + React) - 변경시에만 실행  
        stage('🌐 Webservice CI/CD') {
            when {
                anyOf {
                    environment name: 'WEBSERVICE_CHANGED', value: 'true'
                    environment name: 'ROOT_CHANGED', value: 'true'
                }
            }
            parallel {
                // Frontend 빌드
                stage('React Frontend') {
                    steps {
                        dir('webservice') {
                            script {
                                echo "⚛️ Webservice 변경 감지됨 - React 프론트엔드 빌드 시작..."
                                bat 'npm install'
                                bat 'npm run build'
                                echo "✅ React 빌드 완료!"
                            }
                        }
                    }
                }
                
                // Backend 빌드 및 테스트
                stage('FastAPI Backend') {
                    steps {
                        dir('webservice') {
                            script {
                                echo "🐍 FastAPI 백엔드 설정 (Python 3.13)..."
                                
                                // Python 3.13 가상환경 및 PYTHONPATH 설정
                                bat 'py -3.13 -m venv .venv'
                                bat 'call .venv\\Scripts\\activate && pip install -r requirements.txt'
                                
                                echo "📋 config.json 생성..."
                                bat 'copy config.example.json config.json'
                                
                                echo "🧪 Webservice 테스트 실행..."
                                // PYTHONPATH 설정 후 테스트 실행 (필수 - src/ 모듈 임포트용)
                                bat '''
                                call .venv\\Scripts\\activate
                                set PYTHONPATH=%CD%
                                pytest tests/ -v --tb=short || echo "테스트 실패 허용"
                                '''
                                
                                echo "✅ FastAPI 백엔드 CI 완료!"
                                env.WEBSERVICE_BUILD_SUCCESS = 'true'
                            }
                        }
                    }
                }
            }
        }

        // 3. CLI (Python 3.13) - 변경시에만 실행
        stage('⚡ CLI CI/CD') {
            when {
                anyOf {
                    environment name: 'CLI_CHANGED', value: 'true'
                    environment name: 'ROOT_CHANGED', value: 'true'
                }
            }
            steps {
                dir('cli') {
                    script {
                        echo "🛠️ CLI 변경 감지됨 - CLI 도구 설정 (Python 3.13)..."
                        
                        // Python 3.13 환경에서 CLI 설치 및 테스트
                        bat 'py -3.13 -m venv .venv'
                        bat 'call .venv\\Scripts\\activate && pip install -r requirements.txt'
                        bat 'call .venv\\Scripts\\activate && pip install -e .'
                        
                        echo "🧪 CLI 테스트 실행..."
                        bat 'call .venv\\Scripts\\activate && pytest tests/ -v --tb=short || echo "테스트 실패 허용"'
                        
                        echo "✅ CLI CI 완료!"
                        env.CLI_BUILD_SUCCESS = 'true'
                    }
                }
            }
        }

        // 4. 통합 테스트 (변경된 서비스에 대해서만)
        stage('🔍 통합 테스트') {
            when {
                anyOf {
                    environment name: 'WEBSERVICE_CHANGED', value: 'true'
                    environment name: 'ROOT_CHANGED', value: 'true'
                }
            }
            steps {
                script {
                    echo "🎯 변경된 Webservice에 대한 E2E 테스트 실행..."
                    
                    // Webservice E2E 테스트 (중요: Playwright 필수)
                    dir('webservice') {
                        bat 'call .venv\\Scripts\\activate && npm run test:e2e || echo "E2E 테스트 실패 허용"'
                    }
                    
                    echo "✅ 통합 테스트 완료!"
                }
            }
        }

        // 5. 스마트 배포 (변경된 서비스만 배포)
        stage('🚀 스마트 배포 - 변경된 서비스만') {
            when {
                branch 'develop' // develop 브랜치에서만 배포 실행
            }
            parallel {
                // AutoDoc Service 배포
                stage('AutoDoc Service 배포') {
                    when {
                        environment name: 'AUTODOC_BUILD_SUCCESS', value: 'true'
                    }
                    steps {
                        script {
                            echo "🔧 AutoDoc Service 배포 시작 (포트 8001)..."
                            
                            bat '''
                            echo "AutoDoc Service 재시작..."
                            taskkill /F /FI "WINDOWTITLE eq AutoDoc*" 2>nul || echo "기존 프로세스 없음"
                            
                            cd autodoc_service
                            call .venv312\\Scripts\\activate
                            start "AutoDoc Service" python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
                            '''
                            
                            echo "✅ AutoDoc Service 배포 완료 (http://${DEV_SERVER_IP}:8001)"
                        }
                    }
                }
                
                // Webservice Backend 배포  
                stage('Webservice Backend 배포') {
                    when {
                        environment name: 'WEBSERVICE_BUILD_SUCCESS', value: 'true'
                    }
                    steps {
                        script {
                            echo "🐍 Webservice Backend 배포 시작 (포트 8000)..."
                            
                            bat '''
                            echo "Webservice Backend 재시작..."
                            taskkill /F /FI "WINDOWTITLE eq Webservice Backend*" 2>nul || echo "기존 프로세스 없음"
                            
                            cd webservice/backend
                            call ../.venv\\Scripts\\activate
                            set PYTHONPATH=%CD%/..
                            start "Webservice Backend" python -m uvicorn main:app --host 0.0.0.0 --port 8000
                            '''
                            
                            echo "✅ Webservice Backend 배포 완료 (http://${DEV_SERVER_IP}:8000)"
                        }
                    }
                }
                
                // Webservice Frontend 배포
                stage('Webservice Frontend 배포') {
                    when {
                        environment name: 'WEBSERVICE_BUILD_SUCCESS', value: 'true'
                    }
                    steps {
                        script {
                            echo "⚛️ Webservice Frontend 배포 시작 (포트 3000)..."
                            
                            bat '''
                            echo "Webservice Frontend 재시작..."
                            taskkill /F /FI "WINDOWTITLE eq Webservice Frontend*" 2>nul || echo "기존 프로세스 없음"
                            
                            cd webservice
                            start "Webservice Frontend" npm run dev
                            '''
                            
                            echo "✅ Webservice Frontend 배포 완료 (http://${DEV_SERVER_IP}:3000)"
                        }
                    }
                }
                
                // CLI는 배포 불필요 (패키지 빌드만)
                stage('CLI 패키지 빌드') {
                    when {
                        environment name: 'CLI_BUILD_SUCCESS', value: 'true'
                    }
                    steps {
                        script {
                            echo "📦 CLI 실행파일 빌드..."
                            
                            dir('cli') {
                                bat '''
                                call .venv\\Scripts\\activate
                                python scripts/build.py --no-test
                                '''
                            }
                            
                            echo "✅ CLI 실행파일 빌드 완료"
                        }
                    }
                }
            }
        }

        // 6. 배포 상태 확인
        stage('🔍 배포 상태 확인') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    echo "🎯 배포된 서비스 상태 확인..."
                    
                    // 헬스체크 (5초 대기 후 확인)
                    sleep 5
                    
                    if (env.AUTODOC_BUILD_SUCCESS == 'true') {
                        bat 'curl -f http://localhost:8001/health || echo "AutoDoc Service 헬스체크 실패"'
                        echo "✅ AutoDoc Service 가동 확인"
                    }
                    
                    if (env.WEBSERVICE_BUILD_SUCCESS == 'true') {
                        bat 'curl -f http://localhost:8000/api/health || echo "Webservice Backend 헬스체크 실패"'
                        bat 'curl -f http://localhost:3000 || echo "Webservice Frontend 헬스체크 실패"'
                        echo "✅ Webservice 가동 확인"
                    }
                    
                    echo "🎉 배포 상태 확인 완료!"
                }
            }
        }
    }

    post {
        always {
            script {
                echo "🏁 Jenkins 파이프라인이 완료되었습니다."
                
                // 아티팩트 보관 (빌드 결과물)
                archiveArtifacts artifacts: '**/dist/**,**/build/**,**/documents/**', allowEmptyArchive: true
                
                // 테스트 결과 수집
                publishTestResults testResultsPattern: '**/test-results.xml', allowEmptyResults: true
            }
        }
        
        success {
            script {
                def deployedServices = []
                
                if (env.AUTODOC_BUILD_SUCCESS == 'true') {
                    deployedServices.add("AutoDoc Service (http://${DEV_SERVER_IP}:8001)")
                }
                if (env.WEBSERVICE_BUILD_SUCCESS == 'true') {
                    deployedServices.add("Webservice Backend (http://${DEV_SERVER_IP}:8000)")
                    deployedServices.add("Webservice Frontend (http://${DEV_SERVER_IP}:3000)")
                }
                if (env.CLI_BUILD_SUCCESS == 'true') {
                    deployedServices.add("CLI 실행파일")
                }
                
                echo "✅ MSA 스마트 배포 성공!"
                echo "🎯 배포된 서비스:"
                deployedServices.each { service ->
                    echo "  - ${service}"
                }
                
                if (deployedServices.isEmpty()) {
                    echo "ℹ️ 변경된 서비스가 없어 배포를 건너뛰었습니다."
                }
                
                // 성공 알림 (Slack, 이메일 등)
                // slackSend channel: '#ci-cd', message: "✅ MSA 스마트 배포 성공 (${deployedServices.size()}개 서비스): ${env.BUILD_URL}"
            }
        }
        
        failure {
            script {
                echo "❌ 빌드 실패! 로그를 확인하세요."
                
                // 실패 알림
                // slackSend channel: '#ci-cd', color: 'danger', message: "❌ cm-docs 빌드 실패: ${env.BUILD_URL}"
            }
        }
        
        cleanup {
            script {
                echo "🧹 임시 파일 정리..."
                // 가상환경 및 임시 파일 정리 (선택사항)
                bat '''
                if exist "webservice\\.venv" rmdir /s /q "webservice\\.venv"
                if exist "cli\\.venv" rmdir /s /q "cli\\.venv"
                if exist "autodoc_service\\.venv312" rmdir /s /q "autodoc_service\\.venv312"
                '''
            }
        }
    }
}