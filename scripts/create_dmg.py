#!/usr/bin/env python3
"""
macOS DMG 생성 스크립트

TestscenarioMaker CLI의 macOS 설치 패키지를 생성합니다.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
import tempfile
import plistlib
from typing import Dict, Any
import argparse
import re


class DMGCreator:
    """macOS DMG 생성 클래스"""
    
    def __init__(self, project_root: Path, include_helper_app: bool = True):
        """
        DMG 생성자 초기화
        
        Args:
            project_root: 프로젝트 루트 디렉토리
            include_helper_app: 헬퍼 앱을 DMG에 포함할지 여부
        """
        self.project_root = project_root.resolve()
        self.dist_dir = self.project_root / "dist"
        self.scripts_dir = self.project_root / "scripts"
        self.include_helper_app = include_helper_app
        
        # 버전 정보
        self.version = self._get_version()
        self.app_name = "TestscenarioMaker CLI"
        
        print(f"🍎 macOS DMG 생성 준비")
        print(f"   앱 이름: {self.app_name}")
        print(f"   버전: {self.version}")
        print(f"   헬퍼 앱 포함: {'예' if include_helper_app else '아니오'}")
    
    def _get_version(self) -> str:
        """버전 정보 조회"""
        try:
            init_file = self.project_root / "src" / "ts_cli" / "__init__.py"
            if init_file.exists():
                with open(init_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('__version__'):
                            return line.split('"')[1]
            return "1.0.0"
        except Exception:
            return "1.0.0"
    
    def build_helper_app_if_needed(self) -> Path:
        """
        헬퍼 앱 빌드 (필요시)
        
        Returns:
            헬퍼 앱 경로 또는 None (헬퍼 앱이 포함되지 않는 경우)
        """
        if not self.include_helper_app:
            return None
            
        print("🛠️  헬퍼 앱 확인 및 빌드...")
        
        helper_app_path = self.dist_dir / "TestscenarioMaker Helper.app"
        
        # 헬퍼 앱이 이미 존재하는지 확인
        print(f"   🔍 헬퍼 앱 경로 확인: {helper_app_path}")
        print(f"   📁 경로 존재 여부: {helper_app_path.exists()}")
        
        if helper_app_path.exists():
            print(f"   ✓ 기존 헬퍼 앱 발견: {helper_app_path}")
            return helper_app_path
        
        # 헬퍼 앱 빌드 스크립트 실행
        build_script = self.scripts_dir / "build_helper_app.py"
        if not build_script.exists():
            raise FileNotFoundError(f"헬퍼 앱 빌드 스크립트를 찾을 수 없습니다: {build_script}")
        
        print("   🏗️  헬퍼 앱 빌드 중...")
        try:
            # 실시간 출력을 위해 capture_output=False 사용
            print(f"   📝 명령어: {sys.executable} {build_script} --project-root {self.project_root}")
            result = subprocess.run([
                sys.executable, str(build_script),
                '--project-root', str(self.project_root)
            ], check=True, capture_output=False, text=True, timeout=180)  # 타임아웃을 180초로 증가
            
            print("   ✓ 헬퍼 앱 빌드 완료")
            
            # 빌드된 헬퍼 앱 경로 확인
            if helper_app_path.exists():
                return helper_app_path
            else:
                raise RuntimeError("헬퍼 앱이 빌드되었지만 예상 위치에서 찾을 수 없습니다")
                
        except subprocess.TimeoutExpired:
            print(f"   ❌ 헬퍼 앱 빌드 타임아웃 (180초)")
            raise RuntimeError("헬퍼 앱 빌드가 180초 내에 완료되지 않았습니다")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 헬퍼 앱 빌드 실패: {e.stderr}")
            raise RuntimeError(f"헬퍼 앱 빌드 실패: {e.stderr}")
    
    def create_app_bundle(self) -> Path:
        """
        .app 번들 생성
        
        Returns:
            생성된 .app 번들 경로
        """
        print("📦 .app 번들 생성 중...")
        
        app_name = "TestscenarioMaker CLI.app"
        app_path = self.dist_dir / app_name
        
        # 기존 .app 번들 제거
        if app_path.exists():
            shutil.rmtree(app_path)
        
        # .app 번들 디렉토리 구조 생성
        contents_dir = app_path / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"
        
        macos_dir.mkdir(parents=True)
        resources_dir.mkdir(parents=True)
        
        # 실행파일 존재 확인 및 복사
        exe_path = self.dist_dir / "ts-cli"
        if not exe_path.exists():
            raise FileNotFoundError(
                f"실행파일을 찾을 수 없습니다: {exe_path}\n"
                f"먼저 'python scripts/build.py'를 실행하여 빌드를 완료하세요."
            )
        
        if not exe_path.is_file():
            raise FileNotFoundError(f"실행파일이 올바른 파일이 아닙니다: {exe_path}")
        
        print(f"   📄 실행파일 복사: {exe_path}")
        app_exe_path = macos_dir / "ts-cli"
        shutil.copy2(exe_path, app_exe_path)
        app_exe_path.chmod(0o755)  # 실행 권한 부여
        
        # 설정 파일 복사 (선택사항)
        source_config = self.project_root / "config" / "config.ini"
        if source_config.exists():
            config_dir = resources_dir / "config"
            config_dir.mkdir()
            shutil.copy2(source_config, config_dir / "config.ini")
            print(f"   📄 설정 파일 복사: {source_config}")
        else:
            print(f"   ⚠️ 설정 파일 없음 (선택사항): {source_config}")
        
        # Info.plist 생성
        self._create_info_plist(contents_dir)
        
        # 아이콘 복사 (있는 경우)
        icon_file = self.scripts_dir / "icon.icns"
        if icon_file.exists():
            shutil.copy2(icon_file, resources_dir / "icon.icns")
        
        print(f"   ✓ .app 번들 생성: {app_path}")
        return app_path
    
    def _create_info_plist(self, contents_dir: Path) -> None:
        """Info.plist 파일 생성"""
        print("📄 Info.plist 생성 중...")
        
        info_plist = {
            'CFBundleName': 'TestscenarioMaker CLI',
            'CFBundleDisplayName': 'TestscenarioMaker CLI',
            'CFBundleIdentifier': 'com.testscenariomaker.cli',
            'CFBundleVersion': self.version,
            'CFBundleShortVersionString': self.version,
            'CFBundleExecutable': 'ts-cli',
            'CFBundleIconFile': 'icon.icns',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'TSCM',
            'LSMinimumSystemVersion': '10.12',  # macOS Sierra 이상
            'NSHighResolutionCapable': True,
            'LSApplicationCategoryType': 'public.app-category.developer-tools',
            'CFBundleDocumentTypes': [],
        }
        
        # CFBundleURLTypes 중복 검사 및 안전 추가
        if not hasattr(self, '_url_types_added'):
            url_types = [
                {
                    'CFBundleURLName': 'TestscenarioMaker Protocol',
                    'CFBundleURLSchemes': ['testscenariomaker'],
                    'LSHandlerRank': 'Owner'
                }
            ]
            
            # 기존 CFBundleURLTypes 확인
            existing_url_types = info_plist.get('CFBundleURLTypes', [])
            
            # testscenariomaker 스킴이 이미 등록되어 있는지 확인
            testscenariomaker_exists = False
            for url_type in existing_url_types:
                schemes = url_type.get('CFBundleURLSchemes', [])
                if 'testscenariomaker' in schemes:
                    testscenariomaker_exists = True
                    print("   ℹ️ testscenariomaker URL 스킴이 이미 등록되어 있습니다.")
                    break
            
            # testscenariomaker 프로토콜이 없을 경우에만 추가
            if not testscenariomaker_exists:
                existing_url_types.extend(url_types)
                print("   ✓ testscenariomaker URL 프로토콜을 추가했습니다.")
            
            info_plist['CFBundleURLTypes'] = existing_url_types
            self._url_types_added = True
        else:
            # 이미 처리된 경우 기본값 설정
            info_plist['CFBundleURLTypes'] = []
        
        plist_path = contents_dir / "Info.plist"
        with open(plist_path, 'wb') as f:
            plistlib.dump(info_plist, f)
        
        print(f"   ✓ Info.plist 생성: {plist_path}")
        
        # Code Signing과 Notarization에 대한 참고 사항
        print("   📝 참고: macOS Big Sur 이상에서는 Code Signing과 Notarization이 필요할 수 있습니다.")
        print("   📝 배포 시 다음 명령어를 고려하세요:")
        print("      codesign --deep --force --verify --verbose --sign 'Developer ID Application: Your Name' 'TestscenarioMaker CLI.app'")
        print("      xcrun notarytool submit 'TestscenarioMaker-CLI-{}.dmg' --keychain-profile 'notarization'".format(self.version))
    
    def _parse_mount_point(self, hdiutil_output: str) -> Path:
        """hdiutil attach 출력에서 마운트 포인트 추출"""
        # hdiutil attach 출력 형식:
        # /dev/disk4s2 	Apple_HFS 	/Volumes/TestscenarioMaker CLI 1.0.0
        
        patterns = [
            # 정확한 볼륨 이름 매칭
            r'/Volumes/TestscenarioMaker CLI[^\t\n]*',
            # 일반적인 /Volumes/ 패턴
            r'/Volumes/[^\t\n]+TestscenarioMaker[^\t\n]*',
            # 백업 패턴: /Volumes/로 시작하는 모든 경로
            r'/Volumes/[^\t\n]+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, hdiutil_output)
            for match in matches:
                mount_path = Path(match.strip())
                if mount_path.exists():
                    print(f"   🔍 마운트 포인트 발견: {mount_path}")
                    return mount_path
        
        # 모든 패턴이 실패한 경우 디버그 정보 출력
        print(f"   ⚠️ hdiutil 출력:\n{hdiutil_output}")
        return None
    
    def create_installer_script(self, helper_app: Path = None) -> Path:
        """설치 스크립트 생성"""
        print("📜 설치 스크립트 생성 중...")
        
        # 헬퍼 앱 포함 여부에 따른 설치 스크립트 생성
        helper_install_section = ""
        helper_usage_section = ""
        
        if helper_app and helper_app.exists():
            helper_name = helper_app.name
            helper_install_section = f'''
# 헬퍼 앱 설치
HELPER_APP_NAME="{helper_name}"
echo "🛠️  헬퍼 앱을 설치하는 중..."
if [ -d "$HELPER_APP_NAME" ]; then
    if [ -d "$INSTALL_DIR/$HELPER_APP_NAME" ]; then
        echo "   기존 헬퍼 앱을 제거하는 중..."
        rm -rf "$INSTALL_DIR/$HELPER_APP_NAME"
    fi
    
    cp -R "$HELPER_APP_NAME" "$INSTALL_DIR/"
    echo "   ✓ $INSTALL_DIR/$HELPER_APP_NAME 설치 완료"
    
    # 헬퍼 앱 권한 설정
    chmod +x "$INSTALL_DIR/$HELPER_APP_NAME/Contents/MacOS/applet" 2>/dev/null || true
    
    echo "   ℹ️  헬퍼 앱이 URL 프로토콜 처리를 담당합니다"
else
    echo "   ⚠️  헬퍼 앱을 찾을 수 없습니다 (선택사항)"
fi
'''
            helper_usage_section = '''
echo "🌐 웹 브라우저에서 testscenariomaker:// 링크 사용:"
echo "   - 헬퍼 앱이 자동으로 브라우저 샌드박스를 우회하여 CLI를 실행합니다"
echo "   - 첫 번째 링크 클릭 시 브라우저에서 허용 여부를 묻습니다"
'''

        install_script = f'''#!/bin/bash
# TestscenarioMaker CLI 설치 스크립트

set -e

# 스크립트가 있는 디렉터리로 이동
SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="TestscenarioMaker CLI.app"
INSTALL_DIR="/Applications"
CLI_NAME="ts-cli"
CLI_LINK="/usr/local/bin/$CLI_NAME"

echo "🚀 TestscenarioMaker CLI 설치를 시작합니다..."
echo "   스크립트 위치: $SCRIPT_DIR"

# 메인 CLI 앱 번들 존재 확인
if [ ! -d "$APP_NAME" ]; then
    echo "❌ 오류: $APP_NAME을 찾을 수 없습니다."
    echo "   현재 위치: $(pwd)"
    echo "   파일 목록:"
    ls -la
    exit 1
fi

# Applications 폴더에 메인 앱 복사
echo "📱 메인 애플리케이션을 설치하는 중..."
if [ -d "$INSTALL_DIR/$APP_NAME" ]; then
    echo "   기존 설치본을 제거하는 중..."
    rm -rf "$INSTALL_DIR/$APP_NAME"
fi

cp -R "$APP_NAME" "$INSTALL_DIR/"
echo "   ✓ $INSTALL_DIR/$APP_NAME 설치 완료"
{helper_install_section}
# CLI 링크 생성
echo "🔗 명령행 도구 링크를 생성하는 중..."

# 기존 링크 제거
if [ -L "$CLI_LINK" ]; then
    echo "   기존 링크를 제거하는 중..."
    sudo rm "$CLI_LINK"
fi

# /usr/local/bin 디렉토리 생성 (권한 확인)
if [ ! -d "/usr/local/bin" ]; then
    echo "   /usr/local/bin 디렉토리를 생성하는 중..."
    sudo mkdir -p /usr/local/bin
fi

# 심볼릭 링크 생성
echo "   새 링크를 생성하는 중..."
sudo ln -s "$INSTALL_DIR/$APP_NAME/Contents/MacOS/$CLI_NAME" "$CLI_LINK"

echo "   ✓ $CLI_LINK 링크 생성 완료"

# 실행 권한 확인
chmod +x "$INSTALL_DIR/$APP_NAME/Contents/MacOS/$CLI_NAME"

echo ""
echo "✅ 설치가 완료되었습니다!"
echo ""
echo "📋 사용 방법:"
echo "   ts-cli --help"
echo "   ts-cli analyze --path /path/to/repository"
echo ""
echo "🌐 URL 프로토콜 사용:"
echo "   testscenariomaker:///path/to/your/repository"
{helper_usage_section}'''
        
        script_path = self.dist_dir / "install.sh"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(install_script)
        
        script_path.chmod(0o755)  # 실행 권한 부여
        
        print(f"   ✓ 설치 스크립트 생성: {script_path}")
        return script_path
    
    def create_uninstaller_script(self, helper_app: Path = None) -> Path:
        """제거 스크립트 생성"""
        print("🗑️ 제거 스크립트 생성 중...")
        
        # 헬퍼 앱 포함 여부에 따른 제거 스크립트 생성
        helper_uninstall_section = ""
        
        if helper_app and helper_app.exists():
            helper_name = helper_app.name
            helper_uninstall_section = f'''
# 헬퍼 앱 제거
HELPER_APP_NAME="{helper_name}"
if [ -d "$INSTALL_DIR/$HELPER_APP_NAME" ]; then
    echo "🛠️  헬퍼 앱을 제거하는 중..."
    rm -rf "$INSTALL_DIR/$HELPER_APP_NAME"
    echo "   ✓ $INSTALL_DIR/$HELPER_APP_NAME 제거 완료"
fi
'''

        uninstall_script = f'''#!/bin/bash
# TestscenarioMaker CLI 제거 스크립트

set -e

APP_NAME="TestscenarioMaker CLI.app"
INSTALL_DIR="/Applications"
CLI_LINK="/usr/local/bin/ts-cli"

echo "🗑️ TestscenarioMaker CLI 제거를 시작합니다..."

# CLI 링크 제거
if [ -L "$CLI_LINK" ]; then
    echo "🔗 명령행 도구 링크를 제거하는 중..."
    sudo rm "$CLI_LINK"
    echo "   ✓ $CLI_LINK 제거 완료"
fi

# 메인 애플리케이션 제거
if [ -d "$INSTALL_DIR/$APP_NAME" ]; then
    echo "📱 메인 애플리케이션을 제거하는 중..."
    rm -rf "$INSTALL_DIR/$APP_NAME"
    echo "   ✓ $INSTALL_DIR/$APP_NAME 제거 완료"
fi
{helper_uninstall_section}
echo ""
echo "✅ TestscenarioMaker CLI가 성공적으로 제거되었습니다."
echo "ℹ️  URL 프로토콜 등록은 시스템 재시작 후 완전히 제거됩니다."
'''
        
        script_path = self.dist_dir / "uninstall.sh"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(uninstall_script)
        
        script_path.chmod(0o755)
        
        print(f"   ✓ 제거 스크립트 생성: {script_path}")
        return script_path
    
    def create_readme(self, helper_app: Path = None) -> Path:
        """README 파일 생성"""
        print("📝 README 파일 생성 중...")
        
        # 헬퍼 앱 포함 여부에 따른 README 내용 생성
        helper_info_section = ""
        helper_install_section = ""
        
        if helper_app and helper_app.exists():
            helper_info_section = f'''
## 📱 포함된 앱

이 패키지에는 두 개의 앱이 포함되어 있습니다:

1. **TestscenarioMaker CLI.app** - 메인 CLI 도구
2. **{helper_app.name}** - 웹 브라우저 URL 프로토콜 헬퍼

### 헬퍼 앱의 역할

헬퍼 앱은 웹 브라우저에서 `testscenariomaker://` 링크를 클릭했을 때 macOS의 샌드박스 제약을 우회하여 CLI를 안정적으로 실행하는 역할을 합니다.

- **문제**: 브라우저에서 직접 CLI를 실행하면 샌드박스 제약으로 네트워크 통신이 차단됨
- **해결**: 헬퍼 앱이 독립적인 프로세스로 CLI를 실행하여 제약 우회
'''
            helper_install_section = '''
   - 헬퍼 앱도 자동으로 Applications 폴더에 설치됩니다
   - 첫 번째 URL 링크 클릭 시 브라우저에서 허용 여부를 묻습니다'''

        readme_content = f'''# TestscenarioMaker CLI v{self.version}

TestscenarioMaker를 위한 로컬 저장소 분석 CLI 도구입니다.
{helper_info_section}
## 설치 방법

1. **자동 설치 (권장)**
   - `install.sh` 스크립트를 실행하세요:
   ```bash
   ./install.sh
   ```{helper_install_section}

2. **수동 설치**
   - `TestscenarioMaker CLI.app`을 Applications 폴더로 드래그하세요
   {'- 헬퍼 앱도 Applications 폴더로 드래그하세요' if helper_app and helper_app.exists() else ''}
   - 터미널에서 다음 명령어를 실행하세요:
   ```bash
   ln -s "/Applications/TestscenarioMaker CLI.app/Contents/MacOS/ts-cli" /usr/local/bin/ts-cli
   ```

## 사용 방법

### 명령행에서 사용

```bash
# 도움말 보기
ts-cli --help

# 저장소 분석
ts-cli analyze --path /path/to/repository

# 저장소 정보 확인
ts-cli info /path/to/repository

# 설정 확인
ts-cli config-show
```

### 웹 브라우저에서 사용

```
testscenariomaker:///path/to/your/repository
```

## URL 프로토콜

설치 후 웹 브라우저에서 `testscenariomaker://` 링크를 클릭하면 {'헬퍼 앱이 자동으로 CLI를 실행합니다' if helper_app and helper_app.exists() else 'CLI가 자동으로 실행됩니다'}.

{'### 브라우저 호환성' if helper_app and helper_app.exists() else ''}
{'- **Safari**: 첫 번째 클릭 시 "허용" 선택' if helper_app and helper_app.exists() else ''}
{'- **Chrome**: 첫 번째 클릭 시 "열기" 선택' if helper_app and helper_app.exists() else ''}
{'- **Firefox**: 첫 번째 클릭 시 "링크 열기" 선택' if helper_app and helper_app.exists() else ''}

## 제거 방법

`uninstall.sh` 스크립트를 실행하세요:
```bash
./uninstall.sh
```

## 시스템 요구사항

- macOS 10.12 (Sierra) 이상
- 64비트 시스템

## 문제 해결

### URL 프로토콜이 작동하지 않는 경우

1. 시스템 재시작
2. 헬퍼 앱을 한 번 더블클릭하여 실행
3. 다음 명령어로 URL 스킴 등록 확인:
```bash
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker
```

## 지원

문제가 있으시면 https://github.com/testscenariomaker/cli/issues 에서 리포트해주세요.

---
© 2024 TestscenarioMaker Team
'''
        
        readme_path = self.dist_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"   ✓ README 생성: {readme_path}")
        return readme_path
    
    def create_dmg(self, app_bundle: Path, helper_app: Path = None) -> Path:
        """DMG 파일 생성"""
        print("💿 DMG 파일 생성 중...")
        
        dmg_name = f"TestscenarioMaker-CLI-{self.version}.dmg"
        dmg_path = self.dist_dir / dmg_name
        
        # 기존 DMG 제거
        if dmg_path.exists():
            dmg_path.unlink()
        
        # 임시 DMG 생성
        temp_dmg = self.dist_dir / "temp.dmg"
        if temp_dmg.exists():
            temp_dmg.unlink()
        
        try:
            # 1. 빈 DMG 생성 (100MB)
            print("   💿 빈 DMG 생성 중...")
            create_result = subprocess.run([
                'hdiutil', 'create',
                '-size', '100m',
                '-fs', 'HFS+',
                '-volname', f'TestscenarioMaker CLI {self.version}',
                str(temp_dmg)
            ], check=True, capture_output=True, text=True)
            
            if create_result.returncode != 0:
                raise RuntimeError(f"DMG 생성 실패: {create_result.stderr}")
            
            # 2. DMG 마운트
            print("   📂 DMG 마운트 중...")
            mount_result = subprocess.run([
                'hdiutil', 'attach',
                str(temp_dmg),
                '-readwrite',
                '-noverify'
            ], check=True, capture_output=True, text=True)
            
            if mount_result.returncode != 0:
                raise RuntimeError(f"DMG 마운트 실패: {mount_result.stderr}")
            
            # 마운트 포인트 찾기 (정규식 사용)
            mount_point = self._parse_mount_point(mount_result.stdout)
            
            if not mount_point or not mount_point.exists():
                raise RuntimeError("DMG 마운트 포인트를 찾을 수 없습니다")
            
            print(f"   📁 마운트 포인트: {mount_point}")
            
            # 3. 파일들을 DMG에 복사
            print("   📦 파일들을 DMG에 복사 중...")
            try:
                # 메인 CLI 앱 번들 복사
                shutil.copytree(app_bundle, mount_point / app_bundle.name)
                print(f"   ✓ CLI 앱 번들 복사 완료")
                
                # 헬퍼 앱 복사 (있는 경우)
                if helper_app and helper_app.exists():
                    shutil.copytree(helper_app, mount_point / helper_app.name)
                    print(f"   ✓ 헬퍼 앱 복사 완료: {helper_app.name}")
                
                # 설치/제거 스크립트 복사
                install_script = self.create_installer_script(helper_app)
                uninstall_script = self.create_uninstaller_script(helper_app)
                readme_file = self.create_readme(helper_app)
                
                shutil.copy2(install_script, mount_point)
                shutil.copy2(uninstall_script, mount_point)
                shutil.copy2(readme_file, mount_point)
                
                # DMG에 복사된 스크립트에 실행 권한 재설정
                (mount_point / install_script.name).chmod(0o755)
                (mount_point / uninstall_script.name).chmod(0o755)
                
                print(f"   ✓ 설치 스크립트 및 문서 복사 완료")
                
                # Applications 폴더 링크 생성
                subprocess.run([
                    'ln', '-s', '/Applications',
                    str(mount_point / 'Applications')
                ], check=True, capture_output=True)
                print(f"   ✓ Applications 링크 생성 완료")
                
            except Exception as e:
                print(f"   ❌ 파일 복사 중 오류: {e}")
                # 언마운트 시도
                try:
                    subprocess.run([
                        'hdiutil', 'detach', str(mount_point)
                    ], capture_output=True)
                except:
                    pass
                raise
            
            # 4. DMG 언마운트
            print("   📤 DMG 언마운트 중...")
            detach_result = subprocess.run([
                'hdiutil', 'detach',
                str(mount_point)
            ], check=True, capture_output=True, text=True)
            
            if detach_result.returncode != 0:
                print(f"   ⚠️ 언마운트 경고: {detach_result.stderr}")
            
            # 5. 최종 DMG 생성 (압축)
            print("   🗜️ DMG 압축 중...")
            convert_result = subprocess.run([
                'hdiutil', 'convert',
                str(temp_dmg),
                '-format', 'UDZO',
                '-o', str(dmg_path)
            ], check=True, capture_output=True, text=True)
            
            if convert_result.returncode != 0:
                raise RuntimeError(f"DMG 압축 실패: {convert_result.stderr}")
            
            print(f"   ✓ DMG 생성 완료: {dmg_path}")
            return dmg_path
            
        finally:
            # 임시 파일 정리
            if temp_dmg.exists():
                temp_dmg.unlink()
    
    def create_distribution(self) -> Path:
        """전체 배포 패키지 생성"""
        print("🚀 macOS 배포 패키지 생성 시작")
        print("=" * 50)
        
        try:
            # 1. .app 번들 생성 (메인 CLI 앱)
            app_bundle = self.create_app_bundle()
            
            # 2. 헬퍼 앱 빌드 (필요시)
            helper_app = self.build_helper_app_if_needed()
            
            # 3. DMG 생성 (메인 앱 + 헬퍼 앱)
            dmg_path = self.create_dmg(app_bundle, helper_app)
            
            print("=" * 50)
            print("✅ macOS 배포 패키지 생성 완료!")
            print(f"   DMG 파일: {dmg_path}")
            if helper_app:
                print(f"   헬퍼 앱 포함: {helper_app.name}")
            
            return dmg_path
            
        except Exception as e:
            print("=" * 50)
            print(f"❌ DMG 생성 실패: {e}")
            raise


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='macOS DMG 생성 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  python scripts/create_dmg.py                      # 헬퍼 앱 포함하여 DMG 생성
  python scripts/create_dmg.py --no-helper-app      # 헬퍼 앱 없이 DMG 생성
  python scripts/create_dmg.py --project-root /path # 다른 프로젝트 경로 지정
        '''
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help='프로젝트 루트 디렉토리'
    )
    parser.add_argument(
        '--no-helper-app',
        action='store_true',
        help='헬퍼 앱을 DMG에 포함하지 않음'
    )
    
    args = parser.parse_args()
    
    # macOS 확인
    if sys.platform != 'darwin':
        print("❌ 이 스크립트는 macOS에서만 실행할 수 있습니다.", file=sys.stderr)
        return 1
    
    try:
        # 헬퍼 앱 포함 여부 결정
        include_helper_app = not args.no_helper_app
        
        creator = DMGCreator(args.project_root, include_helper_app=include_helper_app)
        dmg_path = creator.create_distribution()
        
        print(f"\n🎉 DMG 설치 파일이 생성되었습니다:")
        print(f"   {dmg_path}")
        print(f"\n📋 다음 단계:")
        print(f"   1. DMG 파일을 더블클릭하여 마운트")
        print(f"   2. install.sh 스크립트 실행 또는 수동 설치")
        
        if include_helper_app:
            print(f"\n🛠️  헬퍼 앱 정보:")
            print(f"   - 웹 브라우저 샌드박스 제약 우회")
            print(f"   - testscenariomaker:// URL 프로토콜 안정적 처리")
            print(f"   - 브라우저별 호환성 최적화")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ DMG 생성 오류: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())