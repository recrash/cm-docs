#!/usr/bin/env python3
"""
TestscenarioMaker CLI Build Script

Generates OS-specific executables using PyInstaller.
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
import configparser
import tempfile


class BuildError(Exception):
    """Build-related errors"""
    pass


class CLIBuilder:
    """CLI Build Manager"""
    
    def __init__(self, project_root: Path, base_url: Optional[str] = None):
        """
        Initialize build manager
        
        Args:
            project_root: Project root directory
        """
        self.project_root = project_root.resolve()
        self.src_dir = self.project_root / "src"
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.scripts_dir = self.project_root / "scripts"
        self.base_url = base_url
        
        self.platform_name = platform.system().lower()
        self.arch = platform.machine().lower()
        
        # Load version info
        self.version = self._get_version()
        
        print(f"Build environment initialized")
        print(f"   Base URL: {self.base_url}")
        print(f"   Platform: {self.platform_name} ({self.arch})")
        print(f"   Version: {self.version}")
        print(f"   Project root: {self.project_root}")
    
    def _get_version(self) -> str:
        """Get version information"""
        try:
            # Extract version info from __init__.py
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
        """Clean build directories"""
        print("Cleaning build directories...")
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                try:
                    # Try default deletion (works on all platforms)
                    shutil.rmtree(dir_path)
                    print(f"   {dir_path.name} cleaned")
                except PermissionError as e:
                    # Additional processing for Windows only
                    if self.platform_name == 'windows':
                        print(f"   Windows permission error: {dir_path.name}")
                        print(f"   Attempting Windows-specific cleanup...")
                        
                        try:
                            self._safe_remove_windows_dir(dir_path)
                            print(f"   {dir_path.name} Windows cleanup complete")
                        except Exception as win_error:
                            print(f"   Windows cleanup also failed: {win_error}")
                            print(f"   Resolution:")
                            print(f"      1. Run PowerShell as Administrator")
                            print(f"      2. Manual deletion: Remove-Item -Path '{dir_path}' -Recurse -Force")
                            print(f"      3. Or retry build with --no-clean option")
                            raise BuildError(f"Windows directory deletion failed: {e}")
                    else:
                        # Propagate original error on macOS/Linux
                        raise BuildError(f"Directory deletion permission error: {e}")
                except Exception as e:
                    # Handle other errors the same way on all platforms
                    print(f"   {dir_path.name} cleanup failed: {e}")
                    raise BuildError(f"Directory cleanup failed: {e}")
            
            # Recreate directory (same on all platforms)
            dir_path.mkdir(parents=True, exist_ok=True)

    def _safe_remove_windows_dir(self, dir_path: Path) -> None:
        """Safe directory deletion on Windows (maintaining cross-platform compatibility)"""
        import time
        
        # 1st attempt: Delete after changing file attributes
        try:
            # Method only available on Windows
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        # Use chmod on Windows only (POSIX compatible)
                        if hasattr(file_path, 'chmod'):
                            file_path.chmod(0o777)
                    except (OSError, AttributeError):
                        # Ignore chmod failure (cross-platform safety)
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
        
        # 2nd attempt: Retry after brief wait
        time.sleep(1)
        try:
            shutil.rmtree(dir_path)
            return
        except PermissionError:
            pass
        
        # 3rd attempt: Windows-specific command (subprocess)
        try:
            # Code that only runs on Windows
            if self.platform_name == 'windows':
                subprocess.run(
                    ['cmd', '/c', f'rmdir /s /q "{dir_path}"'],
                    check=True,
                    capture_output=True,
                    timeout=30  # Add timeout
                )
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 4th attempt: Use PowerShell command
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
        
        # 5th attempt: Delete using robocopy (Windows only)
        try:
            if self.platform_name == 'windows':
                # Overwrite with empty directory using robocopy then delete
                temp_dir = dir_path.parent / f"temp_delete_{dir_path.name}"
                temp_dir.mkdir(exist_ok=True)
                
                subprocess.run(
                    ['robocopy', str(temp_dir), str(dir_path), '/MIR'],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                
                # Delete temporary directory
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
                # Now try to delete empty directory
                shutil.rmtree(dir_path)
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # All attempts failed
        raise PermissionError(f"Failed to delete directory on Windows: {dir_path}")
    
    def check_dependencies(self) -> None:
        """Check build dependencies"""
        print("Checking build dependencies...")
        
        # Package name to actual import module name mapping
        package_mapping = {
            'pyinstaller': 'PyInstaller'
        }
        
        for package, import_name in package_mapping.items():
            try:
                # Check with actual import module name
                __import__(import_name)
                print(f"   {package} installed")
            except ImportError:
                # Re-check with subprocess on import failure
                try:
                    result = subprocess.run(
                        [sys.executable, '-c', f'import {import_name}'],
                        capture_output=True,
                        check=True
                    )
                    print(f"   {package} installed (subprocess verification)")
                except subprocess.CalledProcessError:
                    raise BuildError(
                        f"Required package {package} is not installed. "
                        f"Please install with 'pip install {package}'."
                    )
    
    def _prepare_build_files(self) -> Dict[str, Any]:
        """Check and prepare paths for build files"""
        print("Preparing build files...")
        
        build_info = {
            'main_script': self.src_dir / "ts_cli" / "main.py",
            'datas': [],
            'version_file': None,
            'icon_file': None
        }
        
        # Check required files
        if not build_info['main_script'].exists():
            raise BuildError(f"Main script not found: {build_info['main_script']}")

        # 동적 config.ini 생성 로직 추가!
        dynamic_config_file_path = self._create_dynamic_config()
        build_info['datas'].append((str(dynamic_config_file_path), "config"))
        print(f"   Including dynamic config file: {dynamic_config_file_path}")
        
        # Check optional files
        # config_file = self.project_root / "config" / "config.ini"
        # if config_file.exists():
        #     build_info['datas'].append((str(config_file), "config"))
        #     print(f"   Including config file: {config_file}")
        # else:
        #     print(f"   Config file not found (optional): {config_file}")
        
        # Windows version info file
        if self.platform_name == 'windows':
            version_file = self.scripts_dir / "version_info.txt"
            if version_file.exists():
                build_info['version_file'] = str(version_file)
                print(f"   Version info file: {version_file}")
        
        # Icon file
        icon_file = self.scripts_dir / "icon.ico"
        if icon_file.exists():
            build_info['icon_file'] = str(icon_file)
            print(f"   Icon file: {icon_file}")
        
        return build_info
    
    def create_spec_file(self) -> Path:
        """Create PyInstaller spec file"""
        print("Creating PyInstaller spec file...")
        
        # Prepare build files
        build_info = self._prepare_build_files()
        
        # Configure datas array
        datas_str = "[\n"
        for data_item in build_info['datas']:
            datas_str += f"        {repr(data_item)},\n"
        datas_str += "    ]"
        
        # Process version and icon paths
        version_str = f'r"{build_info["version_file"]}"' if build_info['version_file'] else 'None'
        icon_str = f'r"{build_info["icon_file"]}"' if build_info['icon_file'] else 'None'
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Set project paths
project_root = Path(r"{str(self.project_root)}")
src_dir = project_root / "src"

# Analysis settings
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

# PYZ settings
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable settings
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
        
        print(f"   Spec file created: {spec_file}")
        return spec_file
    
    def create_version_info(self) -> Optional[Path]:
        """Create Windows version info file"""
        if self.platform_name != 'windows':
            return None
        
        print("Creating Windows version info file...")
        
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
        
        print(f"   Version info file created: {version_file}")
        return version_file
    
    def build_executable(self, spec_file: Path) -> Path:
        """Build executable"""
        print("Building executable...")
        
        # Run PyInstaller
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            str(spec_file)
        ]
        
        print(f"   Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            
            print("   PyInstaller execution complete")
            
        except subprocess.CalledProcessError as e:
            print(f"   PyInstaller execution failed:")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            raise BuildError(f"PyInstaller build failed: {e}")
        
        # Check generated executable
        exe_name = 'ts-cli' + ('.exe' if self.platform_name == 'windows' else '')
        exe_path = self.dist_dir / exe_name
        
        if not exe_path.exists():
            raise BuildError(f"Executable was not created: {exe_path}")
        
        print(f"   Executable created: {exe_path}")
        return exe_path
    
    def test_executable(self, exe_path: Path) -> None:
        """Test generated executable"""
        print("Testing executable...")
        
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
                    print(f"   {' '.join(cmd_args)} test passed")
                else:
                    print(f"   {' '.join(cmd_args)} test failed (code: {result.returncode})")
                    
            except subprocess.TimeoutExpired:
                print(f"   {' '.join(cmd_args)} test timeout")
            except Exception as e:
                print(f"   {' '.join(cmd_args)} test error: {e}")
    
    def create_build_info(self, exe_path: Path) -> None:
        """Create build info file"""
        print("Creating build info file...")
        
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
        
        print(f"   Build info: {info_file}")
        
        # Output build info
        print("Build complete info:")
        print(f"   Version: {build_info['version']}")
        print(f"   Platform: {build_info['platform']} ({build_info['architecture']})")
        print(f"   Executable: {build_info['executable_path']}")
        print(f"   Size: {build_info['executable_size']:,} bytes")
    
    # 동적 config.ini 파일을 생성하는 새 메서드 추가
    def _create_dynamic_config(self) -> str:
        """
        Creates a temporary config.ini file with the specified base_url.
        Returns the path to the temporary file.
        """
        original_config_path = self.project_root / "config" / "config.ini"
        if not original_config_path.exists():
            raise BuildError(f"Original config file not found: {original_config_path}")

        config = configparser.ConfigParser()
        config.read(original_config_path, encoding='utf-8')

        # base_url이 주입된 경우, config 파일 내용 수정
        if self.base_url:
            if not config.has_section('api'):
                config.add_section('api')
            config.set('api', 'base_url', self.base_url)
            print(f"   Updated [api] base_url to: {self.base_url}")

        # 임시 파일에 수정된 내용을 쓴다
        # tempfile을 사용하면 스크립트 종료 시 자동으로 정리됨 (더 안전)
        fd, temp_config_path = tempfile.mkstemp(suffix=".ini", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as temp_file:
            config.write(temp_file)
            
        print(f"   Temporary config file created at: {temp_config_path}")
        return temp_config_path
    
    def build(self, clean: bool = True, test: bool = True) -> Path:
        """Full build process"""
        print("TestscenarioMaker CLI build started")
        print("=" * 50)
        
        try:
            # 1. Clean
            if clean:
                self.clean_build_dirs()
            
            # 2. Check dependencies
            self.check_dependencies()
            
            # 3. Create version info file (Windows only)
            self.create_version_info()
            
            # 4. Create spec file
            spec_file = self.create_spec_file()
            
            # 5. Build executable
            exe_path = self.build_executable(spec_file)
            
            # 6. Test
            if test:
                self.test_executable(exe_path)
            
            # 7. Create build info
            self.create_build_info(exe_path)
            
            print("=" * 50)
            print("Build successful!")
            print(f"   Executable: {exe_path}")
            
            return exe_path
            
        except Exception as e:
            print("=" * 50)
            print(f"Build failed: {e}")
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
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://cm-docs.cloud',
        help='API Base URL to bake into the executable'
    )
    
    args = parser.parse_args()
    
    try:
        builder = CLIBuilder(args.project_root, base_url=args.base_url)
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