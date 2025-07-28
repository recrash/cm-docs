# src/prompt_loader.py
def load_prompt(path="prompts/final_prompt.txt"):
    """텍스트 파일에서 프롬프트 템플릿을 읽어옵니다."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"오류: 프롬프트 파일('{path}')을 찾을 수 없습니다.")
        return None

def create_final_prompt(git_analysis):
    """
    프롬프트 템플릿을 로드하고, git_analysis 데이터로 완성합니다.
    """
    template = load_prompt()
    if template:
        return template.format(git_analysis=git_analysis)
    return None