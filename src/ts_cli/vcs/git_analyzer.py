"""
Git 저장소 분석기

Git 저장소의 변경사항을 분석하고 텍스트로 반환하는 구현체입니다.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_analyzer import RepositoryAnalyzer, RepositoryError, InvalidRepositoryError


logger = logging.getLogger(__name__)


class GitAnalyzer(RepositoryAnalyzer):
    """
    Git 저장소 분석기

    Git 명령어를 사용하여 저장소의 변경사항을 분석합니다.
    """

    def validate_repository(self) -> bool:
        """
        Git 저장소 유효성 검증

        Returns:
            유효한 Git 저장소이면 True, 그렇지 않으면 False
        """
        try:
            # .git 디렉토리 존재 확인
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                return False

            # git status 명령어로 저장소 상태 확인
            result = self._run_git_command(
                ["git", "status", "--porcelain"], check_repo=False
            )
            return result is not None

        except Exception as e:
            logger.debug(f"Git 저장소 검증 실패: {e}")
            return False

    def get_changes(self) -> str:
        """
        Git 저장소의 변경사항 분석 텍스트 반환

        git diff HEAD와 git log -1을 조합하여 변경사항을 분석합니다.

        Returns:
            분석된 변경사항 텍스트

        Raises:
            InvalidRepositoryError: 유효하지 않은 Git 저장소인 경우
            RepositoryError: Git 명령어 실행 중 오류 발생시
        """
        if not self.validate_repository():
            raise InvalidRepositoryError(
                "유효하지 않은 Git 저장소입니다.", self.repo_path
            )

        try:
            changes_parts = []

            # 1. 최근 커밋 정보
            commit_info = self._get_latest_commit_info()
            if commit_info:
                changes_parts.append("=== 최근 커밋 정보 ===")
                changes_parts.append(commit_info)
                changes_parts.append("")

            # 2. 작업 디렉토리 변경사항 (Staged + Unstaged)
            working_changes = self._get_working_directory_changes()
            if working_changes:
                changes_parts.append("=== 작업 디렉토리 변경사항 ===")
                changes_parts.append(working_changes)
                changes_parts.append("")

            # 3. HEAD와의 차이점 (커밋되지 않은 모든 변경사항)
            diff_changes = self._get_diff_from_head()
            if diff_changes:
                changes_parts.append("=== HEAD와의 차이점 ===")
                changes_parts.append(diff_changes)

            if not changes_parts:
                return "변경사항이 없습니다. 작업 디렉토리가 깨끗합니다."

            return "\n".join(changes_parts)

        except subprocess.CalledProcessError as e:
            raise RepositoryError(
                f"Git 명령어 실행 실패: {e.stderr.decode('utf-8') if e.stderr else str(e)}",
                self.repo_path,
            )
        except Exception as e:
            raise RepositoryError(
                f"예상치 못한 오류가 발생했습니다: {str(e)}", self.repo_path
            )

    def get_repository_info(self) -> Dict[str, Any]:
        """
        Git 저장소 기본 정보 반환

        Returns:
            저장소 정보를 담은 딕셔너리
        """
        if not self.validate_repository():
            return {}

        try:
            info = {
                "vcs_type": "git",
                "path": str(self.repo_path),
                "is_valid": True,
            }

            # 브랜치 정보
            current_branch = self._get_current_branch()
            if current_branch:
                info["current_branch"] = current_branch

            # 원격 저장소 정보
            remote_url = self._get_remote_url()
            if remote_url:
                info["remote_url"] = remote_url

            # 커밋 수
            commit_count = self._get_commit_count()
            if commit_count is not None:
                info["commit_count"] = commit_count

            # 상태 정보
            status_info = self._get_status_summary()
            info.update(status_info)

            return info

        except Exception as e:
            logger.warning(f"저장소 정보 수집 중 오류: {e}")
            return {
                "vcs_type": "git",
                "path": str(self.repo_path),
                "is_valid": False,
                "error": str(e),
            }

    def _run_git_command(
        self, command: List[str], check_repo: bool = True
    ) -> Optional[str]:
        """
        Git 명령어 실행

        Args:
            command: 실행할 Git 명령어 리스트
            check_repo: 저장소 유효성 검사 여부

        Returns:
            명령어 실행 결과 또는 None (실패시)
        """
        if check_repo and not self.validate_repository():
            return None

        try:
            result = subprocess.run(
                command,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,  # 30초 타임아웃
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.debug(f"Git 명령어 실행 실패: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Git 명령어 실행 시간 초과: {' '.join(command)}")
            return None
        except Exception as e:
            logger.debug(f"Git 명령어 실행 중 오류: {e}")
            return None

    def _get_latest_commit_info(self) -> Optional[str]:
        """최근 커밋 정보 반환"""
        result = self._run_git_command(
            [
                "git",
                "log",
                "-1",
                "--pretty=format:커밋: %H%n작성자: %an <%ae>%n날짜: %ad%n메시지: %s",
                "--date=format:%Y-%m-%d %H:%M:%S",
            ]
        )
        return result

    def _get_working_directory_changes(self) -> Optional[str]:
        """작업 디렉토리 변경사항 반환"""
        result = self._run_git_command(["git", "status", "--porcelain"])
        if not result:
            return None

        changes = []
        for line in result.split("\n"):
            if line.strip():
                status = line[:2]
                filename = line[3:]
                status_desc = self._parse_git_status(status)
                changes.append(f"{status_desc}: {filename}")

        return "\n".join(changes) if changes else None

    def _get_diff_from_head(self) -> Optional[str]:
        """HEAD와의 차이점 반환"""
        # Staged changes
        staged_diff = self._run_git_command(["git", "diff", "--cached"])

        # Unstaged changes
        unstaged_diff = self._run_git_command(["git", "diff"])

        diff_parts = []
        if staged_diff:
            diff_parts.append("--- Staged Changes ---")
            diff_parts.append(staged_diff)

        if unstaged_diff:
            if diff_parts:
                diff_parts.append("")
            diff_parts.append("--- Unstaged Changes ---")
            diff_parts.append(unstaged_diff)

        return "\n".join(diff_parts) if diff_parts else None

    def _get_current_branch(self) -> Optional[str]:
        """현재 브랜치 이름 반환"""
        return self._run_git_command(["git", "branch", "--show-current"])

    def _get_remote_url(self) -> Optional[str]:
        """원격 저장소 URL 반환"""
        return self._run_git_command(["git", "remote", "get-url", "origin"])

    def _get_commit_count(self) -> Optional[int]:
        """전체 커밋 수 반환"""
        result = self._run_git_command(["git", "rev-list", "--count", "HEAD"])
        try:
            return int(result) if result else None
        except (ValueError, TypeError):
            return None

    def _get_status_summary(self) -> Dict[str, Any]:
        """Git 상태 요약 정보 반환"""
        status_result = self._run_git_command(["git", "status", "--porcelain"])

        if not status_result:
            return {"has_changes": False}

        staged_count = 0
        unstaged_count = 0
        untracked_count = 0

        for line in status_result.split("\n"):
            if line.strip():
                status = line[:2]
                if status[0] != " " and status[0] != "?":
                    staged_count += 1
                if status[1] != " ":
                    unstaged_count += 1
                if status.startswith("??"):
                    untracked_count += 1

        return {
            "has_changes": True,
            "staged_files": staged_count,
            "unstaged_files": unstaged_count,
            "untracked_files": untracked_count,
        }

    def _parse_git_status(self, status: str) -> str:
        """Git 상태 코드를 한국어로 변환"""
        status_map = {
            "A ": "추가됨 (Staged)",
            "M ": "수정됨 (Staged)",
            "D ": "삭제됨 (Staged)",
            "R ": "이름변경됨 (Staged)",
            "C ": "복사됨 (Staged)",
            " M": "수정됨 (Unstaged)",
            " D": "삭제됨 (Unstaged)",
            "??": "추적되지 않음",
            "MM": "수정됨 (Staged + Unstaged)",
            "AM": "추가됨 + 수정됨",
            "MD": "수정됨 + 삭제됨",
        }

        return status_map.get(status, f"알 수 없는 상태 ({status})")
