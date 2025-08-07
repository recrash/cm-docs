"""
CLI 비즈니스 로직 핸들러

저장소 분석 → API 호출 → 결과 처리의 전체 워크플로우를 관리합니다.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.panel import Panel
from rich.syntax import Syntax

from .vcs import get_analyzer, get_supported_vcs_types
from .vcs.base_analyzer import (
    RepositoryError,
    UnsupportedVCSError,
    InvalidRepositoryError,
)
from .api_client import APIClient, APIError
from .utils.logger import get_logger


class CLIHandler:
    """
    CLI 비즈니스 로직 핸들러

    저장소 분석부터 결과 다운로드까지의 전체 프로세스를 관리합니다.
    """

    def __init__(
        self, verbose: bool = False, output_format: str = "text", dry_run: bool = False
    ) -> None:
        """
        CLIHandler 초기화

        Args:
            verbose: 상세 출력 모드
            output_format: 출력 형식 ('text' 또는 'json')
            dry_run: 실제 API 호출 없이 분석만 수행
        """
        self.verbose = verbose
        self.output_format = output_format
        self.dry_run = dry_run

        self.console = Console()
        self.logger = get_logger(f"{__package__}.{self.__class__.__name__}")

        # API 클라이언트는 필요시에만 초기화
        self._api_client: Optional[APIClient] = None

    @property
    def api_client(self) -> APIClient:
        """API 클라이언트 지연 초기화"""
        if self._api_client is None:
            self._api_client = APIClient()
        return self._api_client

    def analyze_repository(self, path: Path, base_branch: str = "origin/develop", head_branch: str = "HEAD") -> bool:
        """
        저장소 분석 메인 워크플로우

        Args:
            path: 분석할 저장소 경로
            base_branch: 기준 브랜치명 (기본값: origin/develop)
            head_branch: 대상 브랜치명 (기본값: HEAD)

        Returns:
            성공 여부
        """
        try:
            # 1. 저장소 유효성 검사 및 분석기 생성
            analyzer = self._validate_repository(path)
            if not analyzer:
                return False

            # 2. 저장소 변경사항 분석 (브랜치 파라미터 전달)
            analysis_result = self._analyze_changes(analyzer, base_branch, head_branch)
            if not analysis_result:
                return False

            # 3. Dry run 모드인 경우 결과만 출력하고 종료
            if self.dry_run:
                self._display_dry_run_result(analysis_result)
                return True

            # 4. v2 API로 시나리오 생성 요청
            api_response = self._send_to_api_v2(path)
            if not api_response:
                return False

            # 5. 결과 출력
            self._display_final_result_v2(api_response)

            return True

        except Exception as e:
            self.logger.error(f"저장소 분석 중 오류: {e}")
            self.console.print(f"[red]저장소 분석 중 오류가 발생했습니다: {str(e)}[/red]")
            return False

    def _validate_repository(self, path: Path) -> Optional[Any]:
        """
        저장소 유효성 검사 및 분석기 생성

        Args:
            path: 저장소 경로

        Returns:
            분석기 인스턴스 또는 None
        """
        try:
            if self.verbose:
                self.console.print(f"[dim]저장소 검증 중: {path.resolve()}[/dim]")

            # 경로 존재 여부 확인
            if not path.exists():
                self.console.print(f"[red]경로가 존재하지 않습니다: {path}[/red]")
                return None

            if not path.is_dir():
                self.console.print(f"[red]디렉토리가 아닙니다: {path}[/red]")
                return None

            # VCS 분석기 생성
            analyzer = get_analyzer(path)
            if not analyzer:
                supported_types = ", ".join(get_supported_vcs_types())
                self.console.print(
                    f"[red]지원되지 않는 저장소 타입입니다.[/red]\n"
                    f"지원되는 VCS: {supported_types}"
                )
                return None

            # 저장소 유효성 검증
            if not analyzer.validate_repository():
                self.console.print(
                    f"[red]유효하지 않은 {analyzer.get_vcs_type().upper()} 저장소입니다.[/red]"
                )
                return None

            if self.verbose:
                repo_info = analyzer.get_repository_info()
                self.console.print(
                    f"[green]✓[/green] {analyzer.get_vcs_type().upper()} 저장소 확인됨"
                )
                if repo_info.get("current_branch"):
                    self.console.print(
                        f"  현재 브랜치: [cyan]{repo_info['current_branch']}[/cyan]"
                    )

            return analyzer

        except Exception as e:
            self.logger.error(f"저장소 검증 중 오류: {e}")
            self.console.print(
                f"[red]저장소 검증 중 오류가 발생했습니다: {str(e)}[/red]"
            )
            return None

    def _analyze_changes(self, analyzer: Any, base_branch: str = "origin/develop", head_branch: str = "HEAD") -> Optional[Dict[str, Any]]:
        """
        저장소 변경사항 분석

        Args:
            analyzer: VCS 분석기
            base_branch: 기준 브랜치명
            head_branch: 대상 브랜치명

        Returns:
            분석 결과 딕셔너리 또는 None
        """
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("저장소 변경사항 분석 중...", total=None)

                # 저장소 정보 수집
                repo_info = analyzer.get_repository_info()

                # 변경사항 분석 (브랜치 파라미터 전달)
                changes_text = analyzer.get_changes(base_branch, head_branch)

                progress.update(task, completed=True)

            # 분석 결과 구성
            analysis_result = {
                "repository_info": repo_info,
                "changes_text": changes_text,
                "analysis_timestamp": self._get_current_timestamp(),
                "cli_version": self._get_cli_version(),
                "branch_info": {
                    "base_branch": base_branch,
                    "head_branch": head_branch,
                },
            }

            if self.verbose:
                self.console.print("[green]✓[/green] 저장소 분석 완료")
                self.console.print(f"  변경사항 크기: {len(changes_text)} 문자")
                self.console.print(f"  기준 브랜치: {base_branch}")
                self.console.print(f"  대상 브랜치: {head_branch}")

                if not changes_text.strip():
                    self.console.print("  [yellow]변경사항이 없습니다.[/yellow]")

            return analysis_result

        except RepositoryError as e:
            self.logger.error(f"저장소 분석 오류: {e}")
            self.console.print(f"[red]저장소 분석 실패: {str(e)}[/red]")
            return None

        except Exception as e:
            self.logger.error(f"변경사항 분석 중 오류: {e}")
            self.console.print(
                f"[red]변경사항 분석 중 오류가 발생했습니다: {str(e)}[/red]"
            )
            return None

    def _send_to_api_v2(self, repo_path: Path) -> Optional[Dict[str, Any]]:
        """
        v2 API로 시나리오 생성 요청

        Args:
            repo_path: 저장소 경로

        Returns:
            API 응답 또는 None
        """
        try:
            # v2 API 호출을 위한 비동기 함수
            async def run_v2_generation():
                client_id = None
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeElapsedColumn(),
                    console=self.console,
                    transient=False,
                ) as progress:
                    # 1단계: v2 API 요청
                    api_task = progress.add_task("v2 API 요청 전송 중...", total=100)
                    
                    def api_progress_callback(message: str, progress_value: int):
                        progress.update(api_task, description=message, completed=progress_value)
                    
                    response = await self.api_client.send_analysis_v2(
                        repo_path=str(repo_path.resolve()),
                        use_performance_mode=True,
                        progress_callback=api_progress_callback,
                    )
                    
                    client_id = response.get("client_id")
                    websocket_url = response.get("websocket_url")
                    
                    progress.update(api_task, completed=100, description="v2 API 요청 완료")
                    
                    if not websocket_url:
                        raise APIError("WebSocket URL을 받지 못했습니다.")
                    
                    # 2단계: WebSocket으로 진행 상황 모니터링
                    ws_task = progress.add_task("시나리오 생성 진행 중...", total=100)
                    
                    def ws_progress_callback(status: str, message: str, progress_value: int, result: Optional[Dict[str, Any]]):
                        progress.update(ws_task, description=f"[{status}] {message}", completed=progress_value)
                    
                    # WebSocket 연결 및 진행 상황 수신
                    final_result = await self.api_client.listen_to_progress_v2(
                        websocket_url=websocket_url,
                        progress_callback=ws_progress_callback,
                        timeout=600,
                    )
                    
                    progress.update(ws_task, completed=100, description="시나리오 생성 완료!")
                    
                    return final_result
            
            # 비동기 함수 실행
            result = asyncio.run(run_v2_generation())

            if self.verbose:
                self.console.print("[green]✓[/green] v2 API 시나리오 생성 완료")

            return result

        except APIError as e:
            self.logger.error(f"v2 API 호출 오류: {e}")
            self.console.print(f"[red]v2 API 서버 통신 실패: {str(e)}[/red]")
            return None

        except Exception as e:
            self.logger.error(f"v2 API 전송 중 오류: {e}")
            self.console.print(f"[red]v2 API 전송 중 오류가 발생했습니다: {str(e)}[/red]")
            return None

    def _display_dry_run_result(self, analysis_result: Dict[str, Any]) -> None:
        """
        Dry run 모드 결과 출력

        Args:
            analysis_result: 분석 결과
        """
        self.console.print("\n[bold blue]== Dry Run 모드 - 분석 결과 ==[/bold blue]")

        if self.output_format == "json":
            # JSON 형식으로 출력
            json_output = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            syntax = Syntax(json_output, "json", theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            # 텍스트 형식으로 출력
            repo_info = analysis_result.get("repository_info", {})
            changes_text = analysis_result.get("changes_text", "")

            # 저장소 정보
            info_panel = Panel(
                f"경로: {repo_info.get('path', 'N/A')}\n"
                f"VCS 타입: {repo_info.get('vcs_type', 'N/A')}\n"
                f"브랜치: {repo_info.get('current_branch', 'N/A')}\n"
                f"커밋 수: {repo_info.get('commit_count', 'N/A')}",
                title="저장소 정보",
                border_style="blue",
            )
            self.console.print(info_panel)

            # 변경사항
            if changes_text.strip():
                changes_panel = Panel(
                    changes_text,
                    title="변경사항 분석 결과",
                    border_style="green",
                    expand=False,
                )
                self.console.print(changes_panel)
            else:
                self.console.print("[yellow]변경사항이 없습니다.[/yellow]")

    def _display_final_result_v2(self, api_response: Dict[str, Any]) -> None:
        """
        v2 API 최종 결과 출력

        Args:
            api_response: v2 API 응답 (result 데이터)
        """
        if self.output_format == "json":
            # JSON 형식으로 출력
            json_output = json.dumps(api_response, ensure_ascii=False, indent=2)
            syntax = Syntax(json_output, "json", theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            # 텍스트 형식으로 출력
            filename = api_response.get('filename', '')
            description = api_response.get('description', '')
            download_url = api_response.get('download_url', '')

            result_panel = Panel(
                f"파일명: {filename}\n"
                f"설명: {description}\n"
                f"다운로드 URL: http://localhost:8000{download_url}",
                title="✅ 시나리오 생성 완료",
                border_style="green",
            )
            self.console.print(result_panel)

            # 추가 안내 메시지
            self.console.print("\n[bold blue]🎉 테스트 시나리오가 성공적으로 생성되었습니다![/bold blue]")
            self.console.print(f"[cyan]다운로드 링크: http://localhost:8000{download_url}[/cyan]")

    def _display_final_result(self, api_response: Dict[str, Any]) -> None:
        """
        최종 결과 출력 (v1 API 호환성 유지)

        Args:
            api_response: API 응답
        """
        if self.output_format == "json":
            # JSON 형식으로 출력
            json_output = json.dumps(api_response, ensure_ascii=False, indent=2)
            syntax = Syntax(json_output, "json", theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            # 텍스트 형식으로 출력
            download_url = api_response.get('download_url', '')
            filename = api_response.get('filename', '')
            message = api_response.get('message', '')

            result_panel = Panel(
                f"파일명: {filename}\n"
                f"메시지: {message}\n"
                f"웹 UI 다운로드: http://localhost:8000{download_url}",
                title="✅ 시나리오 생성 완료",
                border_style="green",
            )
            self.console.print(result_panel)

            # 추가 안내 메시지
            self.console.print("\n[bold blue] 웹 UI에서 결과를 확인하고 다운로드하세요:[/bold blue]")
            self.console.print(f"[cyan]http://localhost:8000{download_url}[/cyan]")

    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _get_cli_version(self) -> str:
        """CLI 버전 반환"""
        from . import __version__

        return __version__
