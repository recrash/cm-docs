#!/bin/bash

# TestscenarioMaker 개발 서버 정리 스크립트

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧹 TestscenarioMaker 개발 서버 정리 중...${NC}"

# PID 파일들
BACKEND_PID_FILE="/tmp/testscenario_backend.pid"
FRONTEND_PID_FILE="/tmp/testscenario_frontend.pid"

# PID 파일 기반 정리
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    echo -e "${RED}  - FastAPI 서버 종료 중... (PID: $BACKEND_PID)${NC}"
    kill -TERM $BACKEND_PID 2>/dev/null || true
    sleep 1
    kill -KILL $BACKEND_PID 2>/dev/null || true
    rm -f "$BACKEND_PID_FILE"
fi

if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    echo -e "${RED}  - React 서버 종료 중... (PID: $FRONTEND_PID)${NC}"
    kill -TERM $FRONTEND_PID 2>/dev/null || true
    sleep 1
    kill -KILL $FRONTEND_PID 2>/dev/null || true
    rm -f "$FRONTEND_PID_FILE"
fi

# 포트 기반 강제 정리
echo -e "${RED}  - 포트 기반 프로세스 정리 중...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true

# 프로세스 이름 기반 정리
echo -e "${RED}  - 프로세스 이름 기반 정리 중...${NC}"
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "start-dev.sh" 2>/dev/null || true

echo -e "${GREEN}✅ 모든 개발 서버가 정리되었습니다!${NC}"
echo -e "${GREEN}   이제 ./start-dev.sh로 다시 시작할 수 있습니다.${NC}"