#!/bin/bash

# TestscenarioMaker 개발 서버 시작 스크립트

# 새로운 프로세스 그룹 생성 (중요: 모든 자식 프로세스를 함께 관리)
set -m

echo "🚀 TestscenarioMaker 개발 서버를 시작합니다..."

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PID 파일들 (정리 시 사용)
BACKEND_PID_FILE="/tmp/testscenario_backend.pid"
FRONTEND_PID_FILE="/tmp/testscenario_frontend.pid"

# 의존성 설치 확인
echo -e "${BLUE}📦 의존성 확인 중...${NC}"

# Python 의존성 확인
if [ ! -d "venv" ]; then
    echo -e "${BLUE}Python 가상환경을 생성합니다...${NC}"
    python -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

# Node.js 의존성 확인
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Node.js 의존성을 설치합니다...${NC}"
    npm install > /dev/null 2>&1
fi

# 이전 실행된 서버들 정리
cleanup_existing() {
    echo -e "${YELLOW}🧹 기존 서버 프로세스 정리 중...${NC}"
    
    # 포트 기반으로 기존 프로세스 종료
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3001 | xargs kill -9 2>/dev/null || true
    
    # PID 파일 기반 정리
    if [ -f "$BACKEND_PID_FILE" ]; then
        kill -9 $(cat "$BACKEND_PID_FILE") 2>/dev/null || true
        rm -f "$BACKEND_PID_FILE"
    fi
    if [ -f "$FRONTEND_PID_FILE" ]; then
        kill -9 $(cat "$FRONTEND_PID_FILE") 2>/dev/null || true
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # uvicorn과 vite 프로세스 강제 종료
    pkill -f "uvicorn backend.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    sleep 1
}

# 종료 시 모든 프로세스 정리
cleanup() {
    echo -e "\n${RED}🛑 모든 서버를 종료합니다...${NC}"
    
    # 프로세스 그룹 전체 종료 (SIGTERM 먼저, 그 다음 SIGKILL)
    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${RED}  - FastAPI 서버 종료 중... (PID: $BACKEND_PID)${NC}"
        kill -TERM $BACKEND_PID 2>/dev/null || true
        sleep 2
        kill -KILL $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${RED}  - React 서버 종료 중... (PID: $FRONTEND_PID)${NC}"
        kill -TERM $FRONTEND_PID 2>/dev/null || true
        sleep 2
        kill -KILL $FRONTEND_PID 2>/dev/null || true
    fi
    
    # 포트 기반 강제 정리
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:3001 | xargs kill -9 2>/dev/null || true
    
    # 프로세스 이름 기반 정리
    pkill -f "uvicorn backend.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    # PID 파일 정리
    rm -f "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"
    
    echo -e "${GREEN}✅ 모든 서버가 정상적으로 종료되었습니다.${NC}"
    exit 0
}

# 기존 프로세스 정리
cleanup_existing

# 종료 신호 처리 설정
trap cleanup INT TERM EXIT

# 백그라운드에서 FastAPI 서버 시작
echo -e "${GREEN}🔧 FastAPI 백엔드 서버 시작 (포트 8000)...${NC}"
python -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo $BACKEND_PID > "$BACKEND_PID_FILE"

# 백엔드 서버 시작 대기
sleep 3

# 백그라운드에서 React 서버 시작
echo -e "${GREEN}⚛️  React 프론트엔드 서버 시작 (포트 3000)...${NC}"
npm run dev &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$FRONTEND_PID_FILE"

echo -e "${GREEN}🎉 서버 시작 완료!${NC}"
echo -e "${BLUE}  - FastAPI 백엔드: http://localhost:8000${NC}"
echo -e "${BLUE}  - React 프론트엔드: http://localhost:3000${NC}"
echo -e "${BLUE}  - API 문서: http://localhost:8000/docs${NC}"
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요...${NC}"

# 백그라운드 프로세스들을 기다림
wait