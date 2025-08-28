#!/usr/bin/env python3
"""
TestscenarioMaker CLI 메인 모듈

저장소 분석을 위한 명령행 인터페이스를 제공합니다.
"""

import sys
import os
# ▼▼▼ 이 코드를 추가해줘! ▼▼▼
# PyInstaller로 빌드된 실행 파일이 어디서 실행되든
# 자기 자신의 위치를 기준으로 모듈을 찾을 수 있게 해주는 코드
if getattr(sys, 'frozen', False):
    # 실행 파일(.exe)로 실행된 경우
    application_path = os.path.dirname(sys.executable)
    sys.path.append(application_path)
    # 만약 .exe가 src/ts_cli 안에 있다면 상위 폴더도 추가
    sys.path.append(os.path.join(application_path, '..'))
    sys.path.append(os.path.join(application_path, '..', '..'))
else:
    # 일반 파이썬 스크립트로 실행된 경우
    application_path = os.path.dirname(os.path.abspath(__file__))
import os
import platform
import urllib.parse
from pathlib import Path
from typing import Optional

import click
import requests
from rich.console import Console
from rich.traceback import install

# PyInstaller 호환성을 위한 import 처리
try:
    from . import __version__
    from .cli_handler import CLIHandler
    from .utils.logger import setup_logger, set_log_level
    from .utils.config_loader import load_config
except ImportError:
    # PyInstaller 환경에서는 절대 import 사용
    import ts_cli
    from ts_cli import __version__
    from ts_cli.cli_handler import CLIHandler
    from ts_cli.utils.logger import setup_logger, set_log_level
    from ts_cli.utils.config_loader import load_config

# Rich traceback 설치 (더 예쁜 에러 메시지)
install(show_locals=True)

# 콘솔 인스턴스
console = Console()


def load_server_config() -> str:
    """
    서버 설정을 로드합니다.
    
    1순위: config.ini 파일
    2순위: TSM_SERVER_URL 환경 변수
    
    Returns:
        서버 URL
        
    Raises:
        SystemExit: 설정을 찾을 수 없는 경우
    """
    # 1순위: config.ini 파일에서 로드 시도
    try:
        try:
            from .utils.config_loader import load_config
        except ImportError:
            from ts_cli.utils.config_loader import load_config
            
        config_loader = load_config()
        server_url = config_loader.get("api", "base_url")
        if server_url and server_url.strip():  # 빈 값 체크 추가
            console.print(f"[green]Server URL loaded from config: {server_url}[/green]")
            return server_url
    except Exception as e:
        console.print(f"[yellow]Config file load failed: {e}[/yellow]")
    
    # 2순위: TSM_SERVER_URL 환경 변수에서 로드 시도
    env_server_url = os.environ.get("TSM_SERVER_URL")
    if env_server_url and env_server_url.strip():  # 빈 값 체크 추가
        console.print(f"[green]Server URL loaded from environment: {env_server_url}[/green]")
        return env_server_url
    
    # 모두 실패한 경우
    console.print("[red]Server URL not found.[/red]")
    console.print("[red]Please configure one of the following:[/red]")
    console.print("[red]  1. Set base_url in [api] section of config.ini[/red]")
    console.print("[red]  2. Set TSM_SERVER_URL environment variable[/red]")
    sys.exit(1)


