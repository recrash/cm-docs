#!/bin/bash
# AutoDoc Service 실행 스크립트 (macOS/Linux)

set -e  # 에러 시 중단

echo "==============================================="
echo "🏗️  AutoDoc Service 시작 (Bash)"
echo "==============================================="

# 현재 디렉터리를 스크립트 위치로 설정
cd "$(dirname "$0")"

# Python 버전 확인
check_python() {
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    else
        echo "❌ Python이 설치되지 않았습니다."
        exit 1
    fi
    
    # 버전 확인
    VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "🐍 Python 버전: $VERSION"
    
    if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        echo "❌ Python 3.8 이상이 필요합니다."
        exit 1
    fi
}

# 의존성 설치
install_dependencies() {
    echo "📦 의존성 설치 중..."
    
    if [ -d "wheels" ]; then
        echo "🔧 오프라인 모드: wheels 디렉터리에서 설치"
        $PYTHON_CMD -m pip install --no-index --find-links ./wheels -r requirements.txt
    else
        echo "🌐 온라인 모드: PyPI에서 설치"
        $PYTHON_CMD -m pip install -r requirements.txt
    fi
    
    echo "✅ 의존성 설치 완료"
}

# 템플릿 파일 확인
check_templates() {
    echo "🔍 템플릿 파일 확인 중..."
    
    TEMPLATES_DIR="templates"
    REQUIRED_TEMPLATES=("template.docx" "template.xlsx" "template_list.xlsx")
    MISSING_TEMPLATES=()
    
    for template in "${REQUIRED_TEMPLATES[@]}"; do
        if [ -f "$TEMPLATES_DIR/$template" ]; then
            echo "✅ $template 발견"
        else
            MISSING_TEMPLATES+=("$template")
        fi
    done
    
    if [ ${#MISSING_TEMPLATES[@]} -gt 0 ]; then
        echo "❌ 누락된 템플릿 파일: ${MISSING_TEMPLATES[*]}"
        echo "템플릿 디렉터리: $(pwd)/$TEMPLATES_DIR"
        return 1
    fi
    
    echo "✅ 모든 템플릿 파일 확인됨"
    return 0
}

# 문서 디렉터리 생성
create_documents_dir() {
    mkdir -p documents
    echo "📁 문서 디렉터리 준비: $(pwd)/documents"
}

# 메인 실행
main() {
    # Python 확인
    check_python
    
    # 의존성 확인 및 설치
    if ! $PYTHON_CMD -c "import fastapi, uvicorn" 2>/dev/null; then
        install_dependencies
    else
        echo "✅ 주요 의존성이 이미 설치되어 있습니다."
    fi
    
    # 템플릿 확인
    if ! check_templates; then
        echo ""
        echo "⚠️  템플릿 파일이 없어도 서버는 시작할 수 있습니다."
        echo "   API 호출 시 404 오류가 발생할 수 있습니다."
        echo ""
        read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ 실행이 취소되었습니다."
            exit 1
        fi
    fi
    
    # 문서 디렉터리 생성
    create_documents_dir
    
    # 서버 실행
    echo ""
    echo "🚀 AutoDoc Service 시작 중..."
    echo "   주소: http://localhost:8000"
    echo "   API 문서: http://localhost:8000/docs"
    echo "   종료하려면 Ctrl+C를 누르세요"
    echo ""
    
    $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# 신호 처리
trap 'echo -e "\n👋 AutoDoc Service가 종료되었습니다."; exit 0' INT TERM

# 메인 실행
main "$@"