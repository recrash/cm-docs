#!/bin/bash
"""
TestscenarioMaker Helper App 독립 설치 스크립트

이 스크립트는 헬퍼 앱만 별도로 설치하거나 업데이트할 때 사용합니다.
전체 DMG 설치와는 별도로 헬퍼 앱만 설치하고 싶을 때 유용합니다.
"""

set -e

# 스크립트 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPER_APP_NAME="TestscenarioMaker Helper.app"
INSTALL_DIR="/Applications"

echo "🛠️  TestscenarioMaker Helper App 설치 스크립트"
echo "================================================"
echo "   프로젝트: $PROJECT_ROOT"
echo "   설치 대상: $INSTALL_DIR/$HELPER_APP_NAME"
echo

# 1. 헬퍼 앱 빌드
echo "📦 헬퍼 앱 빌드 중..."
if [ ! -f "$PROJECT_ROOT/scripts/build_helper_app.py" ]; then
    echo "❌ 오류: 헬퍼 앱 빌드 스크립트를 찾을 수 없습니다."
    echo "   경로: $PROJECT_ROOT/scripts/build_helper_app.py"
    exit 1
fi

# Python 3 확인
if ! command -v python3 &> /dev/null; then
    echo "❌ 오류: Python 3이 설치되어 있지 않습니다."
    echo "   Python 3을 설치한 후 다시 시도하세요."
    exit 1
fi

# 헬퍼 앱 빌드 실행
echo "   🏗️  빌드 스크립트 실행 중..."
cd "$PROJECT_ROOT"
python3 scripts/build_helper_app.py --project-root "$PROJECT_ROOT"

if [ $? -ne 0 ]; then
    echo "❌ 헬퍼 앱 빌드 실패"
    exit 1
fi

# 2. 빌드된 헬퍼 앱 확인
HELPER_APP_PATH="$PROJECT_ROOT/dist/$HELPER_APP_NAME"
if [ ! -d "$HELPER_APP_PATH" ]; then
    echo "❌ 오류: 빌드된 헬퍼 앱을 찾을 수 없습니다."
    echo "   예상 경로: $HELPER_APP_PATH"
    exit 1
fi

echo "   ✓ 헬퍼 앱 빌드 완료: $HELPER_APP_PATH"

# 3. 기존 헬퍼 앱 제거 (있는 경우)
INSTALLED_HELPER_PATH="$INSTALL_DIR/$HELPER_APP_NAME"
if [ -d "$INSTALLED_HELPER_PATH" ]; then
    echo "🗑️  기존 헬퍼 앱 제거 중..."
    rm -rf "$INSTALLED_HELPER_PATH"
    echo "   ✓ 기존 헬퍼 앱 제거 완료"
fi

# 4. 새 헬퍼 앱 설치
echo "📱 헬퍼 앱 설치 중..."
cp -R "$HELPER_APP_PATH" "$INSTALL_DIR/"
echo "   ✓ 헬퍼 앱 설치 완료: $INSTALLED_HELPER_PATH"

# 5. 권한 설정
echo "🔐 권한 설정 중..."
chmod +x "$INSTALLED_HELPER_PATH/Contents/MacOS/applet" 2>/dev/null || true
echo "   ✓ 실행 권한 설정 완료"

# 6. 코드 서명 (선택사항)
echo "✍️  코드 서명 중..."
if command -v codesign &> /dev/null; then
    codesign --force --deep -s - "$INSTALLED_HELPER_PATH" &>/dev/null || {
        echo "   ⚠️  코드 서명 실패 (무시됨)"
    }
    echo "   ✓ Ad-hoc 서명 완료"
else
    echo "   ⚠️  codesign 명령을 찾을 수 없음 (무시됨)"
fi

# 7. 격리 속성 제거
echo "🧹 격리 속성 제거 중..."
if command -v xattr &> /dev/null; then
    xattr -d com.apple.quarantine "$INSTALLED_HELPER_PATH" &>/dev/null || {
        echo "   ℹ️  격리 속성이 없거나 이미 제거됨"
    }
    echo "   ✓ 격리 속성 처리 완료"
else
    echo "   ⚠️  xattr 명령을 찾을 수 없음 (무시됨)"
fi

# 8. URL 스킴 등록 확인
echo "🔗 URL 스킴 등록 확인 중..."
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [ -x "$LSREGISTER" ]; then
    # LaunchServices 데이터베이스 새로고침
    "$LSREGISTER" -f "$INSTALLED_HELPER_PATH" &>/dev/null || true
    
    # 등록 상태 확인
    if "$LSREGISTER" -dump | grep -q "testscenariomaker"; then
        echo "   ✓ URL 스킴 등록 확인됨"
    else
        echo "   ℹ️  URL 스킴 등록 대기 중 (첫 실행 후 등록됩니다)"
    fi
else
    echo "   ⚠️  lsregister 명령을 찾을 수 없음"
fi

# 9. 검증
echo "🧪 설치 검증 중..."
VALIDATION_ERRORS=0

# 앱 번들 존재 확인
if [ ! -d "$INSTALLED_HELPER_PATH" ]; then
    echo "   ❌ 헬퍼 앱이 설치되지 않음"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
else
    echo "   ✓ 헬퍼 앱 설치 확인"
fi

# CLI 실행파일 확인
CLI_IN_HELPER="$INSTALLED_HELPER_PATH/Contents/Resources/TestscenarioMaker-CLI"
if [ ! -f "$CLI_IN_HELPER" ]; then
    echo "   ❌ 내장된 CLI 실행파일 없음"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
elif [ ! -x "$CLI_IN_HELPER" ]; then
    echo "   ❌ CLI 실행파일 권한 없음"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
else
    echo "   ✓ 내장된 CLI 실행파일 확인"
fi

# Info.plist 확인
PLIST_PATH="$INSTALLED_HELPER_PATH/Contents/Info.plist"
if [ ! -f "$PLIST_PATH" ]; then
    echo "   ❌ Info.plist 파일 없음"
    VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
else
    # URL 스킴 등록 확인
    if plutil -extract CFBundleURLTypes.0.CFBundleURLSchemes.0 raw "$PLIST_PATH" 2>/dev/null | grep -q "testscenariomaker"; then
        echo "   ✓ URL 스킴 등록 확인"
    else
        echo "   ❌ URL 스킴 등록 안됨"
        VALIDATION_ERRORS=$((VALIDATION_ERRORS + 1))
    fi
fi

echo
if [ $VALIDATION_ERRORS -eq 0 ]; then
    echo "✅ 헬퍼 앱 설치 및 검증 완료!"
    echo
    echo "📋 사용 방법:"
    echo "   1. 웹 브라우저에서 testscenariomaker:// 링크 클릭"
    echo "   2. 첫 번째 클릭 시 브라우저에서 '허용' 선택"
    echo "   3. 헬퍼 앱이 자동으로 CLI를 실행"
    echo
    echo "🧪 테스트 명령어:"
    echo "   open 'testscenariomaker:///path/to/your/repository'"
    echo
    echo "🔍 URL 스킴 등록 확인:"
    echo "   $LSREGISTER -dump | grep testscenariomaker"
    echo
else
    echo "❌ 설치 검증 실패 ($VALIDATION_ERRORS개 오류)"
    echo "   로그를 확인하고 문제를 해결한 후 다시 시도하세요."
    exit 1
fi