def make_api_request(server_url: str, repo_path: Path, client_id: Optional[str] = None) -> bool:
    """
    동기 방식으로 API 요청을 수행합니다.
    
    Args:
        server_url: API 서버 URL
        repo_path: 저장소 경로
        client_id: 클라이언트 ID (옵션)
        
    Returns:
        요청 성공 여부
    """
    try:
        # VCS 분석기를 사용해 변경사항 수집
        try:
            from .vcs import get_analyzer
        except ImportError:
            from ts_cli.vcs import get_analyzer
            
        analyzer = get_analyzer(repo_path)
        if not analyzer or not analyzer.validate_repository():
            console.print(f"[red]유효하지 않은 저장소입니다: {repo_path}[/red]")
            return False
            
        changes_data = analyzer.get_changes("origin/develop", "HEAD")
        if not changes_data:
            console.print("[yellow]변경사항이 없습니다.[/yellow]")
            return True
            
        # v2 API 요청 데이터 준비
        if not client_id:
            import uuid
            client_id = f"ts_cli_{uuid.uuid4().hex[:8]}"
            
        # Git 저장소 유효성 검증 수행 (로컬에서만)
        is_valid_git_repo = analyzer.validate_repository()
        
        request_data = {
            "client_id": client_id,
            "repo_path": str(repo_path.resolve()),
            "use_performance_mode": True,
            "is_valid_git_repo": is_valid_git_repo
        }
        
        # v2 API 엔드포인트 URL 구성
        api_url = f"{server_url.rstrip('/')}/api/v2/scenario/generate"
        
        console.print("[cyan]Sending API request...[/cyan]")
        
        # requests를 사용한 동기 API 호출
        with requests.Session() as session:
            session.headers.update({
                "Content-Type": "application/json",
                "User-Agent": f"TestscenarioMaker-CLI/{__version__}"
            })
            
            response = session.post(
                api_url,
                json=request_data,
                timeout=(10, 30)  # (연결 타임아웃, 읽기 타임아웃)
            )
            
            # HTTP 상태 코드 확인
            response.raise_for_status()
            
            # v2 API 응답 처리 (client_id, websocket_url)
            result_data = response.json()
            client_id_response = result_data.get("client_id")
            websocket_url = result_data.get("websocket_url")
            
            console.print(f"[green]v2 API 요청 완료. Client ID: {client_id_response}[/green]")
            console.print(f"[cyan]시나리오 생성이 백그라운드에서 진행됩니다.[/cyan]")
            console.print(f"[yellow]웹 UI에서 진행 상황을 확인하세요: {server_url}[/yellow]")
                
            return True
            
    except requests.exceptions.ConnectionError:
        console.print("[red]서버에 연결할 수 없습니다[/red]")
        console.print("[red]네트워크 연결을 확인하거나 서버 URL이 올바른지 확인해주세요.[/red]")
        return False
        
    except requests.exceptions.Timeout:
        console.print("[red]요청 시간이 초과되었습니다.[/red]")
        console.print("[red]서버가 응답하지 않습니다. 잠시 후 다시 시도해주세요.[/red]")
        return False
        
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "Unknown"
        console.print(f"[red]HTTP 오류가 발생했습니다: {status_code}[/red]")
        
        if status_code == 400:
            console.print("[red]요청 데이터가 올바르지 않습니다.[/red]")
        elif status_code == 401:
            console.print("[red]인증이 필요합니다.[/red]")
        elif status_code == 403:
            console.print("[red]접근 권한이 없습니다.[/red]")
        elif status_code == 404:
            console.print("[red]API 엔드포인트를 찾을 수 없습니다.[/red]")
        elif status_code >= 500:
            console.print("[red]서버 내부 오류가 발생했습니다.[/red]")
            
        return False
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]요청 중 오류가 발생했습니다: {e}[/red]")
        return False
        
    except Exception as e:
        console.print(f"[red]예상치 못한 오류가 발생했습니다: {e}[/red]")
        return False


