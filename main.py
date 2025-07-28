import json
import re
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel

def main():
    model_name = "qwen3:14b"
    repo_path = "/Users/recrash/Documents/Workspace/CPMES"

    print("1. Git 변경 내역을 상세 분석합니다...")
    git_analysis = get_git_analysis_text(repo_path)
    
    print("\nSTEP 2: 단일 LLM 호출로 모든 정보를 생성합니다.")
    
    final_prompt = f"""너는 주어진 Git 변경 내역을 분석하여, 완벽한 테스트 시나리오 문서를 생성하는 전문가다.

**지시사항:**
1. 먼저, 주어진 '분석할 Git 변경 내역'을 바탕으로 최종 JSON 결과물을 만들기 위한 너의 생각 과정을 `<thinking>` 태그 안에 단계별로 서술해라. 모든 생각은 한국어로 작성한다.
2. 생각 과정이 끝나면, 그 생각을 바탕으로 최종 결과물을 `<json>` 태그 안에 완벽한 JSON 객체로 생성해라.
3. 최종 JSON 객체의 모든 문자열 값은 **반드시 한국어로** 작성해야 하며, 어떤 필드도 비워두어서는 안 된다.

### 분석할 Git 변경 내역:
{git_analysis}

### 최종 출력 형식:
<thinking>
1. Git 변경 내역 분석: 핵심 변경 사항 파악.
2. 개요 및 제목 구상: 전체 시나리오를 대표할 'Scenario Description'과 'Test Scenario Name' 구상.
3. 테스트 케이스 3개 구상: 각 변경 사항을 검증할 구체적인 ID, 절차, 사전조건 등을 작성.
4. 최종 JSON 생성: 위 내용을 종합하여 최종 JSON 구조에 맞게 내용 채우기.
</thinking>
<json>
{{
  "Scenario Description": "사용자 관점에서 이 테스트 전체의 목적을 요약한 설명.",
  "Test Scenario Name": "테스트 시나리오 전체를 대표하는 명확한 제목.",
  "Test Cases": [
    {{
      "ID": "CMP_MES_001",
      "절차": "1. 첫 번째 절차.\\n2. 두 번째 절차.",
      "사전조건": "테스트를 위한 사전 조건.",
      "데이터": "테스트에 사용될 특정 데이터.",
      "예상결과": "시스템의 정상적인 반응.",
      "종류": "단위 또는 통합"
    }},
    {{
      "ID": "CMP_MES_002",
      "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..."
    }},
    {{
      "ID": "CMP_MES_003",
      "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..."
    }}
  ]
}}
</json>
"""
    
    raw_response = call_ollama_llm(final_prompt, model=model_name, timeout=600)

    if not raw_response:
        print("오류: LLM으로부터 응답을 받지 못했습니다.")
        return
        
    try:
        json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
        if not json_match:
            raise ValueError("LLM 응답에서 <json> 블록을 찾을 수 없습니다.")
        
        json_string = json_match.group(1).strip()
        result_json = json.loads(json_string)
        print("✅ LLM이 생성한 전체 시나리오 파싱 성공!")
        
        save_results_to_excel(result_json)
        
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   -> 최종 결과 파싱 실패! 오류: {e}")
        print(f"   -> LLM 원본 응답: {raw_response}")

if __name__ == "__main__":
    main()