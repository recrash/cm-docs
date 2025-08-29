"""
SVN 저장소 분석기

SVN 저장소의 변경사항을 분석하고 텍스트로 반환하는 구현체입니다.
Working Directory와 직전 커밋(HEAD)을 비교하여 변경사항을 추출합니다.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_analyzer import RepositoryAnalyzer, RepositoryError, InvalidRepositoryError


logger = logging.getLogger(__name__)


class SVNAnalyzer(RepositoryAnalyzer):
    """
    SVN 저장소 분석기
    
    SVN 명령어를 사용하여 저장소의 변경사항을 분석합니다.
    Working Directory와 HEAD 리비전을 비교하여 변경사항을 추출합니다.
    """

    def validate_repository(self) -> bool:
        """
        SVN 저장소 유효성 검증

        Returns:
            유효한 SVN 저장소이면 True, 그렇지 않으면 False
        """
        try:
            # .svn 디렉토리 존재 확인
            svn_dir = self.repo_path / ".svn"
            if not svn_dir.exists():
                return False

            # svn info 명령어로 저장소 상태 확인
            result = self._run_svn_command(
                ["svn", "info"], check_repo=False
            )
            return result is not None

        except Exception as e:
            logger.debug(f"SVN 저장소 검증 실패: {e}")
            return False

    def get_changes(self, base_branch: str = "", head_branch: str = "") -> str:
        """
        SVN 저장소의 Working Directory vs HEAD 변경사항 분석
        
        SVN에서는 브랜치 개념이 다르므로 base_branch, head_branch 파라미터는 무시하고
        Working Directory와 HEAD 리비전을 비교합니다.

        Args:
            base_branch: SVN에서는 사용되지 않음 (호환성을 위한 파라미터)
            head_branch: SVN에서는 사용되지 않음 (호환성을 위한 파라미터)

        Returns:
            분석된 변경사항 텍스트

        Raises:
            RepositoryError: SVN 명령어 실행 중 오류 발생시
        """
        try:
            logger.debug("SVN 저장소 변경사항 분석 시작")
            
            changes_parts = []
            
            # 1. SVN 저장소 기본 정보
            info_result = self._run_svn_command(["svn", "info"])
            if info_result:
                changes_parts.append("=== SVN 저장소 정보 ===")
                changes_parts.append(info_result.strip())
                changes_parts.append("")
            
            # 2. Working Directory 상태 확인 (수정된 파일, 추가된 파일 등)
            status_result = self._run_svn_command(["svn", "status"])
            if status_result and status_result.strip():
                changes_parts.append("=== Working Directory 상태 ===")
                changes_parts.append(status_result.strip())
                changes_parts.append("")
            
            # 3. Working Directory vs HEAD 차이점 분석
            diff_result = self._run_svn_command(["svn", "diff"])
            if diff_result and diff_result.strip():
                changes_parts.append("=== Working Directory vs HEAD 차이점 ===")
                changes_parts.append(diff_result.strip())
                changes_parts.append("")
            
            # 4. 최근 커밋 로그 (참고 정보)
            log_result = self._run_svn_command(["svn", "log", "-l", "3", "-v"])
            if log_result:
                changes_parts.append("=== 최근 커밋 로그 (참고) ===")
                changes_parts.append(log_result.strip())
            
            if not changes_parts:
                return "변경사항이 없습니다. Working Directory가 HEAD와 동일합니다."
            
            full_changes = "\n".join(changes_parts)
            logger.debug(f"SVN 변경사항 분석 완료: {len(full_changes)} 문자")
            
            return full_changes

        except subprocess.CalledProcessError as e:
            error_msg = f"SVN 명령어 실행 실패: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            raise RepositoryError(error_msg, self.repo_path)
        
        except Exception as e:
            error_msg = f"SVN 저장소 분석 중 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            raise RepositoryError(error_msg, self.repo_path)

    def get_repository_info(self) -> Dict[str, Any]:
        """
        SVN 저장소 기본 정보 반환

        Returns:
            저장소 정보를 담은 딕셔너리
        """
        try:
            info = {
                "path": str(self.repo_path),
                "vcs_type": "svn"
            }
            
            # SVN info 명령어로 저장소 정보 수집
            info_result = self._run_svn_command(["svn", "info"])
            if info_result:
                # URL 추출
                for line in info_result.split('\n'):
                    if line.startswith('URL: '):
                        info["repository_url"] = line.replace('URL: ', '').strip()
                    elif line.startswith('Revision: '):
                        info["current_revision"] = line.replace('Revision: ', '').strip()
                    elif line.startswith('Repository Root: '):
                        info["repository_root"] = line.replace('Repository Root: ', '').strip()
            
            # Working Directory 상태 정보
            status_result = self._run_svn_command(["svn", "status"])
            if status_result:
                modified_files = []
                added_files = []
                deleted_files = []
                
                for line in status_result.split('\n'):
                    if line.strip():
                        status_char = line[0] if len(line) > 0 else ''
                        filename = line[1:].strip() if len(line) > 1 else ''
                        
                        if status_char == 'M':
                            modified_files.append(filename)
                        elif status_char == 'A':
                            added_files.append(filename)
                        elif status_char == 'D':
                            deleted_files.append(filename)
                
                info["modified_files_count"] = len(modified_files)
                info["added_files_count"] = len(added_files)
                info["deleted_files_count"] = len(deleted_files)
                info["has_changes"] = len(modified_files) + len(added_files) + len(deleted_files) > 0
            else:
                info["has_changes"] = False
                info["modified_files_count"] = 0
                info["added_files_count"] = 0
                info["deleted_files_count"] = 0
            
            return info

        except Exception as e:
            logger.error(f"SVN 저장소 정보 수집 실패: {e}")
            return {
                "path": str(self.repo_path),
                "vcs_type": "svn",
                "error": str(e)
            }

    def _run_svn_command(
        self, 
        command: List[str], 
        check_repo: bool = True,
        timeout: int = 30
    ) -> Optional[str]:
        """
        SVN 명령어 실행 헬퍼 메서드

        Args:
            command: 실행할 SVN 명령어 리스트
            check_repo: 저장소 유효성 사전 검사 여부
            timeout: 명령어 실행 타임아웃 (초)

        Returns:
            명령어 실행 결과 또는 None (실패시)

        Raises:
            subprocess.CalledProcessError: SVN 명령어 실행 실패시
        """
        try:
            if check_repo and not self.repo_path.exists():
                raise RepositoryError(f"저장소 경로가 존재하지 않습니다: {self.repo_path}")

            logger.debug(f"SVN 명령어 실행: {' '.join(command)} (경로: {self.repo_path})")
            
            result = subprocess.run(
                command,
                cwd=str(self.repo_path),  # pathlib.Path를 문자열로 변환
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=timeout,
                check=True
            )
            
            return result.stdout

        except subprocess.TimeoutExpired as e:
            error_msg = f"SVN 명령어 타임아웃 ({timeout}초): {' '.join(command)}"
            logger.error(error_msg)
            raise RepositoryError(error_msg, self.repo_path)
        
        except subprocess.CalledProcessError as e:
            # SVN 명령어가 설치되지 않은 경우 특별 처리
            stderr_msg = e.stderr if e.stderr else ""
            if "not found" in str(e) or "command not found" in stderr_msg:
                error_msg = (
                    "SVN 명령어가 설치되지 않았습니다. "
                    "SVN 클라이언트를 설치한 후 다시 시도해주세요.\n"
                    "Windows: TortoiseSVN 또는 SVN Command Line Tools\n"
                    "macOS: brew install subversion\n"
                    "Linux: apt-get install subversion 또는 yum install subversion"
                )
                logger.error(error_msg)
                raise RepositoryError(error_msg, self.repo_path)
            
            # 기타 SVN 오류
            stderr_msg = e.stderr if e.stderr else "알 수 없는 오류"
            error_msg = f"SVN 명령어 실행 실패: {stderr_msg}"
            logger.error(error_msg)
            raise RepositoryError(error_msg, self.repo_path)
        
        except Exception as e:
            error_msg = f"SVN 명령어 실행 중 예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            raise RepositoryError(error_msg, self.repo_path)