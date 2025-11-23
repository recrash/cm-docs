import git
import os
from typing import List, Tuple, Optional

# 상수 정의
MAX_DIFF_LINES_PER_FILE = 20
COMMIT_MESSAGES_HEADER = "### 커밋 메시지 목록:"
CODE_CHANGES_HEADER = "### 주요 코드 변경 내용 (diff):"
DIFF_TRUNCATION_MESSAGE = "... (내용 생략) ..."
COMMON_ANCESTOR_ERROR = "오류: 공통 조상을 찾을 수 없습니다."
GIT_ERROR_PREFIX = "Git 분석 중 오류 발생: "

# RAG 시스템 노이즈 감소를 위한 필터링 상수
IGNORE_EXTENSIONS = {
    # 이미지/바이너리
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
    '.woff', '.woff2', '.ttf', '.eot',
    '.mp4', '.avi',
    # 빌드/의존성
    '.lock', '-lock.json', '.whl', '.pyc',
    '.o', '.obj', '.dll', '.exe', '.so', '.class',
    # 아카이브
    '.zip', '.tar', '.gz', '.7z', '.rar',
    # 문서/설정
    '.pdf', '.ds_store'
}

IGNORE_DIRS = {
    'node_modules', '.venv', 'venv', 'env',
    '.git', '.svn', '.idea', '.vscode',
    '__pycache__', 'dist', 'build', 'out', 'target',
    '.next', '.nuxt', 'coverage'
}


def _is_valid_file(file_path: str) -> bool:
    """
    파일이 RAG 시스템에 포함될 유효한 파일인지 검사합니다.

    Args:
        file_path: 검사할 파일 경로

    Returns:
        bool: 유효한 파일이면 True, 필터링 대상이면 False
    """
    # Windows 백슬래시를 슬래시로 정규화
    normalized_path = file_path.replace('\\', '/')

    # 확장자 검사
    _, ext = os.path.splitext(normalized_path.lower())
    if ext in IGNORE_EXTENSIONS:
        return False

    # 특수 케이스: package-lock.json, yarn.lock 등
    if any(lock_pattern in normalized_path.lower() for lock_pattern in ['-lock.json', '.lock']):
        return False

    # 디렉토리 경로 검사
    path_parts = normalized_path.split('/')
    for part in path_parts:
        if part in IGNORE_DIRS:
            return False

    return True


def get_merge_base_commits(repo: git.Repo, base_branch: str, head_branch: str) -> Optional[git.Commit]:
    """
    두 브랜치의 공통 조상 커밋을 찾아 반환합니다.
    
    Args:
        repo: Git 저장소 객체
        base_branch: 기준 브랜치명
        head_branch: 대상 브랜치명
    
    Returns:
        공통 조상 커밋 또는 None
    """
    merge_base_commits = repo.merge_base(base_branch, head_branch)
    return merge_base_commits[0] if merge_base_commits else None


def extract_commit_messages(repo: git.Repo, base_commit: git.Commit, head_commit: git.Commit) -> List[str]:
    """
    커밋 메시지 목록을 추출합니다.
    
    Args:
        repo: Git 저장소 객체
        base_commit: 기준 커밋
        head_commit: 대상 커밋
    
    Returns:
        커밋 메시지 문자열 리스트
    """
    commits = list(repo.iter_commits(f'{base_commit.hexsha}..{head_commit.hexsha}'))
    commit_messages = [COMMIT_MESSAGES_HEADER]
    
    for commit in reversed(commits):  # 시간순으로 정렬
        commit_messages.append(f"- {commit.summary}")
    
    return commit_messages


def extract_code_changes(base_commit: git.Commit, head_commit: git.Commit) -> List[str]:
    """
    코드 변경 내용(diff)을 추출합니다.
    필터링 로직을 통해 유효한 파일의 변경사항만 포함합니다.

    Args:
        base_commit: 기준 커밋
        head_commit: 대상 커밋

    Returns:
        코드 변경 내용 문자열 리스트 (필터링 적용)
    """
    diffs = base_commit.diff(head_commit, create_patch=True)
    code_changes = [CODE_CHANGES_HEADER]

    for diff in diffs:
        processed = _process_single_diff(diff)

        # 빈 리스트(필터링된 파일)는 스킵
        if not processed:
            continue

        # 유효한 diff만 추가
        code_changes.extend(processed)

    return code_changes


