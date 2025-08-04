#!/usr/bin/env python3
"""
TestscenarioMaker CLI 메인 모듈

저장소 분석을 위한 명령행 인터페이스를 제공합니다.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

from . import __version__
from .cli_handler import CLIHandler
from .utils.logger import setup_logger, set_log_level
from .utils.config_loader import load_config

# Rich traceback 설치 (더 예쁜 에러 메시지)
install(show_locals=True)

# 콘솔 인스턴스
console = Console()


@click.command()
@click.option(
    '--path', '-p',
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help='분석할 저장소 경로 (기본값: 현재 디렉토리)'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True, path_type=Path),
    help='사용할 설정 파일 경로'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='상세 출력 모드 활성화'
)
@click.option(
    '--output', '-o',
    type=click.Choice(['text', 'json'], case_sensitive=False),
    default='text',
    help='출력 형식 선택 (기본값: text)'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='실제 API 호출 없이 분석만 수행'
)
@click.version_option(
    version=__version__,
    prog_name='TestscenarioMaker CLI'
)
def cli(
    path: Path,
    config: Optional[Path],
    verbose: bool,
    output: str,
    dry_run: bool
) -> None:
    """
    TestscenarioMaker CLI - 로컬 저장소 분석 도구
    
    로컬 Git 저장소를 분석하여 TestscenarioMaker 서버로 전송하고
    분석 결과를 다운로드합니다.
    
    예시:
        ts-cli --path /path/to/repo --verbose
        ts-cli -p . -o json
        ts-cli --config custom_config.ini --dry-run
    """
    try:
        # 설정 로드
        load_config(config)
        
        # 로거 설정
        log_level = 'DEBUG' if verbose else 'INFO'
        logger = setup_logger(level=log_level)
        
        if verbose:
            set_log_level('DEBUG')
        
        # 환영 메시지
        if not dry_run:
            console.print(
                f"[bold blue]TestscenarioMaker CLI v{__version__}[/bold blue]"
            )
            console.print(f"저장소 분석 시작: [green]{path.resolve()}[/green]")
        
        # CLI 핸들러 생성 및 실행
        handler = CLIHandler(
            verbose=verbose,
            output_format=output,
            dry_run=dry_run
        )
        
        success = handler.analyze_repository(path)
        
        if success:
            if not dry_run:
                console.print(
                    "[bold green]✅ 저장소 분석이 성공적으로 완료되었습니다![/bold green]"
                )
            sys.exit(0)
        else:
            console.print(
                "[bold red]❌ 저장소 분석 중 오류가 발생했습니다.[/bold red]",
                file=sys.stderr
            )
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print(
            "\n[yellow]사용자에 의해 작업이 중단되었습니다.[/yellow]"
        )
        sys.exit(1)
        
    except Exception as e:
        console.print(
            f"[bold red]예상치 못한 오류가 발생했습니다: {str(e)}[/bold red]",
            file=sys.stderr
        )
        if verbose:
            console.print_exception(show_locals=True)
        sys.exit(1)


@click.group()
def main() -> None:
    """TestscenarioMaker CLI 도구 모음"""
    pass


@main.command()
@click.option(
    '--config', '-c',
    type=click.Path(path_type=Path),
    help='설정 파일 경로'
)
def config_show(config: Optional[Path]) -> None:
    """현재 설정 정보를 표시합니다."""
    try:
        config_loader = load_config(config)
        all_config = config_loader.get_all_sections()
        
        console.print("[bold blue]현재 설정:[/bold blue]")
        console.print(f"설정 파일: [green]{config_loader.config_path}[/green]")
        console.print()
        
        for section_name, section_data in all_config.items():
            console.print(f"[bold yellow][{section_name}][/bold yellow]")
            for key, value in section_data.items():
                console.print(f"  {key} = {value}")
            console.print()
            
    except Exception as e:
        console.print(f"[red]설정 정보 조회 실패: {e}[/red]", file=sys.stderr)
        sys.exit(1)


@main.command()
@click.argument('path', type=click.Path(exists=True, path_type=Path))
def info(path: Path) -> None:
    """저장소 정보를 표시합니다 (분석 없이)."""
    try:
        from .vcs import get_analyzer
        
        analyzer = get_analyzer(path)
        if not analyzer:
            console.print(
                f"[red]{path}는 지원되는 VCS 저장소가 아닙니다.[/red]",
                file=sys.stderr
            )
            sys.exit(1)
        
        if not analyzer.validate_repository():
            console.print(
                f"[red]{path}는 유효하지 않은 저장소입니다.[/red]",
                file=sys.stderr
            )
            sys.exit(1)
        
        repo_info = analyzer.get_repository_info()
        
        console.print("[bold blue]저장소 정보:[/bold blue]")
        console.print(f"경로: [green]{repo_info.get('path', 'N/A')}[/green]")
        console.print(f"VCS 타입: [yellow]{repo_info.get('vcs_type', 'N/A')}[/yellow]")
        
        if repo_info.get('current_branch'):
            console.print(f"현재 브랜치: [cyan]{repo_info['current_branch']}[/cyan]")
        
        if repo_info.get('remote_url'):
            console.print(f"원격 저장소: [blue]{repo_info['remote_url']}[/blue]")
        
        if repo_info.get('commit_count') is not None:
            console.print(f"총 커밋 수: [magenta]{repo_info['commit_count']}[/magenta]")
        
        # 상태 정보
        if repo_info.get('has_changes'):
            console.print("\n[bold yellow]변경사항 요약:[/bold yellow]")
            console.print(f"  Staged 파일: {repo_info.get('staged_files', 0)}")
            console.print(f"  Unstaged 파일: {repo_info.get('unstaged_files', 0)}")
            console.print(f"  Untracked 파일: {repo_info.get('untracked_files', 0)}")
        else:
            console.print("\n[green]작업 디렉토리가 깨끗합니다.[/green]")
            
    except Exception as e:
        console.print(f"[red]저장소 정보 조회 실패: {e}[/red]", file=sys.stderr)
        sys.exit(1)


@main.command()
def version() -> None:
    """버전 정보를 표시합니다."""
    console.print(f"TestscenarioMaker CLI v{__version__}")


# 기본 명령어를 main 그룹에 추가
main.add_command(cli, name='analyze')


if __name__ == '__main__':
    main()