def collect_debug_info(raw_url: str) -> dict:
    """URL 프로토콜 처리를 위한 종합 디버깅 정보 수집"""
    import tempfile
    import subprocess
    import json
    import datetime
    
    debug_info = {
        'timestamp': datetime.datetime.now().isoformat(),
        'url': raw_url,
        'debug_file': Path(tempfile.gettempdir()) / "testscenariomaker_debug.log"
    }
    
    # 1. 기본 시스템 정보
    debug_info['system'] = {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.architecture(),
        'python_version': platform.python_version(),
        'executable_path': sys.executable,
        'working_directory': os.getcwd(),
        'cli_executable': str(Path(sys.executable).parent / "ts-cli.exe") if platform.system() == "Windows" else "ts-cli"
    }
    
    # 2. 환경 변수
    debug_info['environment'] = {
        'PATH': os.environ.get('PATH', 'NOT_SET'),
        'HOME': os.environ.get('HOME', 'NOT_SET'),
        'USER': os.environ.get('USER', 'NOT_SET'),
        'USERNAME': os.environ.get('USERNAME', 'NOT_SET'),
        'USERPROFILE': os.environ.get('USERPROFILE', 'NOT_SET'),
        'TEMP': os.environ.get('TEMP', 'NOT_SET'),
        'TMP': os.environ.get('TMP', 'NOT_SET')
    }
    
    # 3. 프로세스 정보
    try:
        import psutil
        current_process = psutil.Process()
        debug_info['process'] = {
            'pid': current_process.pid,
            'ppid': current_process.ppid(),
            'name': current_process.name(),
            'exe': current_process.exe(),
            'cmdline': current_process.cmdline(),
            'cwd': current_process.cwd(),
            'username': current_process.username()
        }
        
        # 부모 프로세스 정보 (브라우저 정보 획득)
        try:
            parent_process = current_process.parent()
            if parent_process:
                debug_info['parent_process'] = {
                    'pid': parent_process.pid,
                    'name': parent_process.name(),
                    'exe': parent_process.exe(),
                    'cmdline': parent_process.cmdline()
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            debug_info['parent_process'] = {'error': 'Cannot access parent process'}
            
    except ImportError:
        debug_info['process'] = {'error': 'psutil not available, using basic process info'}
        debug_info['process'].update({
            'pid': os.getpid(),
            'cmdline': sys.argv
        })
    except Exception as e:
        debug_info['process'] = {'error': str(e)}
    
    # 4. Windows 레지스트리 정보 (Windows만)
    if platform.system() == "Windows":
        debug_info['registry'] = check_windows_registry()
    
    # 5. CLI 설치 상태 확인
    debug_info['cli_status'] = check_cli_installation()
    
    return debug_info


def check_windows_registry() -> dict:
    """Windows 레지스트리에서 URL 프로토콜 등록 상태 확인"""
    try:
        import winreg
        registry_info = {}
        
        # testscenariomaker 프로토콜 키 확인
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "testscenariomaker") as key:
                registry_info['protocol_exists'] = True
                registry_info['protocol_description'] = winreg.QueryValueEx(key, "")[0]
                
                # URL Protocol 값 확인
                try:
                    registry_info['url_protocol'] = winreg.QueryValueEx(key, "URL Protocol")[0]
                except FileNotFoundError:
                    registry_info['url_protocol'] = 'NOT_SET'
                    
        except FileNotFoundError:
            registry_info['protocol_exists'] = False
            
        # 명령어 경로 확인
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"testscenariomaker\shell\open\command") as key:
                command_path = winreg.QueryValueEx(key, "")[0]
                registry_info['command_path'] = command_path
                
                # 명령어 경로 추출 (따옴표 안의 실행파일 경로만 추출)
                import shlex
                try:
                    # shlex로 명령줄 파싱 (따옴표 처리 포함)
                    parsed_command = shlex.split(command_path)
                    executable_path = parsed_command[0] if parsed_command else ""
                    registry_info['parsed_executable'] = executable_path
                    registry_info['command_exists'] = Path(executable_path).exists()
                except Exception as parse_error:
                    # shlex 파싱 실패시 기본 방식으로 파싱
                    executable_path = command_path.strip('"').split()[0] if command_path else ""
                    registry_info['parsed_executable'] = executable_path
                    registry_info['command_exists'] = Path(executable_path).exists()
                    registry_info['parse_error'] = str(parse_error)
        except FileNotFoundError:
            registry_info['command_path'] = 'NOT_SET'
            registry_info['command_exists'] = False
            
        return registry_info
        
    except ImportError:
        return {'error': 'winreg module not available'}
    except Exception as e:
        return {'error': str(e)}


def check_cli_installation() -> dict:
    """CLI 설치 상태 확인"""
    cli_info = {}
    
    # PATH에서 ts-cli 확인
    import shutil
    cli_path = shutil.which('ts-cli')
    cli_info['cli_in_path'] = cli_path is not None
    cli_info['cli_path'] = cli_path
    
    # 일반적인 설치 경로 확인
    if platform.system() == "Windows":
        common_paths = [
            Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / "TestscenarioMaker CLI" / "ts-cli.exe",
            Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / "TestscenarioMaker CLI" / "ts-cli.exe",
            Path.cwd() / "dist" / "ts-cli.exe"
        ]
        
        for path in common_paths:
            if path.exists():
                cli_info['found_installations'] = cli_info.get('found_installations', []) + [str(path)]
                
    return cli_info