def _process_single_diff(diff) -> List[str]:
    """
    단일 diff 객체를 처리하여 문자열 리스트로 변환합니다.
    필터링 로직을 적용하여 RAG 시스템의 노이즈를 감소시킵니다.

    Args:
        diff: GitPython diff 객체

    Returns:
        처리된 diff 내용 문자열 리스트 (필터링된 경우 빈 리스트)
    """
    # Step 1: 파일 경로 필터링
    file_path = diff.b_path or diff.a_path
    if not _is_valid_file(file_path):
        return []  # 필터링된 파일은 빈 리스트 반환

    # Step 2: 삭제된 파일 간소화 처리
    if diff.deleted_file:
        return [f"--- 파일: {file_path} (삭제됨) ---"]

    # diff 내용 추출
    try:
        diff_content = diff.diff.decode('utf-8', errors='ignore')
    except Exception:
        return []  # 디코딩 실패 시 빈 리스트 반환

    # Step 3: Minified 파일 감지 (첫 10줄 검사)
    lines = diff_content.splitlines()[:10]
    for line in lines:
        if len(line) > 1000:  # 1000자 이상의 줄 = minified 파일
            return [f"--- 파일: {file_path} (Minified File - 생략됨) ---"]

    # 일반 파일 처리: 기존 로직 유지
    diff_lines = diff_content.splitlines()
    result = [f"--- 파일: {file_path} ---"]

    # 최대 줄 수 제한 적용
    result.extend(diff_lines[:MAX_DIFF_LINES_PER_FILE])

    if len(diff_lines) > MAX_DIFF_LINES_PER_FILE:
        result.append(DIFF_TRUNCATION_MESSAGE)

    return result


def get_git_analysis_text(repo_path: str, base_branch: str = 'origin/develop', head_branch: str = 'HEAD') -> str:
    """
    브랜치의 커밋 메시지, 변경 파일 목록, 전체 코드 diff를 종합하여
    하나의 상세한 텍스트로 반환합니다.
    
    Args:
        repo_path: Git 저장소 경로
        base_branch: 기준 브랜치명 (기본값: 'origin/develop')
        head_branch: 대상 브랜치명 (기본값: 'HEAD')
    
    Returns:
        Git 분석 결과 텍스트
    """
    try:
        repo = git.Repo(repo_path)
        
        # 1. 공통 조상 커밋 찾기
        base_commit = get_merge_base_commits(repo, base_branch, head_branch)
        if not base_commit:
            return COMMON_ANCESTOR_ERROR
        
        head_commit = repo.commit(head_branch)

        # 2. 커밋 메시지 수집
        commit_messages = extract_commit_messages(repo, base_commit, head_commit)

        # 3. 코드 변경점(diff) 수집
        code_changes = extract_code_changes(base_commit, head_commit)

        # 4. 모든 정보를 하나의 텍스트로 결합
        return "\n".join(commit_messages) + "\n\n" + "\n".join(code_changes)

    except git.exc.InvalidGitRepositoryError:
        return "오류: Git 저장소가 아니거나 손상되었습니다."
    except git.exc.NoSuchPathError:
        return "오류: 지정된 경로를 찾을 수 없습니다."
    except git.exc.GitCommandError as e:
        return f"오류: Git 명령 실행 중 문제가 발생했습니다 - {str(e)}"
    except PermissionError:
        return "오류: Git 저장소에 대한 접근 권한이 없습니다."
    except Exception as e:
        return f"{GIT_ERROR_PREFIX}{e}"




# 테스트 및 개발용 직접 실행
if __name__ == "__main__":
    import sys
    
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/recrash/Documents/Workspace/CPMES"
    analysis_text = get_git_analysis_text(repo_path)
    print(analysis_text)