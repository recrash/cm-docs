#!/bin/bash
# =================================================================
# 폐쇄망 배포용 'deploy-package.zip' 생성 스크립트 (Bash 버전)
# =================================================================
# 실행 방법:
# 1. 이 스크립트를 프로젝트 루트 폴더에 저장
# 2. 터미널에서 스크립트에 실행 권한 부여: chmod +x create-deploy-package.sh
# 3. 프로젝트 루트에서 스크립트 실행: ./create-deploy-package.sh
# =================================================================

# --- 스크립트 설정 ---
set -e # 에러 발생 시 즉시 중지

# --- 색상 코드 정의 ---
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

# --- 경로 변수 정의 ---
PROJECT_ROOT=$(pwd)
STAGING_DIR="$PROJECT_ROOT/staging"
PACKAGE_FILE="$PROJECT_ROOT/deploy-package.zip"

# --- 폴더 구조 정의 ---
DEPLOY_ROOT="$STAGING_DIR/deploys"
PACKAGE_DIR="$DEPLOY_ROOT/packages"
DATA_DIR="$DEPLOY_ROOT/data"
APPS_DIR="$DEPLOY_ROOT/apps"

# =================================================================
# 0. 패키징 준비
# =================================================================
echo -e "${YELLOW}🚀 (0/5) 패키징을 위한 임시 스테이징 폴더를 준비합니다...${NC}"
if [ -d "$STAGING_DIR" ]; then
    rm -rf "$STAGING_DIR"
    echo "    - 기존 'staging' 폴더를 삭제했습니다."
fi
mkdir -p "$DEPLOY_ROOT" "$PACKAGE_DIR" "$DATA_DIR" "$APPS_DIR"
echo "    - 새로운 'staging/deploys' 폴더 구조를 생성했습니다."

# =================================================================
# 1. 백엔드 서비스 빌드 (.whl 생성)
# =================================================================
echo -e "${YELLOW}🚀 (1/5) Python 백엔드 서비스를 빌드합니다...${NC}"

# --- autodoc_service 빌드 ---
( # Subshell을 사용해서 작업 후 원래 디렉토리로 자동 복귀
    cd "$PROJECT_ROOT/autodoc_service"
    echo "    - 'autodoc_service' 빌드 중..."
    python3.12 -m venv .venv312
    source .venv312/bin/activate
    pip install build --quiet
    python -m build --wheel --no-isolation
    
    TARGET_DIR="$PACKAGE_DIR/autodoc_service"
    mkdir -p "$TARGET_DIR"
    cp dist/*.whl "$TARGET_DIR/"
    deactivate
    echo -e "    - 'autodoc_service' 빌드 완료!${GREEN}✔${NC}"
) || { echo -e "${RED}❌ 'autodoc_service' 빌드 중 심각한 오류가 발생했습니다.${NC}"; exit 1; }

# --- webservice 빌드 ---
(
    cd "$PROJECT_ROOT/webservice"
    echo "    - 'webservice' 빌드 중..."
    python3.13 -m venv .venv
    source .venv/bin/activate    
    pip install --upgrade pip build setuptools wheel --quiet
    python -m build --wheel --no-isolation
    
    TARGET_DIR="$PACKAGE_DIR/webservice"
    mkdir -p "$TARGET_DIR"
    cp dist/*.whl "$TARGET_DIR/"
    deactivate
    echo -e "    - 'webservice' 빌드 완료!${GREEN}✔${NC}"
) || { echo -e "${RED}❌ 'webservice' 빌드 중 심각한 오류가 발생했습니다.${NC}"; exit 1; }

# =================================================================
# 2. 프론트엔드 빌드 (React)
# =================================================================
echo -e "${YELLOW}🚀 (2/5) React 프론트엔드를 빌드합니다...${NC}"
(
    cd "$PROJECT_ROOT/webservice/frontend"
    echo "    - 의존성 설치 (npm install)..."
    npm install
    echo "    - 프로덕션 빌드 (npm run build)..."
    npm run build

    TARGET_DIR="$APPS_DIR/webservice/frontend"
    mkdir -p "$TARGET_DIR"
    cp -r dist/* "$TARGET_DIR/"
    echo -e "    - 프론트엔드 빌드 완료!${GREEN}✔${NC}"
) || { echo -e "${RED}❌ 프론트엔드 빌드 중 심각한 오류가 발생했습니다.${NC}"; exit 1; }

# =================================================================
# 3. 초기 데이터 복사
# =================================================================
echo -e "${YELLOW}🚀 (3/5) 운영에 필요한 초기 데이터를 복사합니다...${NC}"

# --- AutoDoc 템플릿 복사 ---
echo "    - 'autodoc_service'의 템플릿 파일을 복사합니다."
SOURCE_DIR="$PROJECT_ROOT/autodoc_service/templates"
TARGET_DIR="$DATA_DIR/autodoc_service/templates"
mkdir -p "$TARGET_DIR"
cp -r "$SOURCE_DIR"/* "$TARGET_DIR/"

# --- 임베딩 모델 다운로드 및 복사 ---
echo "    - 'webservice'의 임베딩 모델을 다운로드 및 복사합니다. (시간이 걸릴 수 있습니다)"
(
    cd "$PROJECT_ROOT/webservice"
    source .venv/bin/activate
    python scripts/download_embedding_model.py
    deactivate

    SOURCE_DIR="models" # 스크립트가 ./models에 다운로드한다고 가정
    TARGET_DIR="$DATA_DIR/webservice/models"
    mkdir -p "$TARGET_DIR"
    cp -r "$SOURCE_DIR"/* "$TARGET_DIR/"
) || { echo -e "${RED}❌ 임베딩 모델 처리 중 오류가 발생했습니다.${NC}"; exit 1; }

echo -e "    - 초기 데이터 준비 완료!${GREEN}✔${NC}"

# =================================================================
# 4. 최종 패키지 압축
# =================================================================
echo -e "${YELLOW}🚀 (4/5) 모든 결과물을 'deploy-package.zip' 파일로 압축합니다...${NC}"
rm -f "$PACKAGE_FILE"
(
    cd "$STAGING_DIR" # 압축 파일 내의 경로를 'deploys' 부터 시작하도록 이동
    zip -r "$PACKAGE_FILE" deploys
)

# =================================================================
# 5. 완료
# =================================================================
echo -e "${CYAN}🚀 (5/5) 모든 작업 완료!${NC}"
echo -e "${CYAN}-----------------------------------------------------------------${NC}"
echo -e "${GREEN}✅ 성공! '$PACKAGE_FILE' 파일이 생성되었습니다.${NC}"
echo -e "${GREEN}   이 파일을 폐쇄망 운영 서버로 전달하여 배포 매뉴얼에 따라 설치하세요.${NC}"
echo -e "${CYAN}-----------------------------------------------------------------${NC}"