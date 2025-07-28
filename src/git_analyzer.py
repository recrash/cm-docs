import git

def get_git_analysis_text(repo_path, base_branch='origin/develop', head_branch='HEAD'):
    """
    브랜치의 커밋 메시지, 변경 파일 목록, 전체 코드 diff를 종합하여
    하나의 상세한 텍스트로 반환합니다.
    """
    try:
        repo = git.Repo(repo_path)
        
        # 1. 공통 조상 커밋 찾기
        merge_base_commits = repo.merge_base(base_branch, head_branch)
        if not merge_base_commits:
            return "오류: 공통 조상을 찾을 수 없습니다."
        base_commit = merge_base_commits[0]
        head_commit = repo.commit(head_branch)

        # 2. 해당 브랜치의 커밋 메시지 수집
        commits = list(repo.iter_commits(f'{base_commit.hexsha}..{head_commit.hexsha}'))
        commit_messages = ["### 커밋 메시지 목록:"]
        for commit in reversed(commits):
            commit_messages.append(f"- {commit.summary}")

        # 3. 전체 코드 변경점(diff) 수집
        # create_patch=True로 설정해야 diff 내용이 포함됨
        diffs = base_commit.diff(head_commit, create_patch=True)
        code_changes = ["### 주요 코드 변경 내용 (diff):"]
        for diff in diffs:
            # diff 내용이 너무 길어지는 것을 방지하기 위해 상위 20줄만 예시로 포함
            diff_content = diff.diff.decode('utf-8', errors='ignore').splitlines()
            code_changes.append(f"--- 파일: {diff.a_path} ---")
            code_changes.extend(diff_content[:20]) # 각 파일당 최대 20줄
            if len(diff_content) > 20:
                code_changes.append("... (내용 생략) ...")

        # 4. 모든 정보를 하나의 텍스트로 결합
        final_text = "\n".join(commit_messages) + "\n\n" + "\n".join(code_changes)
        return final_text

    except Exception as e:
        return f"Git 분석 중 오류 발생: {e}"

# main.py에서 직접 호출하므로 이 부분은 테스트용
if __name__ == "__main__":
    repo_path = "/Users/recrash/Documents/Workspace/CPMES" # 경로 확인 필요
    analysis_text = get_git_analysis_text(repo_path)
    print(analysis_text)