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

    def analyze_repository(self, path: Path) -> bool:
        """
        저장소 분석 메인 워크플로우

        Args:
            path: 분석할 저장소 경로

        Returns:
            성공 여부
        """
        try:
            # 1. 저장소 유효성 검사 및 분석기 생성
            analyzer = self._validate_repository(path)
            if not analyzer:
                return False

            # 2. 저장소 변경사항 분석
            analysis_result = self._analyze_changes(analyzer)
            if not analysis_result:
                return False

            # 3. Dry run 모드인 경우 결과만 출력하고 종료
            if self.dry_run:
                self._display_dry_run_result(analysis_result)
                return True

            # 4. API 서버로 분석 결과 전송
            api_response = self._send_to_api(analysis_result)
            if not api_response:
                return False

            # 5. 결과 파일 다운로드
            download_success = self._download_result(api_response)
            if not download_success:
                return False

            # 6. 최종 결과 출력
            self._display_final_result(api_response)

            return True

        except KeyboardInterrupt:
            self.console.print(
                "\n[yellow]사용자에 의해 작업이 중단되었습니다.[/yellow]"
            )
            return False

        except Exception as e:
            self.logger.error(f"저장소 분석 중 예상치 못한 오류: {e}")
            self.console.print(f"[red]예상치 못한 오류가 발생했습니다: {str(e)}[/red]")
            if self.verbose:
                self.console.print_exception(show_locals=True)
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

    def _analyze_changes(self, analyzer: Any) -> Optional[Dict[str, Any]]:
        """
        저장소 변경사항 분석

        Args:
            analyzer: VCS 분석기

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

                # 변경사항 분석
                changes_text = analyzer.get_changes()

                progress.update(task, completed=True)

            # 분석 결과 구성
            analysis_result = {
                "repository_info": repo_info,
                "changes_text": changes_text,
                "analysis_timestamp": self._get_current_timestamp(),
                "cli_version": self._get_cli_version(),
            }

            if self.verbose:
                self.console.print("[green]✓[/green] 저장소 분석 완료")
                self.console.print(f"  변경사항 크기: {len(changes_text)} 문자")

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

    def _send_to_api(self, analysis_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        API 서버로 분석 결과 전송

        Args:
            analysis_result: 분석 결과

        Returns:
            API 응답 또는 None
        """
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("API 서버로 데이터 전송 중...", total=100)

                # 비동기 API 호출을 동기적으로 실행
                response = asyncio.run(
                    self.api_client.send_analysis(
                        analysis_result,
                        progress_callback=lambda p: progress.update(task, completed=p),
                    )
                )

                progress.update(task, completed=100)

            if self.verbose:
                self.console.print("[green]✓[/green] API 서버 전송 완료")
                if response.get("analysis_id"):
                    self.console.print(
                        f"  분석 ID: [cyan]{response['analysis_id']}[/cyan]"
                    )

            return response

        except APIError as e:
            self.logger.error(f"API 호출 오류: {e}")
            self.console.print(f"[red]API 서버 통신 실패: {str(e)}[/red]")
            return None

        except Exception as e:
            self.logger.error(f"API 전송 중 오류: {e}")
            self.console.print(f"[red]API 전송 중 오류가 발생했습니다: {str(e)}[/red]")
            return None

    def _download_result(self, api_response: Dict[str, Any]) -> bool:
        """
        결과 파일 다운로드

        Args:
            api_response: API 응답

        Returns:
            다운로드 성공 여부
        """
        try:
            if not api_response.get("result_url"):
                self.console.print("[yellow]다운로드할 결과 파일이 없습니다.[/yellow]")
                return True  # 오류는 아니므로 True 반환

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("결과 파일 다운로드 중...", total=100)

                # 비동기 다운로드를 동기적으로 실행
                download_path = asyncio.run(
                    self.api_client.download_result(
                        api_response["result_url"],
                        progress_callback=lambda p: progress.update(task, completed=p),
                    )
                )

                progress.update(task, completed=100)

            if download_path:
                if self.verbose:
                    self.console.print("[green]✓[/green] 결과 파일 다운로드 완료")
                    self.console.print(f"  저장 위치: [cyan]{download_path}[/cyan]")

                # API 응답에 다운로드 경로 추가
                api_response["download_path"] = str(download_path)
                return True
            else:
                self.console.print("[red]결과 파일 다운로드에 실패했습니다.[/red]")
                return False

        except APIError as e:
            self.logger.error(f"다운로드 오류: {e}")
            self.console.print(f"[red]결과 파일 다운로드 실패: {str(e)}[/red]")
            return False

        except Exception as e:
            self.logger.error(f"다운로드 중 오류: {e}")
            self.console.print(f"[red]다운로드 중 오류가 발생했습니다: {str(e)}[/red]")
            return False

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

    def _display_final_result(self, api_response: Dict[str, Any]) -> None:
        """
        최종 결과 출력

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
            result_panel = Panel(
                f"분석 ID: {api_response.get('analysis_id', 'N/A')}\n"
                f"상태: {api_response.get('status', 'N/A')}\n"
                f"처리 시간: {api_response.get('processing_time', 'N/A')}\n"
                f"결과 파일: {api_response.get('download_path', '다운로드되지 않음')}",
                title="분석 완료",
                border_style="green",
            )
            self.console.print(result_panel)

    def _get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

    def _get_cli_version(self) -> str:
        """CLI 버전 반환"""
        from . import __version__

        return __version__
