"""
IT지원의뢰서 HTML 파서 테스트

픽스처 데이터와 정확히 일치하는지 검증
파생 규칙 검증 포함
"""
import json
import pytest
from pathlib import Path

from ..parsers.itsupp_html_parser import parse_itsupp_html


class TestItsuppHtmlParser:
    """IT지원의뢰서 HTML 파서 테스트"""
    
    @pytest.fixture
    def sample_html(self):
        """테스트용 HTML 픽스처 로드"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        html_file = fixtures_dir / "규격 확정일자.html"
        
        assert html_file.exists(), "테스트용 HTML 파일이 존재하지 않습니다"
        
        with open(html_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    @pytest.fixture
    def expected_json(self):
        """기대되는 JSON 결과 로드"""
        fixtures_dir = Path(__file__).parent / "fixtures"
        json_file = fixtures_dir / "itsupp_sample.json"
        
        assert json_file.exists(), "기대 결과 JSON 파일이 존재하지 않습니다"
        
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def test_parse_html_basic_fields(self, sample_html, expected_json):
        """기본 필드 파싱 테스트"""
        result = parse_itsupp_html(sample_html)
        
        # 기본 필드들 확인
        basic_fields = [
            "문서번호", "제목", "신청자", "요청자", "요청부서",
            "요청시스템_원본", "요청시스템", "변경관리번호"
        ]
        
        for field in basic_fields:
            assert field in result, f"필드 '{field}'가 결과에 없습니다"
            assert result[field] == expected_json[field], (
                f"필드 '{field}' 값이 일치하지 않습니다. "
                f"실제: '{result[field]}', 기대: '{expected_json[field]}'"
            )
    
    def test_parse_html_derived_fields(self, sample_html, expected_json):
        """파생 필드 파싱 테스트"""
        result = parse_itsupp_html(sample_html)
        
        # 파생 필드들 확인
        derived_fields = [
            "시스템", "시스템_약칭", "처리자_약칭", 
            "작성일", "배포일정", "작업일시", "배포일시",
            "DB변동유무", "DB변동유무_사유"
        ]
        
        for field in derived_fields:
            assert field in result, f"파생 필드 '{field}'가 결과에 없습니다"
            assert result[field] == expected_json[field], (
                f"파생 필드 '{field}' 값이 일치하지 않습니다. "
                f"실제: '{result[field]}', 기대: '{expected_json[field]}'"
            )
    
    def test_parse_html_multiline_fields(self, sample_html, expected_json):
        """멀티라인 필드 파싱 테스트"""
        result = parse_itsupp_html(sample_html)
        
        multiline_fields = ["의뢰내용", "요구사항 상세분석", "검토의견"]
        
        for field in multiline_fields:
            assert field in result, f"멀티라인 필드 '{field}'가 결과에 없습니다"
            
            # 공백 정규화를 고려하여 비교
            actual = result[field].strip()
            expected = expected_json[field].strip()
            
            assert actual == expected, (
                f"멀티라인 필드 '{field}' 값이 일치하지 않습니다.\n"
                f"실제: '{actual}'\n기대: '{expected}'"
            )
    
    def test_system_derivation_rule(self, sample_html):
        """시스템명 파생 규칙 검증"""
        result = parse_itsupp_html(sample_html)
        
        # 변경관리번호에서 뒤 11자 제거하여 시스템명 추출
        change_id = result["변경관리번호"]
        expected_system = change_id[:-11] if len(change_id) > 11 else change_id
        
        assert result["시스템"] == expected_system, (
            f"시스템명 파생 규칙 오류: 변경관리번호 '{change_id}'에서 "
            f"시스템명 '{result['시스템']}'이 도출되었지만, '{expected_system}'이 기대됨"
        )
    
    def test_work_deploy_time_derivation(self, sample_html):
        """작업일시/배포일시 파생 규칙 검증"""
        result = parse_itsupp_html(sample_html)
        
        # 검토의견에서 파생된 작성일/배포일정이 있다면
        if "작성일" in result and result["작성일"]:
            expected_work_time = f"{result['작성일']} 18:00"
            assert result["작업일시"] == expected_work_time, (
                f"작업일시 파생 규칙 오류: 작성일 '{result['작성일']}'에서 "
                f"'{expected_work_time}'이 기대되지만 '{result['작업일시']}'가 도출됨"
            )
        
        if "배포일정" in result and result["배포일정"]:
            expected_deploy_time = f"{result['배포일정']} 13:00"
            assert result["배포일시"] == expected_deploy_time, (
                f"배포일시 파생 규칙 오류: 배포일정 '{result['배포일정']}'에서 "
                f"'{expected_deploy_time}'이 기대되지만 '{result['배포일시']}'가 도출됨"
            )
    
    def test_requester_department_split(self, sample_html):
        """요청자/요청부서 분할 규칙 검증"""
        result = parse_itsupp_html(sample_html)
        
        if "신청자" in result and result["신청자"]:
            full_name = result["신청자"]
            parts = full_name.split('/')
            
            if len(parts) >= 2:
                expected_requester = parts[0].strip()
                expected_dept = parts[-1].strip()
                
                assert result["요청자"] == expected_requester, (
                    f"요청자 분할 오류: '{full_name}'에서 '{expected_requester}'가 "
                    f"기대되지만 '{result['요청자']}'가 도출됨"
                )
                
                assert result["요청부서"] == expected_dept, (
                    f"요청부서 분할 오류: '{full_name}'에서 '{expected_dept}'가 "
                    f"기대되지만 '{result['요청부서']}'가 도출됨"
                )
    
    def test_test_results_parsing(self, sample_html, expected_json):
        """테스트 결과 파싱 검증"""
        result = parse_itsupp_html(sample_html)
        
        test_fields = ["테스트일자", "테스트결과", "테스트완료여부"]
        
        for field in test_fields:
            if field in expected_json:
                assert field in result, f"테스트 결과 필드 '{field}'가 결과에 없습니다"
                assert result[field] == expected_json[field], (
                    f"테스트 결과 필드 '{field}' 값이 일치하지 않습니다. "
                    f"실제: '{result[field]}', 기대: '{expected_json[field]}'"
                )
    
    def test_draft_date_parsing(self, sample_html, expected_json):
        """기안일 파싱 검증"""
        result = parse_itsupp_html(sample_html)
        
        if "기안일" in expected_json:
            assert "기안일" in result, "기안일이 파싱되지 않았습니다"
            assert "기안일_가공" in result, "기안일_가공이 파싱되지 않았습니다"
            
            assert result["기안일"] == expected_json["기안일"], (
                f"기안일이 일치하지 않습니다. "
                f"실제: '{result['기안일']}', 기대: '{expected_json['기안일']}'"
            )
            
            assert result["기안일_가공"] == expected_json["기안일_가공"], (
                f"기안일_가공이 일치하지 않습니다. "
                f"실제: '{result['기안일_가공']}', 기대: '{expected_json['기안일_가공']}'"
            )
    
    def test_empty_html_handling(self):
        """빈 HTML 처리 테스트"""
        result = parse_itsupp_html("")
        assert isinstance(result, dict), "빈 HTML에 대해 dict를 반환해야 합니다"
        
        # 빈 HTML이어도 dict는 반환되어야 함 (빈 dict일 수 있음)
    
    def test_invalid_html_handling(self):
        """잘못된 HTML 처리 테스트"""
        invalid_html = "<html><body><p>잘못된 구조</p></body></html>"
        
        # 에러가 발생하지 않고 dict를 반환해야 함
        result = parse_itsupp_html(invalid_html)
        assert isinstance(result, dict), "잘못된 HTML에 대해서도 dict를 반환해야 합니다"
    
    def test_complete_field_coverage(self, sample_html, expected_json):
        """모든 기대 필드가 파싱되는지 확인"""
        result = parse_itsupp_html(sample_html)
        
        missing_fields = []
        for expected_field in expected_json.keys():
            if expected_field not in result:
                missing_fields.append(expected_field)
        
        assert not missing_fields, f"파싱되지 않은 필드들: {missing_fields}"
        
        # 추가로 파싱된 필드도 확인 (디버깅용)
        extra_fields = [field for field in result.keys() if field not in expected_json]
        if extra_fields:
            print(f"추가로 파싱된 필드들: {extra_fields}")  # 정보 출력용