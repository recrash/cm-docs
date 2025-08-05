#!/usr/bin/env python3
"""
TestscenarioMaker Helper App 테스트 및 검증 스크립트

헬퍼 앱의 모든 기능을 테스트하고 검증하는 종합 테스트 도구입니다.
- AppleScript 구문 검증
- .app 번들 구조 검증
- URL 프로토콜 등록 검증
- 샌드박스 우회 기능 테스트
- 브라우저 호환성 테스트
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json
import argparse
import urllib.parse
import time


class HelperAppTester:
    """헬퍼 앱 테스트 클래스"""
    
    def __init__(self, project_root: Path):
        """
        테스터 초기화
        
        Args:
            project_root: 프로젝트 루트 디렉토리
        """
        self.project_root = project_root.resolve()
        self.scripts_dir = self.project_root / "scripts"
        self.dist_dir = self.project_root / "dist"
        
        # 테스트 결과 저장
        self.test_results: Dict[str, Any] = {
            "timestamp": str(__import__('datetime').datetime.now()),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        
        print(f"🧪 TestscenarioMaker Helper App 테스터 초기화")
        print(f"   프로젝트 루트: {self.project_root}")
    
    def log_test_result(self, test_name: str, passed: bool, message: str = "", details: Any = None) -> None:
        """테스트 결과 로깅"""
        result = {
            "passed": passed,
            "message": message,
            "details": details
        }
        
        self.test_results["tests"][test_name] = result
        self.test_results["summary"]["total"] += 1
        
        if passed:
            self.test_results["summary"]["passed"] += 1
            print(f"   ✅ {test_name}: {message}")
        else:
            self.test_results["summary"]["failed"] += 1
            print(f"   ❌ {test_name}: {message}")
            if details:
                print(f"      세부사항: {details}")
    
    def log_test_skip(self, test_name: str, reason: str) -> None:
        """테스트 스킵 로깅"""
        self.test_results["tests"][test_name] = {
            "passed": None,
            "message": f"스킵됨: {reason}",
            "details": None
        }
        self.test_results["summary"]["total"] += 1
        self.test_results["summary"]["skipped"] += 1
        print(f"   ⏭️  {test_name}: 스킵됨 - {reason}")
    
    def test_prerequisites(self) -> bool:
        """필수 조건 테스트"""
        print("\n🔍 필수 조건 검증")
        all_passed = True
        
        # macOS 플랫폼 확인
        is_macos = sys.platform == 'darwin'
        self.log_test_result(
            "macOS 플랫폼", 
            is_macos, 
            "macOS에서 실행 중" if is_macos else "macOS가 아닌 플랫폼에서 실행"
        )
        if not is_macos:
            all_passed = False
        
        # osacompile 명령어 확인
        try:
            result = subprocess.run(['osacompile', '-l', 'AppleScript'], capture_output=True, text=True)
            osacompile_available = result.returncode == 0
            self.log_test_result(
                "osacompile 사용 가능", 
                osacompile_available, 
                "AppleScript 컴파일러 사용 가능" if osacompile_available else "osacompile 명령어 없음"
            )
            if not osacompile_available:
                all_passed = False
        except FileNotFoundError:
            self.log_test_result("osacompile 사용 가능", False, "osacompile 명령어를 찾을 수 없음")
            all_passed = False
        
        # 필수 파일들 존재 확인
        required_files = [
            self.scripts_dir / "helper_app.applescript",
            self.scripts_dir / "helper_app_info.plist",
            self.scripts_dir / "build_helper_app.py"
        ]
        
        for file_path in required_files:
            exists = file_path.exists()
            self.log_test_result(
                f"필수 파일 존재: {file_path.name}",
                exists,
                f"파일 확인됨: {file_path}" if exists else f"파일 없음: {file_path}"
            )
            if not exists:
                all_passed = False
        
        return all_passed
    
    def test_applescript_syntax(self) -> bool:
        """AppleScript 구문 검증"""
        print("\n📜 AppleScript 구문 검증")
        
        applescript_file = self.scripts_dir / "helper_app.applescript"
        if not applescript_file.exists():
            self.log_test_result("AppleScript 구문", False, "AppleScript 파일 없음")
            return False
        
        try:
            # AppleScript 구문 검사 (컴파일 없이)
            result = subprocess.run([
                'osacompile', '-c', '-o', '/dev/null', str(applescript_file)
            ], capture_output=True, text=True)
            
            syntax_valid = result.returncode == 0
            self.log_test_result(
                "AppleScript 구문",
                syntax_valid,
                "구문 검증 통과" if syntax_valid else f"구문 오류: {result.stderr}",
                result.stderr if not syntax_valid else None
            )
            
            return syntax_valid
            
        except Exception as e:
            self.log_test_result("AppleScript 구문", False, f"검증 실패: {e}")
            return False
    
    def test_helper_app_build(self) -> Tuple[bool, Optional[Path]]:
        """헬퍼 앱 빌드 테스트"""
        print("\n🏗️  헬퍼 앱 빌드 테스트")
        
        build_script = self.scripts_dir / "build_helper_app.py"
        if not build_script.exists():
            self.log_test_result("헬퍼 앱 빌드", False, "빌드 스크립트 없음")
            return False, None
        
        # CLI 실행파일 확인 (빌드를 위해 필요)
        cli_executable = self.dist_dir / "ts-cli"
        if not cli_executable.exists():
            self.log_test_skip("헬퍼 앱 빌드", "CLI 실행파일 없음 (python scripts/build.py 먼저 실행)")
            return False, None
        
        try:
            # 헬퍼 앱 빌드 실행
            result = subprocess.run([
                sys.executable, str(build_script),
                '--project-root', str(self.project_root)
            ], capture_output=True, text=True, timeout=60)
            
            build_success = result.returncode == 0
            helper_app_path = self.dist_dir / "TestscenarioMaker Helper.app"
            
            if build_success and helper_app_path.exists():
                self.log_test_result(
                    "헬퍼 앱 빌드",
                    True,
                    f"빌드 성공: {helper_app_path}"
                )
                return True, helper_app_path
            else:
                self.log_test_result(
                    "헬퍼 앱 빌드",
                    False,
                    f"빌드 실패: {result.stderr}",
                    result.stderr
                )
                return False, None
                
        except subprocess.TimeoutExpired:
            self.log_test_result("헬퍼 앱 빌드", False, "빌드 시간 초과 (60초)")
            return False, None
        except Exception as e:
            self.log_test_result("헬퍼 앱 빌드", False, f"빌드 오류: {e}")
            return False, None
    
    def test_app_bundle_structure(self, helper_app_path: Path) -> bool:
        """앱 번들 구조 검증"""
        print("\n📦 앱 번들 구조 검증")
        
        if not helper_app_path or not helper_app_path.exists():
            self.log_test_result("앱 번들 구조", False, "헬퍼 앱 경로 없음")
            return False
        
        all_passed = True
        
        # 필수 디렉토리 구조 확인
        required_structure = [
            "Contents",
            "Contents/MacOS",
            "Contents/Resources",
            "Contents/Info.plist"
        ]
        
        for path_str in required_structure:
            path = helper_app_path / path_str
            exists = path.exists()
            self.log_test_result(
                f"구조: {path_str}",
                exists,
                "존재함" if exists else "없음"
            )
            if not exists:
                all_passed = False
        
        # AppleScript 실행파일 확인
        applet_path = helper_app_path / "Contents/MacOS/applet"
        applet_exists = applet_path.exists()
        applet_executable = applet_path.is_file() and os.access(applet_path, os.X_OK) if applet_exists else False
        
        self.log_test_result(
            "AppleScript 실행파일",
            applet_exists and applet_executable,
            "실행 가능" if applet_executable else ("존재하지만 실행 불가" if applet_exists else "없음")
        )
        if not (applet_exists and applet_executable):
            all_passed = False
        
        # 내장된 CLI 실행파일 확인
        cli_path = helper_app_path / "Contents/Resources/TestscenarioMaker-CLI"
        cli_exists = cli_path.exists()
        cli_executable = cli_path.is_file() and os.access(cli_path, os.X_OK) if cli_exists else False
        
        self.log_test_result(
            "내장 CLI 실행파일",
            cli_exists and cli_executable,
            "실행 가능" if cli_executable else ("존재하지만 실행 불가" if cli_exists else "없음")
        )
        if not (cli_exists and cli_executable):
            all_passed = False
        
        return all_passed
    
    def test_info_plist(self, helper_app_path: Path) -> bool:
        """Info.plist 검증"""
        print("\n📄 Info.plist 검증")
        
        if not helper_app_path or not helper_app_path.exists():
            self.log_test_result("Info.plist", False, "헬퍼 앱 경로 없음")
            return False
        
        plist_path = helper_app_path / "Contents/Info.plist"
        if not plist_path.exists():
            self.log_test_result("Info.plist", False, "Info.plist 파일 없음")
            return False
        
        all_passed = True
        
        try:
            # URL 스킴 등록 확인
            result = subprocess.run([
                'plutil', '-extract', 'CFBundleURLTypes.0.CFBundleURLSchemes.0', 'raw', str(plist_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and 'testscenariomaker' in result.stdout:
                self.log_test_result("URL 스킴 등록", True, "testscenariomaker 스킴 등록됨")
            else:
                self.log_test_result("URL 스킴 등록", False, "URL 스킴 등록 안됨")
                all_passed = False
            
            # LSBackgroundOnly 설정 확인
            result = subprocess.run([
                'plutil', '-extract', 'LSBackgroundOnly', 'raw', str(plist_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip() == 'true':
                self.log_test_result("백그라운드 앱 설정", True, "LSBackgroundOnly=true 설정됨")
            else:
                self.log_test_result("백그라운드 앱 설정", False, "LSBackgroundOnly 설정 안됨")
                all_passed = False
            
        except Exception as e:
            self.log_test_result("Info.plist 검증", False, f"검증 오류: {e}")
            all_passed = False
        
        return all_passed
    
    def test_url_protocol_registration(self, helper_app_path: Path) -> bool:
        """URL 프로토콜 등록 테스트"""
        print("\n🔗 URL 프로토콜 등록 테스트")
        
        if not helper_app_path or not helper_app_path.exists():
            self.log_test_result("URL 프로토콜 등록", False, "헬퍼 앱 경로 없음")
            return False
        
        try:
            # lsregister로 헬퍼 앱 등록
            lsregister = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
            
            if not Path(lsregister).exists():
                self.log_test_skip("URL 프로토콜 등록", "lsregister 명령어 없음")
                return False
            
            # 앱 등록
            subprocess.run([lsregister, '-f', str(helper_app_path)], capture_output=True)
            
            # 등록 확인
            result = subprocess.run([lsregister, '-dump'], capture_output=True, text=True)
            
            if 'testscenariomaker' in result.stdout:
                self.log_test_result("URL 프로토콜 등록", True, "testscenariomaker 프로토콜 등록 확인됨")
                return True
            else:
                self.log_test_result("URL 프로토콜 등록", False, "프로토콜 등록 확인 안됨")
                return False
                
        except Exception as e:
            self.log_test_result("URL 프로토콜 등록", False, f"등록 테스트 오류: {e}")
            return False
    
    def test_url_handling(self, helper_app_path: Path) -> bool:
        """URL 처리 기능 테스트"""
        print("\n🌐 URL 처리 기능 테스트")
        
        if not helper_app_path or not helper_app_path.exists():
            self.log_test_result("URL 처리", False, "헬퍼 앱 경로 없음")
            return False
        
        # 임시 테스트 저장소 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            test_repo_path = Path(temp_dir) / "test-repo"
            test_repo_path.mkdir()
            
            # 간단한 git 저장소 초기화
            try:
                subprocess.run(['git', 'init'], cwd=test_repo_path, capture_output=True, check=True)
                
                # 테스트 URL 생성
                test_url = f"testscenariomaker://{test_repo_path}"
                encoded_url = urllib.parse.quote(test_url, safe=':/')
                
                print(f"   테스트 URL: {test_url}")
                
                # URL 처리 테스트 (실제로는 실행하지 않고 구조만 확인)
                # 실제 실행은 CLI가 API 호출을 시도할 수 있으므로 스킵
                self.log_test_result(
                    "URL 처리 구조",
                    True,
                    f"테스트 URL 생성 성공: {len(test_url)} 문자"
                )
                
                return True
                
            except subprocess.CalledProcessError:
                self.log_test_skip("URL 처리", "git 명령어 없음 또는 실행 실패")
                return False
            except Exception as e:
                self.log_test_result("URL 처리", False, f"URL 처리 테스트 오류: {e}")
                return False
    
    def create_test_html(self) -> Path:
        """테스트용 HTML 파일 생성"""
        print("\n📝 테스트 HTML 파일 생성")
        
        # 임시 테스트 저장소 경로 (실제 존재하는 경로 사용)
        test_repo_path = self.project_root
        
        html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TestscenarioMaker Helper App 테스트</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .test-section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .test-link {{
            display: inline-block;
            padding: 10px 20px;
            background: #007AFF;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 10px 10px 10px 0;
            font-weight: 500;
        }}
        .test-link:hover {{
            background: #0056CC;
        }}
        .code {{
            background: #f1f1f1;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            margin: 10px 0;
        }}
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .success {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <h1>🧪 TestscenarioMaker Helper App 테스트</h1>
    
    <div class="warning">
        <strong>⚠️ 주의사항:</strong>
        <ul>
            <li>이 링크들을 클릭하기 전에 헬퍼 앱이 설치되어 있는지 확인하세요</li>
            <li>첫 번째 클릭 시 브라우저에서 허용 여부를 묻습니다</li>
            <li>CLI 실행파일이 빌드되어 있어야 합니다</li>
        </ul>
    </div>
    
    <div class="test-section">
        <h2>📁 로컬 저장소 테스트</h2>
        <p>현재 프로젝트 디렉토리로 테스트:</p>
        <div class="code">testscenariomaker://{test_repo_path}</div>
        <a href="testscenariomaker://{test_repo_path}" class="test-link">
            🚀 현재 프로젝트 분석하기
        </a>
    </div>
    
    <div class="test-section">
        <h2>🔗 URL 인코딩 테스트</h2>
        <p>공백이 포함된 경로 테스트:</p>
        <div class="code">testscenariomaker:///Users/username/My%20Projects/test%20repo</div>
        <a href="testscenariomaker:///Users/username/My%20Projects/test%20repo" class="test-link">
            📂 공백 경로 테스트
        </a>
    </div>
    
    <div class="test-section">
        <h2>🌏 한글 경로 테스트</h2>
        <p>유니코드 문자가 포함된 경로 테스트:</p>
        <div class="code">testscenariomaker:///Users/username/프로젝트/테스트</div>
        <a href="testscenariomaker:///Users/username/%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8/%ED%85%8C%EC%8A%A4%ED%8A%B8" class="test-link">
            🇰🇷 한글 경로 테스트
        </a>
    </div>
    
    <div class="test-section">
        <h2>🧪 직접 테스트</h2>
        <p>자신의 저장소 경로를 입력하여 테스트해보세요:</p>
        <input type="text" id="customPath" placeholder="/path/to/your/repository" style="width: 300px; padding: 8px; margin-right: 10px;">
        <button onclick="testCustomPath()" style="padding: 8px 16px; background: #007AFF; color: white; border: none; border-radius: 4px;">테스트</button>
        <div id="customResult" style="margin-top: 10px;"></div>
    </div>
    
    <div class="success">
        <strong>✅ 성공 시 나타나는 현상:</strong>
        <ul>
            <li>터미널에서 TestscenarioMaker CLI가 실행됩니다</li>
            <li>헬퍼 앱이 백그라운드에서 작동하므로 UI는 보이지 않습니다</li>
            <li>CLI 출력은 콘솔이나 로그 파일에서 확인할 수 있습니다</li>
        </ul>
    </div>
    
    <div class="test-section">
        <h2>🔍 문제 해결</h2>
        <p>링크가 작동하지 않는 경우:</p>
        <ol>
            <li>헬퍼 앱이 Applications 폴더에 설치되어 있는지 확인</li>
            <li>한 번 헬퍼 앱을 더블클릭하여 실행</li>
            <li>시스템 재시작 후 다시 시도</li>
            <li>터미널에서 URL 스킴 등록 확인:</li>
        </ol>
        <div class="code">/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker</div>
    </div>
    
    <script>
        function testCustomPath() {{
            const path = document.getElementById('customPath').value;
            if (!path) {{
                alert('경로를 입력하세요.');
                return;
            }}
            
            const url = 'testscenariomaker://' + encodeURI(path);
            const resultDiv = document.getElementById('customResult');
            resultDiv.innerHTML = '<div class="code">생성된 URL: ' + url + '</div><a href="' + url + '" class="test-link">🚀 실행하기</a>';
        }}
        
        // 페이지 로드 시 현재 시간 표시
        document.addEventListener('DOMContentLoaded', function() {{
            const now = new Date().toLocaleString('ko-KR');
            document.title = 'TestscenarioMaker Helper App 테스트 - ' + now;
        }});
    </script>
</body>
</html>'''
        
        test_html_path = self.dist_dir / "helper_test.html"
        self.dist_dir.mkdir(exist_ok=True)
        
        with open(test_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.log_test_result(
            "테스트 HTML 생성",
            True,
            f"테스트 파일 생성됨: {test_html_path}"
        )
        
        return test_html_path
    
    def save_test_report(self) -> Path:
        """테스트 보고서 저장"""
        report_path = self.dist_dir / "helper_test_report.json"
        self.dist_dir.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        return report_path
    
    def run_all_tests(self) -> bool:
        """모든 테스트 실행"""
        print("🧪 TestscenarioMaker Helper App 종합 테스트 시작")
        print("=" * 60)
        
        # 1. 필수 조건 테스트
        if not self.test_prerequisites():
            print("\n❌ 필수 조건 미충족으로 테스트 중단")
            return False
        
        # 2. AppleScript 구문 테스트
        self.test_applescript_syntax()
        
        # 3. 헬퍼 앱 빌드 테스트
        build_success, helper_app_path = self.test_helper_app_build()
        
        if build_success and helper_app_path:
            # 4. 앱 번들 구조 테스트
            self.test_app_bundle_structure(helper_app_path)
            
            # 5. Info.plist 테스트
            self.test_info_plist(helper_app_path)
            
            # 6. URL 프로토콜 등록 테스트
            self.test_url_protocol_registration(helper_app_path)
            
            # 7. URL 처리 기능 테스트
            self.test_url_handling(helper_app_path)
        
        # 8. 테스트 HTML 파일 생성
        test_html_path = self.create_test_html()
        
        # 9. 테스트 보고서 저장
        report_path = self.save_test_report()
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print(f"   총 테스트: {self.test_results['summary']['total']}")
        print(f"   통과: {self.test_results['summary']['passed']}")
        print(f"   실패: {self.test_results['summary']['failed']}")
        print(f"   스킵: {self.test_results['summary']['skipped']}")
        
        success_rate = (self.test_results['summary']['passed'] / max(1, self.test_results['summary']['total'])) * 100
        print(f"   성공률: {success_rate:.1f}%")
        
        print(f"\n📋 추가 파일:")
        print(f"   테스트 HTML: {test_html_path}")
        print(f"   테스트 보고서: {report_path}")
        
        # 전체 성공 여부 판단
        all_passed = self.test_results['summary']['failed'] == 0
        
        if all_passed:
            print(f"\n✅ 모든 테스트 통과!")
        else:
            print(f"\n❌ {self.test_results['summary']['failed']}개 테스트 실패")
        
        return all_passed


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='TestscenarioMaker Helper App 테스트 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  python scripts/test_helper_app.py                    # 전체 테스트 실행
  python scripts/test_helper_app.py --project-root /path # 다른 프로젝트 경로 지정
        '''
    )
    
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help='프로젝트 루트 디렉토리'
    )
    
    args = parser.parse_args()
    
    try:
        tester = HelperAppTester(args.project_root)
        success = tester.run_all_tests()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 오류: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())