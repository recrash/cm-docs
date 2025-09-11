#!/bin/bash

# Phase 2 수동 테스트 스크립트
# 사용법: ./test_phase2_manual.sh "/path/to/html/file.html"

HTML_FILE="${1:-/Users/recrash/Downloads/0_FW_ Hub HTML_250813/규격 확정일자.html}"
SESSION_ID="manual_test_$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "Phase 2 문서 생성 테스트"
echo "HTML 파일: $HTML_FILE"
echo "세션 ID: $SESSION_ID"
echo "=========================================="

# 1. HTML 파싱
echo -e "\n[1/4] HTML 파일 파싱 중..."
PARSED_DATA=$(curl -s -X POST "http://localhost:8001/api/autodoc/parse-html-only" \
  -F "file=@$HTML_FILE")

if [ -z "$PARSED_DATA" ]; then
  echo "❌ HTML 파싱 실패"
  exit 1
fi
echo "✅ HTML 파싱 완료"

# 2. 전체 문서 생성 시작 (실제 파싱된 데이터 사용)
echo -e "\n[2/4] 전체 문서 생성 시작..."

# 파싱된 데이터를 JSON으로 변환하여 metadata에 포함
METADATA_WITH_RAW_DATA=$(echo "$PARSED_DATA" | python3 -c "
import sys, json
try:
    parsed_data = json.load(sys.stdin)
    metadata = {
        'change_id': 'CM-TEST-$(date +%Y%m%d-%H%M%S)',
        'system': '테스트시스템', 
        'title': '$(basename "$HTML_FILE" .html) 문서 생성',
        'requester': '테스터',
        'request_dept': 'QA팀',
        'raw_data': parsed_data
    }
    print(json.dumps(metadata, ensure_ascii=False))
except Exception as e:
    print(f'JSON 파싱 실패: {e}', file=sys.stderr)
    # 파싱 실패 시 기본 메타데이터
    metadata = {
        'change_id': 'CM-TEST-$(date +%Y%m%d-%H%M%S)',
        'system': '테스트시스템',
        'title': '$(basename "$HTML_FILE" .html) 문서 생성', 
        'requester': '테스터',
        'request_dept': 'QA팀'
    }
    print(json.dumps(metadata, ensure_ascii=False))
")

GENERATION_RESULT=$(curl -s -X POST "http://localhost:8000/api/webservice/v2/start-full-generation" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"vcs_analysis_text\": \"HTML 파일 기반 문서 생성 테스트:\\n- 파일: $(basename "$HTML_FILE")\\n- 테스트 시점: $(date)\\n- Phase 2 통합 테스트\\n- HTML 파싱 데이터 활용\",
    \"metadata_json\": $METADATA_WITH_RAW_DATA
  }")

if echo "$GENERATION_RESULT" | grep -q "accepted"; then
  echo "✅ 문서 생성 작업 시작됨"
else
  echo "❌ 문서 생성 시작 실패"
  echo "$GENERATION_RESULT"
  exit 1
fi

# 3. 진행 상황 모니터링 (최대 120초)
echo -e "\n[3/4] 문서 생성 진행 중..."
for i in {1..24}; do
  sleep 5
  STATUS=$(curl -s "http://localhost:8000/api/webservice/v2/full-generation-status/$SESSION_ID")
  CURRENT_STATUS=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)
  PROGRESS=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('progress', 0))" 2>/dev/null)
  
  echo "  상태: $CURRENT_STATUS (진행률: ${PROGRESS}%)"
  
  if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "✅ 문서 생성 완료!"
    break
  elif [ "$CURRENT_STATUS" = "error" ]; then
    echo "❌ 문서 생성 실패"
    echo "$STATUS" | python3 -m json.tool
    exit 1
  fi
done

# 4. 결과 확인 및 파일 정보 출력
echo -e "\n[4/4] 생성된 문서 정보..."
FINAL_STATUS=$(curl -s "http://localhost:8000/api/webservice/v2/full-generation-status/$SESSION_ID")
echo "$FINAL_STATUS" | python3 -m json.tool

# 생성된 파일 목록
echo -e "\n=========================================="
echo "📁 생성된 파일들:"
echo "$FINAL_STATUS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', {})
for key, value in results.items():
    if value and 'filename' in key:
        print(f'  - {key}: {value}')
"

echo -e "\n✨ 테스트 완료!"
echo "세션 ID: $SESSION_ID"
echo "=========================================="