def log_debug_info(debug_info: dict) -> None:
    """디버깅 정보를 파일에 로깅"""
    import json
    
    try:
        with open(debug_info['debug_file'], "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"URL Protocol Debug Session: {debug_info['timestamp']}\n")
            f.write(f"{'='*80}\n")
            
            # JSON 형태로 구조화된 정보 저장
            f.write(json.dumps(debug_info, indent=2, ensure_ascii=False, default=str))
            f.write(f"\n{'='*80}\n\n")
            
        console.print("[green]Debug information collected[/green]")
        
    except Exception as e:
        console.print(f"[red]Debug logging failed: {e}[/red]")


def parse_url_parameters(url: str) -> tuple[Path, Optional[str]]:
    """
    URL에서 repoPath와 clientId를 추출합니다.
    
    Args:
        url: testscenariomaker:// 형식의 URL
        
    Returns:
        tuple of (repository_path, client_id)
        
    Raises:
        ValueError: URL 파싱 실패 시
    """
    try:
        # URL 디코딩 및 파싱
        decoded_url = urllib.parse.unquote(url)
        parsed = urllib.parse.urlparse(decoded_url)
        
        # URL 스키마 검증
        if parsed.scheme != "testscenariomaker":
            raise ValueError(f"지원하지 않는 URL 스키마: {parsed.scheme}")
        
        # 쿼리 파라미터 파싱
        query_params = urllib.parse.parse_qs(parsed.query)
        client_id = query_params.get('clientId', [None])[0]
        
        # 경로 추출: 쿼리 파라미터에서 repoPath를 우선 확인
        repo_path_param = query_params.get('repoPath', [None])[0]
        
        if repo_path_param:
            # 쿼리 파라미터에서 경로 추출 (URL 디코딩 적용)
            path_str = urllib.parse.unquote(repo_path_param)
        else:
            # 기존 방식: URL path에서 경로 추출
            if platform.system() == "Windows":
                # Windows: netloc과 path를 합쳐서 전체 경로 구성
                # 예: testscenariomaker://C:/path/to/repo → C:/path/to/repo
                path_str = parsed.netloc + parsed.path
                # Windows 경로 정규화
                path_str = path_str.rstrip('/"').replace('/', '\\')
            else:
                # macOS/Linux: path만 사용 (절대경로 유지)
                # 예: testscenariomaker:///Users/user/repo → /Users/user/repo
                path_str = parsed.path
                # Unix 경로 정규화 (앞쪽 슬래시는 절대경로 표시이므로 유지)
                path_str = path_str.rstrip('/"')
        
        # pathlib.Path 객체로 변환하여 크로스 플랫폼 호환성 보장
        repository_path = Path(path_str)
        
        return repository_path, client_id
        
    except Exception as e:
        raise ValueError(f"URL 파싱 실패: {e}") from e


def validate_repository_path(repo_path: Path) -> None:
    """
    저장소 경로의 유효성을 검증합니다.
    
    Args:
        repo_path: 검증할 저장소 경로
        
    Raises:
        SystemExit: 경로가 유효하지 않은 경우
    """
    if not repo_path.exists():
        console.print(f"[red]경로를 찾을 수 없습니다: {repo_path}[/red]")
        sys.exit(1)
        
    if not repo_path.is_dir():
        console.print(f"[red]디렉토리가 아닙니다: {repo_path}[/red]")
        sys.exit(1)
        
    # Git 저장소인지 확인
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        console.print(f"[red]Git 저장소가 아닙니다: {repo_path}[/red]")
        console.print("[red].git 디렉토리를 찾을 수 없습니다.[/red]")
        sys.exit(1)


def handle_url_protocol() -> None:
    """
    testscenariomaker:// URL 프로토콜 처리
    
    웹 브라우저에서 전달된 URL을 파싱하여 저장소 경로를 추출하고
    동기 방식으로 API 요청을 수행합니다.
    """
    try:
        # URL 재조합 (sys.argv[1:]을 다시 합쳐서 완전한 URL 복원)
        raw_url = " ".join(sys.argv[1:])
        
        if not raw_url.startswith('testscenariomaker://'):
            console.print("[red]Invalid URL format.[/red]")
            sys.exit(1)
        
        console.print(f"[cyan]Processing URL protocol: {raw_url}[/cyan]")
        
        # 종합 디버깅 정보 수집
        debug_info = collect_debug_info(raw_url)
        log_debug_info(debug_info)
        console.print(f"[dim]Debug log: {debug_info['debug_file']}[/dim]")
        
        # URL에서 repoPath, clientId 추출
        try:
            repository_path, client_id = parse_url_parameters(raw_url)
            console.print(f"[green]Target repository: {repository_path.resolve()}[/green]")
            if client_id:
                console.print(f"[cyan]Client ID: {client_id}[/cyan]")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            sys.exit(1)
        
        # 경로 유효성 검증
        validate_repository_path(repository_path)
        
        # 서버 설정 로드
        server_url = load_server_config()
        
        # 동기 API 호출
        console.print(f"[bold blue]TestscenarioMaker CLI v{__version__}[/bold blue]")
        console.print(f"Repository analysis started: [green]{repository_path.resolve()}[/green]")
        
        success = make_api_request(server_url, repository_path, client_id)
        
        if success:
            console.print("[bold green]Repository analysis completed successfully.[/bold green]")
            sys.exit(0)
        else:
            console.print("[bold red]Error occurred during repository analysis.[/bold red]")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]사용자에 의해 중단되었습니다.[/yellow]")
        sys.exit(130)
        
    except Exception as e:
        console.print(f"[red]URL 처리 중 오류가 발생했습니다: {e}[/red]")
        console.print_exception(show_locals=True)
        sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="TestscenarioMaker CLI")
