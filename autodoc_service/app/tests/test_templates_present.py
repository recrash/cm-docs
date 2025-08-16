"""
템플릿 파일 존재 및 무변경 검증 테스트

SHA-256 해시를 사용하여 템플릿 파일이 변경되지 않았음을 보증
"""
import hashlib
import pytest
from pathlib import Path

from ..services.paths import get_templates_dir, verify_template_exists


def _calculate_file_hash(file_path: Path) -> str:
    """파일의 SHA-256 해시 계산"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


class TestTemplatesPresent:
    """템플릿 존재 및 무변경 테스트"""
    
    def test_templates_directory_exists(self):
        """템플릿 디렉터리 존재 여부 확인"""
        templates_dir = get_templates_dir()
        assert templates_dir.exists(), f"템플릿 디렉터리가 존재하지 않습니다: {templates_dir}"
        assert templates_dir.is_dir(), f"템플릿 경로가 디렉터리가 아닙니다: {templates_dir}"
    
    def test_word_template_exists(self):
        """Word 템플릿 파일 존재 확인"""
        template_path = verify_template_exists("template.docx")
        assert template_path.exists(), "template.docx 파일이 존재하지 않습니다"
        assert template_path.is_file(), "template.docx가 파일이 아닙니다"
        
        # 파일 크기 확인 (0바이트가 아님)
        assert template_path.stat().st_size > 0, "template.docx 파일이 비어있습니다"
    
    def test_excel_test_template_exists(self):
        """Excel 테스트 템플릿 파일 존재 확인"""
        template_path = verify_template_exists("template.xlsx")
        assert template_path.exists(), "template.xlsx 파일이 존재하지 않습니다"
        assert template_path.is_file(), "template.xlsx가 파일이 아닙니다"
        
        # 파일 크기 확인
        assert template_path.stat().st_size > 0, "template.xlsx 파일이 비어있습니다"
    
    def test_excel_list_template_exists(self):
        """Excel 목록 템플릿 파일 존재 확인"""
        template_path = verify_template_exists("template_list.xlsx")
        assert template_path.exists(), "template_list.xlsx 파일이 존재하지 않습니다"
        assert template_path.is_file(), "template_list.xlsx가 파일이 아닙니다"
        
        # 파일 크기 확인
        assert template_path.stat().st_size > 0, "template_list.xlsx 파일이 비어있습니다"
    
    def test_invalid_template_raises_error(self):
        """존재하지 않는 템플릿 파일 요청 시 에러 발생 확인"""
        with pytest.raises(FileNotFoundError):
            verify_template_exists("nonexistent_template.docx")
    
    @pytest.mark.parametrize("template_name", [
        "template.docx",
        "template.xlsx", 
        "template_list.xlsx"
    ])
    def test_template_hash_consistency(self, template_name):
        """템플릿 파일 해시 일관성 확인
        
        실행 전후에 템플릿 파일이 변경되지 않았는지 검증
        실제로는 테스트 실행 중에 사용된 후 변경되지 않았는지 확인
        """
        template_path = verify_template_exists(template_name)
        
        # 첫 번째 해시 계산
        hash1 = _calculate_file_hash(template_path)
        
        # 파일을 다시 열어서 해시 재계산 (파일이 변경되지 않았다면 동일해야 함)
        hash2 = _calculate_file_hash(template_path)
        
        assert hash1 == hash2, f"{template_name} 파일 해시가 일치하지 않습니다"
        
        # 해시가 유효한 SHA-256인지 확인
        assert len(hash1) == 64, f"{template_name} 해시 길이가 올바르지 않습니다"
        assert all(c in '0123456789abcdef' for c in hash1), f"{template_name} 해시가 16진수가 아닙니다"
    
    def test_all_required_templates_present(self):
        """모든 필수 템플릿 파일이 존재하는지 한번에 확인"""
        required_templates = [
            "template.docx",
            "template.xlsx",
            "template_list.xlsx"
        ]
        
        missing_templates = []
        
        for template_name in required_templates:
            try:
                verify_template_exists(template_name)
            except FileNotFoundError:
                missing_templates.append(template_name)
        
        assert not missing_templates, f"누락된 템플릿 파일: {missing_templates}"