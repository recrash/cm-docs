#!/bin/bash
# =================================================================
# 폐쇄망 CI/CD를 위한 '의존성 씨앗' 수확 스크립트 (Constraints 반영)
# =================================================================
# 실행 방법:
# 1. 인터넷이 연결된 PC에서 이 스크립트를 프로젝트 루트에 저장
# 2. 터미널에서 스크립트에 실행 권한 부여: chmod +x download-all-dependencies.sh
# 3. 프로젝트 루트에서 스크립트 실행: ./download-all-dependencies.sh
# =================================================================

# --- 스크립트 설정 ---
set -e # 에러 발생 시 즉시 중지

# --- 색상 코드 정의 ---
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color

# --- 경로 변수 정의 ---
PROJECT_ROOT=$(pwd)
WHEELHOUSE_DIR="$PROJECT_ROOT/wheelhouse" # 최종 결과물 폴더

# --- 준비 ---
echo -e "${YELLOW}🚀 'wheelhouse' 폴더를 준비합니다...${NC}"
if [ ! -d "$WHEELHOUSE_DIR" ]; then
    mkdir -p "$WHEELHOUSE_DIR"
    echo "    - 새로운 'wheelhouse' 폴더를 생성했습니다."
else
    echo "    - 기존 'wheelhouse' 폴더에 누락된 파일만 추가합니다."
fi

# --- 서비스별 환경 설정 및 다운로드 ---
SERVICES=(
    "webservice:.venv"
    "autodoc_service:.venv312"
    "cli:.venv"
)

# --- 모든 의존성 다운로드 ---
echo -e "${YELLOW}🚀 모든 Python 의존성 .whl 파일을 수확합니다...${NC}"
for SERVICE_INFO in "${SERVICES[@]}"; do
    IFS=':' read -r SERVICE_DIR VENV_DIR <<< "$SERVICE_INFO"
    SERVICE_PATH="$PROJECT_ROOT/$SERVICE_DIR"
    REQ_FILE="$SERVICE_PATH/requirements.txt"
    REQ_DEV_FILE="$SERVICE_PATH/requirements-dev.txt"
    VENV_PATH="$SERVICE_PATH/$VENV_DIR"
    
    if [ -f "$REQ_FILE" ] && [ -d "$VENV_PATH" ]; then
        # 가상환경의 pip 경로
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            PIP_PATH="$VENV_PATH/Scripts/pip"
        else
            PIP_PATH="$VENV_PATH/bin/pip"
        fi
        
        # ✨ 제약 조건 파일 경로를 동적으로 확인
        CONSTRAINT_FILE="$SERVICE_PATH/pip.constraints.txt"
        
        # 운영 의존성 다운로드
        PIP_COMMAND="\"$PIP_PATH\" download -r \"$REQ_FILE\" -d \"$WHEELHOUSE_DIR\" --prefer-binary"
        if [ -f "$CONSTRAINT_FILE" ]; then
            echo "    - '$REQ_FILE' 파일의 의존성을 제약 조건('-c')을 포함하여 다운로드합니다."
            PIP_COMMAND+=" -c \"$CONSTRAINT_FILE\""
        else
            echo "    - '$REQ_FILE' 파일의 의존성을 다운로드합니다."
        fi
        eval $PIP_COMMAND
        
        # 개발 의존성 다운로드 (requirements-dev.txt가 있는 경우)
        if [ -f "$REQ_DEV_FILE" ]; then
            echo "    - '$REQ_DEV_FILE' 파일의 개발 의존성을 다운로드합니다."
            DEV_PIP_COMMAND="\"$PIP_PATH\" download -r \"$REQ_DEV_FILE\" -d \"$WHEELHOUSE_DIR\" --prefer-binary"
            if [ -f "$CONSTRAINT_FILE" ]; then
                DEV_PIP_COMMAND+=" -c \"$CONSTRAINT_FILE\""
            fi
            eval $DEV_PIP_COMMAND
        fi
    else
        if [ ! -f "$REQ_FILE" ]; then
            echo -e "    - ${YELLOW}경고: '$REQ_FILE' 파일을 찾을 수 없습니다.${NC}"
        fi
        if [ ! -d "$VENV_PATH" ]; then
            echo -e "    - ${YELLOW}경고: '$VENV_PATH' 가상환경을 찾을 수 없습니다.${NC}"
        fi
    fi
done

# --- 빌드 도구 자체도 다운로드 (첫 번째 사용 가능한 환경 사용) ---
echo "    - 빌드 필수 도구(build, wheel)를 다운로드합니다."
for SERVICE_INFO in "${SERVICES[@]}"; do
    IFS=':' read -r SERVICE_DIR VENV_DIR <<< "$SERVICE_INFO"
    VENV_PATH="$PROJECT_ROOT/$SERVICE_DIR/$VENV_DIR"
    
    if [ -d "$VENV_PATH" ]; then
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            PIP_PATH="$VENV_PATH/Scripts/pip"
        else
            PIP_PATH="$VENV_PATH/bin/pip"
        fi
        
        "$PIP_PATH" download build wheel -d "$WHEELHOUSE_DIR"
        break
    fi
done

# --- npm 의존성 처리 (node_modules 직접 복사 방식) ---
echo -e "${YELLOW}🚀 npm 의존성을 설치하고 복사합니다...${NC}"
FRONTEND_PATH="$PROJECT_ROOT/webservice/frontend"

if [ -f "$FRONTEND_PATH/package.json" ] && [ -f "$FRONTEND_PATH/package-lock.json" ]; then
    echo "    - webservice frontend의 npm 의존성을 완전 설치 후 복사합니다."
    cd "$FRONTEND_PATH"

    # 1. 완전한 node_modules 설치
    npm ci
    if [ $? -ne 0 ]; then
        echo -e "    - ${RED}오류: npm ci 실패${NC}"
        exit 1
    fi

    # 2. 대상 디렉토리 준비 (단일 node_modules 폴더)
    NODE_MODULES_TARGET="/deploys/packages/frontend/node_modules"
    # Windows Git Bash의 경우 경로 변환
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        NODE_MODULES_TARGET="C:/deploys/packages/frontend/node_modules"
    fi

    if [ -d "$NODE_MODULES_TARGET" ]; then
        echo "    - 기존 node_modules 폴더 제거 중..."
        rm -rf "$NODE_MODULES_TARGET"
    fi

    # 3. node_modules 폴더 복사
    echo "    - node_modules 폴더를 오프라인 패키지 위치로 복사 중..."
    mkdir -p "$(dirname "$NODE_MODULES_TARGET")"
    cp -r node_modules "$NODE_MODULES_TARGET"

    if [ $? -ne 0 ]; then
        echo -e "    - ${RED}오류: node_modules 복사 실패${NC}"
        exit 1
    fi

    echo "    - npm 오프라인 패키지 준비 완료: $NODE_MODULES_TARGET"
    cd "$PROJECT_ROOT"
else
    echo -e "    - ${YELLOW}경고: webservice/frontend의 package.json 또는 package-lock.json을 찾을 수 없습니다.${NC}"
fi

echo -e "${GREEN}✅ 성공! 모든 의존성 패키지가 준비되었습니다.${NC}"
echo "   - Python: $WHEELHOUSE_DIR"
echo "   - Node.js: $NODE_MODULES_TARGET"
echo "   이제 이 폴더들을 폐쇄망 환경으로 복사하세요."