def click_main() -> None:
    """TestscenarioMaker CLI 도구 모음"""
    pass


def main() -> None:
    """
    메인 엔트리 포인트
    
    URL 프로토콜 처리를 먼저 확인하고, 해당하지 않으면 기존 Click CLI로 넘어갑니다.
    """
    # URL 프로토콜 처리를 위한 사전 검사 (Click 파서 실행 전)
    if len(sys.argv) > 1 and any(arg.startswith('testscenariomaker://') for arg in sys.argv[1:]):
        handle_url_protocol()
        return
    
    # 기존 Click CLI 실행
    click_main()


@click_main.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help="분석할 저장소 경로 (기본값: 현재 디렉토리)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="사용할 설정 파일 경로",
)
@click.option("--verbose", "-v", is_flag=True, help="상세 출력 모드 활성화")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="출력 형식 선택 (기본값: text)",
)
@click.option("--dry-run", is_flag=True, help="실제 API 호출 없이 분석만 수행")
@click.option(
    "--base-branch",
    "-b",
    default="origin/develop",
    help="기준 브랜치명 (기본값: origin/develop)",
)
@click.option(
    "--head-branch",
    "-h",
    default="HEAD",
    help="대상 브랜치명 (기본값: HEAD)",
)
def analyze(
    path: Path, 
    config: Optional[Path], 
    verbose: bool, 
    output: str, 
    dry_run: bool,
    base_branch: str,
    head_branch: str
) -> None:
    """
    TestscenarioMaker CLI - 로컬 저장소 분석 도구

    로컬 Git 저장소를 분석하여 TestscenarioMaker 서버로 전송하고
    분석 결과를 다운로드합니다.

    브랜치 간 비교 분석:
    - 기준 브랜치(base-branch)와 대상 브랜치(head-branch) 간의 차이점을 분석
    - 공통 조상부터 대상 브랜치까지의 모든 커밋 메시지와 코드 변경사항을 수집
    - 현재 작업 디렉토리의 변경사항(Working State)도 포함

    예시:
        ts-cli analyze --path /path/to/repo --verbose
        ts-cli analyze -p . -o json
        ts-cli analyze --config custom_config.ini --dry-run
        ts-cli analyze --base-branch main --head-branch feature/new-feature
    """
    try:
        # 설정 로드
        load_config(config)

        # 로거 설정
        log_level = "DEBUG" if verbose else "INFO"
        logger = setup_logger(level=log_level)

        if verbose:
            set_log_level("DEBUG")

        # 환영 메시지
        if not dry_run:
            console.print(
                f"[bold blue]TestscenarioMaker CLI v{__version__}[/bold blue]"
            )
            console.print(f"저장소 분석 시작: [green]{path.resolve()}[/green]")
            console.print(f"브랜치 비교: [cyan]{base_branch}[/cyan] → [cyan]{head_branch}[/cyan]")

        # CLI 핸들러 생성 및 실행
        handler = CLIHandler(verbose=verbose, output_format=output, dry_run=dry_run)

        success = handler.analyze_repository(path, base_branch, head_branch)

        if success:
            if not dry_run:
                console.print(
                    "[bold green]저장소 분석이 성공적으로 완료되었습니다.[/bold green]"
                )
            sys.exit(0)
        else:
            print(
                "[bold red]저장소 분석 중 오류가 발생했습니다.[/bold red]",
                file=sys.stderr,
            )
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]사용자에 의해 중단되었습니다.[/yellow]")
        sys.exit(130)

    except Exception as e:
        print(f"[red]예상치 못한 오류가 발생했습니다: {e}[/red]", file=sys.stderr)
        console.print_exception(show_locals=True)
        sys.exit(1)


