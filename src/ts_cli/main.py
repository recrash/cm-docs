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
import platform
import urllib.parse
from pathlib import Path
from typing import Optional

import click
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


def handle_url_protocol() -> None:
    """
    testscenariomaker:// URL 프로토콜 처리
    
    웹 브라우저에서 전달된 URL을 파싱하여 저장소 경로를 추출하고
    기존 analyze 명령과 동일한 로직으로 분석을 수행합니다.
    """
    try:
        # URL 재조합 (sys.argv[1:]을 다시 합쳐서 완전한 URL 복원)
        raw_url = " ".join(sys.argv[1:])
        
        if not raw_url.startswith('testscenariomaker://'):
            print("[red]❌ 올바르지 않은 URL 형식입니다.[/red]", file=sys.stderr)
            sys.exit(1)
        
        console.print(f"[cyan]🔗 URL 프로토콜 처리 중: {raw_url}[/cyan]")
        
        # 디버깅을 위한 환경 정보 로깅
        import tempfile
        debug_file = Path(tempfile.gettempdir()) / "testscenariomaker_debug.log"
        with open(debug_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== URL Protocol Debug {__import__('datetime').datetime.now()} ===\n")
            f.write(f"URL: {raw_url}\n")
            f.write(f"PATH: {os.environ.get('PATH', 'NOT_SET')}\n")
            f.write(f"HOME: {os.environ.get('HOME', 'NOT_SET')}\n")
            f.write(f"USER: {os.environ.get('USER', 'NOT_SET')}\n")
            f.write(f"PWD: {os.getcwd()}\n")
            f.write("="*50 + "\n")
        console.print(f"[dim]🐛 디버그 로그: {debug_file}[/dim]")
        
        # URL 디코딩 및 파싱
        decoded_url = urllib.parse.unquote(raw_url)
        parsed = urllib.parse.urlparse(decoded_url)
        
        # 경로 추출 및 플랫폼별 처리
        if platform.system() == "Windows":
            # Windows: netloc과 path를 합쳐서 전체 경로 구성
            path_str = parsed.netloc + parsed.path
            # Windows 경로 정규화 (뒤쪽 슬래시와 따옴표만 제거)
            path_str = path_str.rstrip('/"')
        else:
            # macOS/Linux: path만 사용 (절대경로 유지)
            path_str = parsed.path
            # 뒤쪽 슬래시와 따옴표만 제거 (앞쪽 슬래시는 절대경로 표시이므로 유지)
            path_str = path_str.rstrip('/"')
        
        # pathlib.Path 객체로 변환
        repository_path = Path(path_str)
        
        console.print(f"[green]📂 분석 대상 경로: {repository_path.resolve()}[/green]")
        
        # 경로 존재 여부 확인
        if not repository_path.exists():
            print(
                f"[red]❌ 경로를 찾을 수 없습니다: {repository_path}[/red]", 
                file=sys.stderr
            )
            sys.exit(1)
        
        if not repository_path.is_dir():
            print(
                f"[red]❌ 디렉토리가 아닙니다: {repository_path}[/red]", 
                file=sys.stderr
            )
            sys.exit(1)
        
        # 기본 설정으로 분석 실행
        console.print(f"[bold blue]TestscenarioMaker CLI v{__version__}[/bold blue]")
        console.print(f"저장소 분석 시작: [green]{repository_path.resolve()}[/green]")
        console.print(f"브랜치 비교: [cyan]origin/develop[/cyan] → [cyan]HEAD[/cyan]")
        
        # CLI 핸들러 생성 및 실행 (기본 설정 사용)
        handler = CLIHandler(verbose=False, output_format="text", dry_run=False)
        
        success = handler.analyze_repository(
            repository_path, 
            base_branch="origin/develop", 
            head_branch="HEAD"
        )
        
        if success:
            console.print(
                "[bold green]✅ 저장소 분석이 성공적으로 완료되었습니다.[/bold green]"
            )
            sys.exit(0)
        else:
            print(
                "[bold red]❌ 저장소 분석 중 오류가 발생했습니다.[/bold red]",
                file=sys.stderr,
            )
            sys.exit(1)
        
        input("디버깅: 작업 완료. Enter 키를 누르면 종료됩니다...")
        sys.exit(0) # input 다음에 종료되도록 이동
            
    except KeyboardInterrupt:
        console.print("\n[yellow]사용자에 의해 중단되었습니다.[/yellow]")
        sys.exit(130)
        
    except Exception as e:
        print(f"[red]URL 처리 중 오류가 발생했습니다: {e}[/red]", file=sys.stderr)
        console.print_exception(show_locals=True)
        input("디버깅: 에러 발생. Enter 키를 누르면 종료됩니다...")
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
                    "[bold green]✅ 저장소 분석이 성공적으로 완료되었습니다.[/bold green]"
                )
            sys.exit(0)
        else:
            print(
                "[bold red]❌ 저장소 분석 중 오류가 발생했습니다.[/bold red]",
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


if __name__ == "__main__":
    main()
