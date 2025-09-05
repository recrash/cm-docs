#!/usr/bin/env python3
"""
TestscenarioMaker CLI 빌드 스크립트

PyInstaller를 사용하여 OS별 실행파일을 생성합니다.
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path
import argparse
import json
from typing import Dict, List, Optional, Any


class BuildError(Exception):
    """빌드 관련 오류"""
    pass


class CLIBuilder:
    """CLI 빌드 관리 클래스"""
    
    def __init__(self, project_root: Path):
        """
        빌드 관리자 초기화
        
        Args:
            project_root: 프로젝트 루트 디렉토리
        """
        self.project_root = project_root.resolve()
        self.src_dir = self.project_root / "src"
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.scripts_dir = self.project_root / "scripts"
        
        self.platform_name = platform.system().lower()
        self.arch = platform.machine().lower()
        
        # 버전 정보 로드
        self.version = self._get_version()
        
        print(f"빌드 환경 초기화")
        print(f"   플랫폼: {self.platform_name} ({self.arch})")
        print(f"   버전: {self.version}")
        print(f"   프로젝트 루트: {self.project_root}")
    
    def _get_version(self) -> str:
        """버전 정보 조회"""
        try:
            # __init__.py에서 버전 정보 추출
            init_file = self.src_dir / "ts_cli" / "__init__.py"
            if init_file.exists():
                with open(init_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('__version__'):
                            return line.split('"')[1]
            return "1.0.0"
        except Exception:
            return "1.0.0"
    
    def clean_build_dirs(self) -> None:
        """빌드 디렉토리 정리"""
        print("빌드 디렉토리 정리 중...")
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                try:
                    # 기본 삭제 시도 (모든 플랫폼에서 동작)
                    shutil.rmtree(dir_path)
                    print(f"   {dir_path.name} 정리 완료")
                except PermissionError as e:
                    # Windows에서만 추가 처리
                    if self.platform_name == 'windows':
                        print(f"   Windows 권한 오류 발생: {dir_path.name}")
                        print(f"   Windows 전용 정리 방법 시도 중...")
                        
                        try:
                            self._safe_remove_windows_dir(dir_path)
                            print(f"   {dir_path.name} Windows 정리 완료")
                        except Exception as win_error:
                            print(f"   Windows 정리도 실패: {win_error}")
                            print(f"   해결 방법:")
                            print(f"      1. 관리자 권한으로 PowerShell 실행")
                            print(f"      2. 수동 삭제: Remove-Item -Path '{dir_path}' -Recurse -Force")
                            print(f"      3. 또는 --no-clean 옵션으로 빌드 재시도")
                            raise BuildError(f"Windows 디렉토리 삭제 실패: {e}")
                    else:
                        # macOS/Linux에서는 원래 오류 그대로 전파
                        raise BuildError(f"디렉토리 삭제 권한 오류: {e}")
                except Exception as e:
                    # 기타 오류는 모든 플랫폼에서 동일하게 처리
                    print(f"   {dir_path.name} 정리 실패: {e}")
                    raise BuildError(f"디렉토리 정리 실패: {e}")
            
            # 디렉토리 재생성 (모든 플랫폼에서 동일)
            dir_path.mkdir(parents=True, exist_ok=True)

    def _safe_remove_windows_dir(self, dir_path: Path) -> None:
        """Windows에서 안전한 디렉토리 삭제 (크로스 플랫폼 호환성 유지)"""
        import time
        
        # 1차 시도: 파일 속성 변경 후 삭제
        try:
            # Windows에서만 사용 가능한 방법
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        # Windows에서만 chmod 사용 (POSIX 호환)
                        if hasattr(file_path, 'chmod'):
                            file_path.chmod(0o777)
                    except (OSError, AttributeError):
                        # chmod 실패 시 무시 (크로스 플랫폼 안전성)
                        pass
                
                for dir_name in dirs:
                    dir_file_path = Path(root) / dir_name
                    try:
                        if hasattr(dir_file_path, 'chmod'):
                            dir_file_path.chmod(0o777)
                    except (OSError, AttributeError):
                        pass
            
            shutil.rmtree(dir_path)
            return
        except PermissionError:
            pass
        
        # 2차 시도: 잠시 대기 후 재시도
        time.sleep(1)
        try:
            shutil.rmtree(dir_path)
            return
        except PermissionError:
            pass
        
        # 3차 시도: Windows 전용 명령어 (subprocess)
        try:
            # Windows에서만 실행되는 코드
            if self.platform_name == 'windows':
                subprocess.run(
                    ['cmd', '/c', f'rmdir /s /q "{dir_path}"'],
                    check=True,
                    capture_output=True,
                    timeout=30  # 타임아웃 추가
                )
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 4차 시도: PowerShell 명령어 사용
        try:
            if self.platform_name == 'windows':
                subprocess.run(
                    ['powershell', '-Command', f'Remove-Item -Path "{dir_path}" -Recurse -Force'],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 5차 시도: robocopy를 사용한 삭제 (Windows 전용)
        try:
            if self.platform_name == 'windows':
                # robocopy로 빈 디렉토리로 덮어쓰기 후 삭제
                temp_dir = dir_path.parent / f"temp_delete_{dir_path.name}"
                temp_dir.mkdir(exist_ok=True)
                
                subprocess.run(
                    ['robocopy', str(temp_dir), str(dir_path), '/MIR'],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                
                # 임시 디렉토리 삭제
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
                # 이제 빈 디렉토리 삭제 시도
                shutil.rmtree(dir_path)
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 모든 시도 실패
        raise PermissionError(f"Windows에서 디렉토리 삭제 실패: {dir_path}")
    
    def check_dependencies(self) -> None:
        """빌드 의존성 확인"""
        print("빌드 의존성 확인 중...")
        
        # 패키지명과 실제 import 모듈명 매핑
        package_mapping = {
            'pyinstaller': 'PyInstaller'
        }
        
        for package, import_name in package_mapping.items():
            try:
                # 실제 import 모듈명으로 확인
                __import__(import_name)
                print(f"   {package} 설치됨")
            except ImportError:
                # import 실패 시 subprocess로 재확인
                try:
                    result = subprocess.run(
                        [sys.executable, '-c', f'import {import_name}'],
                        capture_output=True,
                        check=True
                    )
                    print(f"   {package} 설치됨 (subprocess 확인)")
                except subprocess.CalledProcessError:
                    raise BuildError(
                        f"필수 패키지 {package}가 설치되지 않았습니다. "
                        f"'pip install {package}'로 설치하세요."
                    )
    
    def _prepare_build_files(self) -> Dict[str, Any]:
        """빌드에 필요한 파일들 확인 및 경로 준비"""
        print("빌드 파일 준비 중...")
        
        build_info = {
            'main_script': self.src_dir / "ts_cli" / "main.py",
            'datas': [],
            'version_file': None,
            'icon_file': None
        }
        
        # 필수 파일 확인
        if not build_info['main_script'].exists():
            raise BuildError(f"메인 스크립트를 찾을 수 없습니다: {build_info['main_script']}")
        
        # 선택적 파일들 확인
        config_file = self.project_root / "config" / "config.ini"
        if config_file.exists():
            build_info['datas'].append((str(config_file), "config"))
            print(f"   설정 파일 포함: {config_file}")
        else:
            print(f"   설정 파일 없음 (선택사항): {config_file}")
        
        # Windows 버전 정보 파일
        if self.platform_name == 'windows':
            version_file = self.scripts_dir / "version_info.txt"
            if version_file.exists():
                build_info['version_file'] = str(version_file)
                print(f"   버전 정보 파일: {version_file}")
        
        # 아이콘 파일
        icon_file = self.scripts_dir / "icon.ico"
        if icon_file.exists():
            build_info['icon_file'] = str(icon_file)
            print(f"   아이콘 파일: {icon_file}")
        
        return build_info
    
    def create_spec_file(self) -> Path:
        """PyInstaller spec 파일 생성"""
        print(" PyInstaller spec 파일 생성 중...")
        
        # 빌드 파일 준비
        build_info = self._prepare_build_files()
        
        # datas 배열 구성
        datas_str = "[\n"
        for data_item in build_info['datas']:
            datas_str += f"        {repr(data_item)},\n"
        datas_str += "    ]"
        
        # version과 icon 경로 처리
        version_str = f'r"{build_info["version_file"]}"' if build_info['version_file'] else 'None'
        icon_str = f'r"{build_info["icon_file"]}"' if build_info['icon_file'] else 'None'
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 프로젝트 경로 설정
project_root = Path(r"{str(self.project_root)}")
src_dir = project_root / "src"

# 분석 설정
a = Analysis(
    [r"{str(build_info['main_script'])}"],
    pathex=[str(src_dir)],
    binaries=[],
    datas={datas_str},
    hiddenimports=[
        'ts_cli',
        'ts_cli.vcs',
        'ts_cli.utils',
        'click',
        'rich',
        'httpx',
        'tenacity',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'unittest',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ 설정
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 실행파일 설정
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ts-cli{"" if sys.platform != "win32" else ".exe"}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version={version_str},
    icon={icon_str},
)
'''
        
        spec_file = self.project_root / "ts-cli.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"   spec 파일 생성: {spec_file}")
        return spec_file
    
    def create_version_info(self) -> Optional[Path]:
        """Windows용 버전 정보 파일 생성"""
        if self.platform_name != 'windows':
            return None
        
        print("Windows 버전 정보 파일 생성 중...")
        
        version_parts = self.version.split('.')
        while len(version_parts) < 4:
            version_parts.append('0')
        
        version_info_content = f'''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({', '.join(version_parts)}),
    prodvers=({', '.join(version_parts)}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'TestscenarioMaker Team'),
          StringStruct(u'FileDescription', u'TestscenarioMaker CLI Tool'),
          StringStruct(u'FileVersion', u'{self.version}'),
          StringStruct(u'InternalName', u'ts-cli'),
          StringStruct(u'LegalCopyright', u'Copyright © 2023 TestscenarioMaker Team'),
          StringStruct(u'OriginalFilename', u'ts-cli.exe'),
          StringStruct(u'ProductName', u'TestscenarioMaker CLI'),
          StringStruct(u'ProductVersion', u'{self.version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
        
        version_file = self.scripts_dir / "version_info.txt"
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(version_info_content)
        
        print(f"   버전 정보 파일 생성: {version_file}")
        return version_file
    
    def build_executable(self, spec_file: Path) -> Path:
        """실행파일 빌드"""
        print(" 실행파일 빌드 중...")
        
        # PyInstaller 실행
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            str(spec_file)
        ]
        
        print(f"   명령어: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            
            print("   PyInstaller 실행 완료")
            
        except subprocess.CalledProcessError as e:
            print(f"   PyInstaller 실행 실패:")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            raise BuildError(f"PyInstaller 빌드 실패: {e}")
        
        # 생성된 실행파일 확인
        exe_name = 'ts-cli' + ('.exe' if self.platform_name == 'windows' else '')
        exe_path = self.dist_dir / exe_name
        
        if not exe_path.exists():
            raise BuildError(f"실행파일이 생성되지 않았습니다: {exe_path}")
        
        print(f"   실행파일 생성: {exe_path}")
        return exe_path
    
    def test_executable(self, exe_path: Path) -> None:
        """생성된 실행파일 테스트"""
        print(" 실행파일 테스트 중...")
        
        test_commands = [
            ['--version'],
            ['--help'],
        ]
        
        for cmd_args in test_commands:
            try:
                result = subprocess.run(
                    [str(exe_path)] + cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"   {' '.join(cmd_args)} 테스트 통과")
                else:
                    print(f"   {' '.join(cmd_args)} 테스트 실패 (코드: {result.returncode})")
                    
            except subprocess.TimeoutExpired:
                print(f"   {' '.join(cmd_args)} 테스트 타임아웃")
            except Exception as e:
                print(f"   {' '.join(cmd_args)} 테스트 오류: {e}")
    
    def create_build_info(self, exe_path: Path) -> None:
        """빌드 정보 파일 생성"""
        print(" 빌드 정보 파일 생성 중...")
        
        import datetime
        
        build_info = {
            'version': self.version,
            'platform': self.platform_name,
            'architecture': self.arch,
            'build_time': datetime.datetime.now().isoformat(),
            'executable_path': str(exe_path.relative_to(self.project_root)),
            'executable_size': exe_path.stat().st_size,
            'python_version': sys.version,
        }
        
        info_file = self.dist_dir / 'build_info.json'
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2, ensure_ascii=False)
        
        print(f"   빌드 정보: {info_file}")
        
        # 빌드 정보 출력
        print("빌드 완료 정보:")
        print(f"   버전: {build_info['version']}")
        print(f"   플랫폼: {build_info['platform']} ({build_info['architecture']})")
        print(f"   실행파일: {build_info['executable_path']}")
        print(f"   크기: {build_info['executable_size']:,} bytes")
    
    def build(self, clean: bool = True, test: bool = True) -> Path:
        """전체 빌드 프로세스"""
        print("TestscenarioMaker CLI 빌드 시작")
        print("=" * 50)
        
        try:
            # 1. 정리
            if clean:
                self.clean_build_dirs()
            
            # 2. 의존성 확인
            self.check_dependencies()
            
            # 3. 버전 정보 파일 생성 (Windows만)
            self.create_version_info()
            
            # 4. spec 파일 생성
            spec_file = self.create_spec_file()
            
            # 5. 실행파일 빌드
            exe_path = self.build_executable(spec_file)
            
            # 6. 테스트
            if test:
                self.test_executable(exe_path)
            
            # 7. 빌드 정보 생성
            self.create_build_info(exe_path)
            
            print("=" * 50)
            print("빌드 성공!")
            print(f"   실행파일: {exe_path}")
            
            return exe_path
            
        except Exception as e:
            print("=" * 50)
            print(f"빌드 실패: {e}")
            raise


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='TestscenarioMaker CLI Build Script')
    parser.add_argument(
        '--no-clean',
        action='store_true',
        help='Do not clean build directories'
    )
    parser.add_argument(
        '--no-test',
        action='store_true',
        help='Skip testing the executable'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path(__file__).parent.parent,
        help='Project root directory'
    )
    
    args = parser.parse_args()
    
    try:
        builder = CLIBuilder(args.project_root)
        exe_path = builder.build(
            clean=not args.no_clean,
            test=not args.no_test
        )
        
        print(f"\n To use the built executable:")
        print(f"   {exe_path} --help")
        
        return 0
        
    except BuildError as e:
        print(f"\nBuild error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nBuild was interrupted.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())