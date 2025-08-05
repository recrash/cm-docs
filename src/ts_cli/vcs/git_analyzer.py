"""
Git 저장소 분석기

Git 저장소의 변경사항을 분석하고 텍스트로 반환하는 구현체입니다.
TestscenarioMaker 서버와 동일한 분석 로직을 사용합니다.
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
    TestscenarioMaker 서버와 동일한 분석 로직을 사용합니다.
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

    def get_changes(self, base_branch: str = "origin/develop", head_branch: str = "HEAD") -> str:
        """
        Git 저장소의 변경사항 분석 텍스트 반환

        TestscenarioMaker 서버와 동일한 로직으로 브랜치 간 비교를 수행합니다:
        1. 공통 조상 커밋 찾기
        2. 커밋 메시지 수집 (공통 조상부터 HEAD까지)
        3. 코드 변경사항 분석 (diff)
        4. Working State 포함

        Args:
            base_branch: 기준 브랜치명 (기본값: origin/develop)
            head_branch: 대상 브랜치명 (기본값: HEAD)

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

            # 1. 브랜치 간 비교 분석 (TestscenarioMaker 서버 로직)
            branch_analysis = self._get_branch_comparison_analysis(base_branch, head_branch)
            if branch_analysis:
                changes_parts.append(branch_analysis)
                changes_parts.append("")

            # 2. Working State 분석 (현재 작업 디렉토리 변경사항)
            working_state_analysis = self._get_working_state_analysis()
            if working_state_analysis:
                changes_parts.append(working_state_analysis)

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

    def _get_branch_comparison_analysis(self, base_branch: str, head_branch: str) -> Optional[str]:
        """
        브랜치 간 비교 분석 (TestscenarioMaker 서버 로직과 동일)

        Args:
            base_branch: 기준 브랜치명
            head_branch: 대상 브랜치명

        Returns:
            브랜치 비교 분석 결과 텍스트
        """
        try:
            analysis_parts = []

            # 1. 공통 조상 커밋 찾기
            merge_base = self._get_merge_base_commit(base_branch, head_branch)
            if not merge_base:
                return "오류: 공통 조상을 찾을 수 없습니다."

            # 2. 커밋 메시지 수집 (공통 조상부터 HEAD까지)
            commit_messages = self._get_commit_messages(merge_base, head_branch)
            if commit_messages:
                analysis_parts.append("### 커밋 메시지 목록:")
                analysis_parts.extend(commit_messages)
                analysis_parts.append("")

            # 3. 코드 변경사항 분석 (diff)
            code_changes = self._get_code_changes(merge_base, head_branch)
            if code_changes:
                analysis_parts.append("### 주요 코드 변경 내용 (diff):")
                analysis_parts.extend(code_changes)

            return "\n".join(analysis_parts) if analysis_parts else None

        except Exception as e:
            logger.error(f"브랜치 비교 분석 중 오류: {e}")
            return f"브랜치 비교 분석 중 오류가 발생했습니다: {str(e)}"

    def _get_merge_base_commit(self, base_branch: str, head_branch: str) -> Optional[str]:
        """
        두 브랜치의 공통 조상 커밋을 찾습니다.

        Args:
            base_branch: 기준 브랜치명
            head_branch: 대상 브랜치명

        Returns:
            공통 조상 커밋의 해시 또는 None
        """
        try:
            # merge-base 명령어로 공통 조상 찾기
            result = self._run_git_command(
                ["git", "merge-base", base_branch, head_branch]
            )
            return result.strip() if result else None
        except Exception as e:
            logger.error(f"공통 조상 찾기 실패: {e}")
            return None

    def _get_commit_messages(self, base_commit: str, head_branch: str) -> List[str]:
        """
        공통 조상부터 HEAD까지의 커밋 메시지를 수집합니다.

        Args:
            base_commit: 공통 조상 커밋 해시
            head_branch: 대상 브랜치명

        Returns:
            커밋 메시지 리스트
        """
        try:
            # git log 명령어로 커밋 메시지 수집 (시간순 정렬)
            result = self._run_git_command([
                "git", "log", 
                f"{base_commit}..{head_branch}",
                "--pretty=format:- %s",
                "--reverse"  # 시간순 정렬
            ])
            
            if result:
                return result.strip().split("\n")
            return []
        except Exception as e:
            logger.error(f"커밋 메시지 수집 실패: {e}")
            return []

    def _get_code_changes(self, base_commit: str, head_branch: str) -> List[str]:
        """
        공통 조상과 HEAD 간의 코드 변경사항을 분석합니다.

        Args:
            base_commit: 공통 조상 커밋 해시
            head_branch: 대상 브랜치명

        Returns:
            코드 변경사항 리스트
        """
        try:
            changes = []
            
            # git diff 명령어로 전체 diff 가져오기
            diff_result = self._run_git_command([
                "git", "diff", 
                base_commit, head_branch,
                "--unified=3"  # 3줄 컨텍스트
            ])
            
            if diff_result:
                # 파일별로 분리하여 처리
                files = self._parse_diff_files(diff_result)
                for file_info in files:
                    changes.extend(file_info)
                    
                    # 파일당 최대 20줄로 제한 (TestscenarioMaker 서버와 동일)
                    if len(changes) > 20:
                        changes.append("... (내용 생략) ...")
                        break

            return changes
        except Exception as e:
            logger.error(f"코드 변경사항 분석 실패: {e}")
            return [f"코드 변경사항 분석 중 오류가 발생했습니다: {str(e)}"]

    def _parse_diff_files(self, diff_output: str) -> List[List[str]]:
        """
        git diff 출력을 파일별로 파싱합니다.

        Args:
            diff_output: git diff 명령어 출력

        Returns:
            파일별 diff 내용 리스트
        """
        files = []
        current_file = []
        current_filename = None
        
        for line in diff_output.split("\n"):
            if line.startswith("diff --git"):
                # 새 파일 시작
                if current_file and current_filename:
                    files.append(current_file)
                
                # 파일명 추출
                parts = line.split()
                if len(parts) >= 3:
                    current_filename = parts[2].replace("a/", "").replace("b/", "")
                    current_file = [f"--- 파일: {current_filename} ---"]
                else:
                    current_filename = None
                    current_file = []
            elif line.startswith("---") or line.startswith("+++"):
                continue  # 헤더 라인 건너뛰기
            else:
                if current_filename:  # 파일명이 있는 경우에만 내용 추가
                    current_file.append(line)
        
        # 마지막 파일 추가
        if current_file and current_filename:
            files.append(current_file)
            
        return files

    def _get_working_state_analysis(self) -> Optional[str]:
        """
        현재 작업 디렉토리의 상태를 분석합니다 (Working State).

        Returns:
            작업 디렉토리 상태 분석 결과
        """
        try:
            analysis_parts = []

            # 1. 작업 디렉토리 변경사항 (Staged + Unstaged)
            working_changes = self._get_working_directory_changes()
            if working_changes:
                analysis_parts.append("### 작업 디렉토리 변경사항 (Working State):")
                analysis_parts.append(working_changes)
                analysis_parts.append("")

            # 2. HEAD와의 차이점 (커밋되지 않은 모든 변경사항)
            diff_changes = self._get_diff_from_head()
            if diff_changes:
                analysis_parts.append("### HEAD와의 차이점 (Working State):")
                analysis_parts.append(diff_changes)

            return "\n".join(analysis_parts) if analysis_parts else None

        except Exception as e:
            logger.error(f"작업 상태 분석 중 오류: {e}")
            return f"작업 상태 분석 중 오류가 발생했습니다: {str(e)}"

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
