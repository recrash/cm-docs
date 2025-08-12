#!/usr/bin/env python3
"""
TestscenarioMaker CLI Helper App Builder

macOS 헬퍼 앱 자동 생성 스크립트
AppleScript 기반 헬퍼 앱을 생성하여 브라우저 샌드박스 제약을 우회합니다.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
import tempfile
import argparse
from typing import Dict, Any, Optional
import json


class HelperAppBuilder:
    """macOS 헬퍼 앱 빌더 클래스"""
    
    def __init__(self, project_root: Path, cli_executable: Optional[Path] = None):
        """
        헬퍼 앱 빌더 초기화
        
        Args:
            project_root: 프로젝트 루트 디렉토리
            cli_executable: CLI 실행파일 경로 (기본값: dist/ts-cli)
        """
        self.project_root = project_root.resolve()
        self.scripts_dir = self.project_root / "scripts"
        self.dist_dir = self.project_root / "dist"
        
        # CLI 실행파일 경로 설정
        if cli_executable:
            self.cli_executable = cli_executable.resolve()
        else:
            self.cli_executable = self.dist_dir / "ts-cli"
        
        # 헬퍼 앱 관련 파일 경로
        self.applescript_source = self.scripts_dir / "helper_app.applescript"
        self.plist_template = self.scripts_dir / "helper_app_info.plist"
        
        # 버전 정보
        self.version = self._get_version()
        self.app_name = "TestscenarioMaker Helper"
        
        print(f"🛠️  macOS 헬퍼 앱 빌더 초기화")
        print(f"   프로젝트 루트: {self.project_root}")
        print(f"   CLI 실행파일: {self.cli_executable}")
        print(f"   버전: {self.version}")
    
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
    
    def validate_prerequisites(self) -> None:
        """필수 조건 검증"""
        print("🔍 필수 조건 검증 중...")
        
        # macOS 플랫폼 확인
        print("macOS 플랫폼 확인")
        if sys.platform != 'darwin':
            raise RuntimeError("이 스크립트는 macOS에서만 실행할 수 있습니다.")
        
        # AppleScript 소스 파일 확인
        print("AppleScript 소스 파일 확인")
        if not self.applescript_source.exists():
            raise FileNotFoundError(f"AppleScript 소스를 찾을 수 없습니다: {self.applescript_source}")
        
        # Info.plist 템플릿 확인
        print("Info.plist 템플릿 확인")
        if not self.plist_template.exists():
            raise FileNotFoundError(f"Info.plist 템플릿을 찾을 수 없습니다: {self.plist_template}")
        
        # CLI 실행파일 확인
        print("CLI 실행파일 확인")
        if not self.cli_executable.exists():
            raise FileNotFoundError(
                f"CLI 실행파일을 찾을 수 없습니다: {self.cli_executable}\\n"
                f"먼저 'python scripts/build.py'를 실행하여 CLI를 빌드하세요."
            )
        
        print("CLI 실행파일이 올바른 파일인지 확인")
        if not self.cli_executable.is_file():
            raise FileNotFoundError(f"CLI 실행파일이 올바른 파일이 아닙니다: {self.cli_executable}")
        
        # osacompile 명령어 확인
        try:
            print("osacompile 명령어 확인")
            
            # 실제 AppleScript 파일로 osacompile 테스트
            test_output = tempfile.mktemp(suffix='.app')
            result = subprocess.run([
                'osacompile', 
                '-o', test_output,
                str(self.applescript_source)
            ], capture_output=True, text=True, check=False, timeout=30)
            
            # 테스트 파일 정리
            try:
                if os.path.exists(test_output):
                    shutil.rmtree(test_output)
            except:
                pass
            
            if result.returncode != 0:
                print(f"⚠️  osacompile 명령어 실행 실패 (종료 코드: {result.returncode})")
                if result.stderr:
                    print(f"   오류 메시지: {result.stderr.strip()}")
                if result.stdout:
                    print(f"   출력 메시지: {result.stdout.strip()}")
                raise RuntimeError(f"osacompile 명령어 실행 실패: {result.stderr}")
            
            print("   ✓ osacompile 명령어 확인 완료")
            
        except subprocess.TimeoutExpired:
            print("osacompile 명령어 실행 시간 초과")
            raise RuntimeError("osacompile 명령어 실행 시간 초과")
        except FileNotFoundError:
            print("osacompile 명령어를 찾을 수 없습니다. macOS 개발자 도구가 설치되어 있는지 확인하세요.")
            raise RuntimeError("osacompile 명령어를 찾을 수 없습니다. macOS 개발자 도구를 설치하세요.")
        except Exception as e:
            print(f"osacompile 명령어 확인 중 예상치 못한 오류: {e}")
            raise RuntimeError(f"osacompile 명령어 확인 실패: {e}")
        
        print("   ✓ 모든 필수 조건 확인 완료")
    
    def compile_applescript(self) -> Path:
        """AppleScript 컴파일"""
        print("📜 AppleScript 컴파일 중...")
        
        app_name = f"{self.app_name}.app"
        app_path = self.dist_dir / app_name
        
        # 기존 헬퍼 앱 제거
        if app_path.exists():
            shutil.rmtree(app_path)
            print(f"   🗑️  기존 헬퍼 앱 제거: {app_path}")
        
        # 출력 디렉토리 생성
        self.dist_dir.mkdir(exist_ok=True)
        
        # AppleScript 컴파일 실행
        try:
            compile_result = subprocess.run([
                'osacompile',
                '-o', str(app_path),
                str(self.applescript_source)
            ], check=True, capture_output=True, text=True)
            
            print(f"   ✓ AppleScript 컴파일 완료: {app_path}")
            return app_path
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"AppleScript 컴파일 실패: {e.stderr}")
    
    def embed_cli_executable(self, app_path: Path) -> None:
        """CLI 실행파일을 헬퍼 앱에 내장"""
        print("📦 CLI 실행파일 내장 중...")
        
        resources_dir = app_path / "Contents" / "Resources"
        
        # Resources 디렉토리가 없으면 생성
        resources_dir.mkdir(parents=True, exist_ok=True)
        
        # CLI 실행파일 복사
        target_cli_path = resources_dir / "TestscenarioMaker-CLI"
        shutil.copy2(self.cli_executable, target_cli_path)
        
        # 실행 권한 부여
        target_cli_path.chmod(0o755)
        
        print(f"   ✓ CLI 실행파일 내장 완료: {target_cli_path}")
        print(f"   📄 파일 크기: {target_cli_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    def update_info_plist(self, app_path: Path) -> None:
        """Info.plist 업데이트"""
        print("📄 Info.plist 업데이트 중...")
        
        contents_dir = app_path / "Contents"
        info_plist_path = contents_dir / "Info.plist"
        
        # 기존 Info.plist 백업
        if info_plist_path.exists():
            backup_path = info_plist_path.with_suffix('.plist.backup')
            shutil.copy2(info_plist_path, backup_path)
            print(f"   💾 기존 Info.plist 백업: {backup_path}")
        
        # 템플릿에서 Info.plist 생성
        with open(self.plist_template, 'r', encoding='utf-8') as f:
            plist_content = f.read()
        
        # 버전 정보 교체
        plist_content = plist_content.replace('{version}', self.version)
        
        # 새로운 Info.plist 작성
        with open(info_plist_path, 'w', encoding='utf-8') as f:
            f.write(plist_content)
        
        print(f"   ✓ Info.plist 업데이트 완료: {info_plist_path}")
    
    def sign_app(self, app_path: Path) -> None:
        """앱 서명 (Ad-hoc signing)"""
        print("🔐 앱 서명 중...")
        
        try:
            # Ad-hoc 서명 적용
            sign_result = subprocess.run([
                'codesign',
                '--force',
                '--deep',
                '-s', '-',  # Ad-hoc signing
                str(app_path)
            ], check=True, capture_output=True, text=True)
            
            print("   ✓ Ad-hoc 서명 완료")
            
            # 서명 검증
            verify_result = subprocess.run([
                'codesign',
                '--verify',
                '--deep',
                '--strict',
                str(app_path)
            ], check=True, capture_output=True, text=True)
            
            print("   ✓ 서명 검증 완료")
            
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  서명 경고: {e.stderr}")
            print("   ℹ️  Ad-hoc 서명이 적용되지 않았지만 앱은 여전히 작동할 수 있습니다.")
    
    def remove_quarantine(self, app_path: Path) -> None:
        """격리 속성 제거"""
        print("🧹 격리 속성 제거 중...")
        
        try:
            # com.apple.quarantine 속성 제거
            xattr_result = subprocess.run([
                'xattr', '-d', 'com.apple.quarantine', str(app_path)
            ], capture_output=True, text=True)
            
            if xattr_result.returncode == 0:
                print("   ✓ 격리 속성 제거 완료")
            else:
                print("   ℹ️  격리 속성이 없거나 이미 제거됨")
            
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  격리 속성 제거 경고: {e.stderr}")
    
    def create_validation_script(self, app_path: Path) -> Path:
        """검증 스크립트 생성"""
        print("🧪 검증 스크립트 생성 중...")
        
        validation_script = f'''#!/bin/bash
# TestscenarioMaker Helper App 검증 스크립트

set -e

APP_PATH="{app_path}"
CLI_PATH="$APP_PATH/Contents/Resources/TestscenarioMaker-CLI"

echo "🔍 TestscenarioMaker Helper App 검증"
echo "   앱 경로: $APP_PATH"
echo

# 1. 앱 번들 구조 확인
echo "1. 앱 번들 구조 확인..."
if [ -d "$APP_PATH" ]; then
    echo "   ✓ 앱 번들 존재"
else
    echo "   ❌ 앱 번들 없음"
    exit 1
fi

# 2. CLI 실행파일 확인
echo "2. CLI 실행파일 확인..."
if [ -f "$CLI_PATH" ]; then
    echo "   ✓ CLI 실행파일 존재"
    if [ -x "$CLI_PATH" ]; then
        echo "   ✓ 실행 권한 있음"
    else
        echo "   ❌ 실행 권한 없음"
        exit 1
    fi
else
    echo "   ❌ CLI 실행파일 없음"
    exit 1
fi

# 3. Info.plist 확인
echo "3. Info.plist 확인..."
PLIST_PATH="$APP_PATH/Contents/Info.plist"
if [ -f "$PLIST_PATH" ]; then
    echo "   ✓ Info.plist 존재"
    
    # URL 스킴 등록 확인
    if plutil -extract CFBundleURLTypes.0.CFBundleURLSchemes.0 raw "$PLIST_PATH" 2>/dev/null | grep -q "testscenariomaker"; then
        echo "   ✓ testscenariomaker URL 스킴 등록됨"
    else
        echo "   ❌ URL 스킴 등록 안됨"
        exit 1
    fi
else
    echo "   ❌ Info.plist 없음"
    exit 1
fi

# 4. 서명 상태 확인
echo "4. 서명 상태 확인..."
if codesign --verify --deep --strict "$APP_PATH" 2>/dev/null; then
    echo "   ✓ 앱 서명 유효"
else
    echo "   ⚠️  앱 서명 없음 (Ad-hoc 서명 권장)"
fi

# 5. URL 스킴 등록 상태 확인 (시스템 레벨)
echo "5. 시스템 URL 스킴 등록 확인..."
if /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep -q "testscenariomaker"; then
    echo "   ✓ 시스템에 URL 스킴 등록됨"
else
    echo "   ⚠️  시스템에 URL 스킴 미등록 (앱을 한 번 실행하면 등록됩니다)"
fi

echo
echo "✅ 검증 완료! Helper App이 올바르게 구성되었습니다."
echo
echo "📋 사용 방법:"
echo "1. 헬퍼 앱을 Applications 폴더로 이동"
echo "2. 웹 브라우저에서 testscenariomaker:// 링크 클릭"
echo "3. Helper App이 자동으로 CLI를 실행"
echo
echo "🧪 테스트 명령어:"
echo "   open 'testscenariomaker:///path/to/your/repository'"
'''
        
        script_path = self.dist_dir / "validate_helper_app.sh"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(validation_script)
        
        script_path.chmod(0o755)
        
        print(f"   ✓ 검증 스크립트 생성: {script_path}")
        return script_path
    
    def create_build_info(self, app_path: Path) -> Path:
        """빌드 정보 JSON 생성"""
        print("📊 빌드 정보 생성 중...")
        
        build_info = {
            "app_name": self.app_name,
            "version": self.version,
            "build_date": str(__import__('datetime').datetime.now()),
            "app_path": str(app_path),
            "cli_executable": str(self.cli_executable),
            "bundle_identifier": "com.testscenariomaker.helper",
            "url_scheme": "testscenariomaker",
            "macos_version": subprocess.run(['sw_vers', '-productVersion'], 
                                         capture_output=True, text=True).stdout.strip(),
            "builder_script": str(__file__),
            "file_sizes": {
                "app_bundle": self._get_directory_size(app_path),
                "cli_executable": self.cli_executable.stat().st_size
            }
        }
        
        info_path = self.dist_dir / "helper_app_build_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)
        
        print(f"   ✓ 빌드 정보 생성: {info_path}")
        return info_path
    
    def _get_directory_size(self, path: Path) -> int:
        """디렉토리 총 크기 계산"""
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except:
            pass
        return total_size
    
    def build_helper_app(self) -> Path:
        """헬퍼 앱 전체 빌드 프로세스"""
        print("🚀 macOS 헬퍼 앱 빌드 시작")
        print("=" * 50)
        
        try:
            # 1. 필수 조건 검증
            self.validate_prerequisites()
            
            # 2. AppleScript 컴파일
            app_path = self.compile_applescript()
            
            # 3. CLI 실행파일 내장
            self.embed_cli_executable(app_path)
            
            # 4. Info.plist 업데이트
            self.update_info_plist(app_path)
            
            # 5. 앱 서명
            self.sign_app(app_path)
            
            # 6. 격리 속성 제거
            self.remove_quarantine(app_path)
            
            # 7. 검증 스크립트 생성
            validation_script = self.create_validation_script(app_path)
            
            # 8. 빌드 정보 생성
            build_info = self.create_build_info(app_path)
            
            print("=" * 50)
            print("✅ 헬퍼 앱 빌드 완료!")
            print(f"   앱 경로: {app_path}")
            print(f"   앱 크기: {self._get_directory_size(app_path) / 1024 / 1024:.1f} MB")
            print(f"   검증 스크립트: {validation_script}")
            print(f"   빌드 정보: {build_info}")
            
            return app_path
            
        except Exception as e:
            print("=" * 50)
            print(f"❌ 헬퍼 앱 빌드 실패: {e}")
            raise


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='TestscenarioMaker CLI macOS 헬퍼 앱 빌더',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  python scripts/build_helper_app.py
  python scripts/build_helper_app.py --cli-executable ./dist/ts-cli
  python scripts/build_helper_app.py --project-root /path/to/project
        '''
    )
    
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help='프로젝트 루트 디렉토리 (기본값: 스크립트 위치의 상위 디렉토리)'
    )
    
    parser.add_argument(
        '--cli-executable',
        type=Path,
        help='CLI 실행파일 경로 (기본값: {project_root}/dist/ts-cli)'
    )
    
    args = parser.parse_args()
    
    # macOS 확인
    if sys.platform != 'darwin':
        print("❌ 이 스크립트는 macOS에서만 실행할 수 있습니다.", file=sys.stderr)
        return 1
    
    try:
        builder = HelperAppBuilder(args.project_root, args.cli_executable)
        app_path = builder.build_helper_app()
        
        print(f"\\n📋 다음 단계:")
        print(f"   1. 헬퍼 앱을 Applications 폴더로 이동:")
        print(f"      mv '{app_path}' /Applications/")
        print(f"   2. 검증 스크립트 실행:")
        print(f"      ./dist/validate_helper_app.sh")
        print(f"   3. 테스트:")
        print(f"      open 'testscenariomaker:///path/to/your/repository'")
        
        return 0
        
    except Exception as e:
        print(f"\\n❌ 헬퍼 앱 빌드 오류: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())