@click_main.command()
@click.option("--config", "-c", type=click.Path(path_type=Path), help="설정 파일 경로")
def config_show(config: Optional[Path]) -> None:
    """현재 설정 정보를 표시합니다."""
    try:
        config_loader = load_config(config)
        all_config = config_loader.get_all_sections()

        console.print("현재 설정:")
        console.print(f"설정 파일: {config_loader.config_path}")
        console.print()

        for section_name, section_data in all_config.items():
            console.print(f"[{section_name}]")
            for key, value in section_data.items():
                console.print(f"  {key} = {value}")
            console.print()

    except Exception as e:
        print(f"[red]설정 정보 조회 실패: {e}[/red]", file=sys.stderr)
        sys.exit(1)


@click_main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def info(path: Path) -> None:
    """저장소 정보를 표시합니다 (분석 없이)."""
    try:
        # PyInstaller 호환성을 위한 import 처리
        try:
            from .vcs import get_analyzer
        except ImportError:
            from ts_cli.vcs import get_analyzer

        analyzer = get_analyzer(path)
        if not analyzer:
            print(
                f"[red]{path}는 지원되는 VCS 저장소가 아닙니다.[/red]", file=sys.stderr
            )
            sys.exit(1)

        if not analyzer.validate_repository():
            print(f"[red]{path}는 유효하지 않은 저장소입니다.[/red]", file=sys.stderr)
            sys.exit(1)

        repo_info = analyzer.get_repository_info()

        console.print("[bold blue]저장소 정보:[/bold blue]")
        console.print(f"경로: [green]{repo_info.get('path', 'N/A')}[/green]")
        console.print(f"VCS 타입: [yellow]{repo_info.get('vcs_type', 'N/A')}[/yellow]")

        if repo_info.get("current_branch"):
            console.print(f"현재 브랜치: [cyan]{repo_info['current_branch']}[/cyan]")

        if repo_info.get("remote_url"):
            console.print(f"원격 저장소: [blue]{repo_info['remote_url']}[/blue]")

        if repo_info.get("commit_count") is not None:
            console.print(f"총 커밋 수: [magenta]{repo_info['commit_count']}[/magenta]")

        # 상태 정보
        if repo_info.get("has_changes"):
            console.print("\n[bold yellow]변경사항 요약:[/bold yellow]")
            console.print(f"  Staged 파일: {repo_info.get('staged_files', 0)}")
            console.print(f"  Unstaged 파일: {repo_info.get('unstaged_files', 0)}")
            console.print(f"  Untracked 파일: {repo_info.get('untracked_files', 0)}")
        else:
            console.print("\n[green]작업 디렉토리가 깨끗합니다.[/green]")

    except Exception as e:
        print(f"[red]저장소 정보 조회 실패: {e}[/red]", file=sys.stderr)
        sys.exit(1)


@click_main.command()
def version() -> None:
    """버전 정보를 표시합니다."""
    console.print(f"TestscenarioMaker CLI v{__version__}")


# CLI 엔트리 포인트 별칭 (setup.py에서 사용)
cli = main

if __name__ == "__main__":
    main()
