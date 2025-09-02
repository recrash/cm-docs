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

echo -e "${GREEN}✅ 성공! '$WHEELHOUSE_DIR' 폴더에 모든 의존성 씨앗이 준비되었습니다.${NC}"
echo "   이제 이 'wheelhouse' 폴더를 소스코드와 함께 인트라넷 환경으로 가져가세요."