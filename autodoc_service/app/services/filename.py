"""
파일명 관리 서비스

파일명 sanitize 및 중복 방지 기능 제공
"""
import re
from pathlib import Path
from typing import Optional


def sanitize(name: str) -> str:
    """파일명 sanitize 처리
    
    금지문자(\\ / : * ? " < > |)만 '_'로 치환
    대괄호/괄호는 허용
    
    Args:
        name: 원본 파일명
        
    Returns:
        str: sanitized 파일명
    """
    # Windows 파일명 금지 문자들만 치환
    forbidden_chars = r'[\\/:*?"<>|]'
    sanitized = re.sub(forbidden_chars, '_', name)
    
    # 연속된 언더스코어를 하나로 정리
    sanitized = re.sub(r'_{2,}', '_', sanitized)
    
    # 앞뒤 공백 및 점 제거
    sanitized = sanitized.strip(' .')
    
    return sanitized


def unique_path(base_dir: Path, filename: str) -> Path:
    """중복되지 않는 파일 경로 생성
    
    중복 시 _{n} 형식으로 증분하여 고유한 경로 생성
    
    Args:
        base_dir: 기본 디렉터리
        filename: 파일명 (확장자 포함)
        
    Returns:
        Path: 고유한 파일 경로
    """
    sanitized_filename = sanitize(filename)
    
    # 파일명과 확장자 분리
    name_part = Path(sanitized_filename).stem
    suffix_part = Path(sanitized_filename).suffix
    
    # 초기 경로 시도
    target_path = base_dir / sanitized_filename
    
    # 중복 시 증분 번호 추가
    counter = 1
    while target_path.exists():
        new_filename = f"{name_part}_{counter}{suffix_part}"
        target_path = base_dir / new_filename
        counter += 1
        
        # 무한루프 방지
        if counter > 9999:
            raise RuntimeError(f"파일명 중복 해결 실패: {filename}")
    
    return target_path


def generate_word_filename(change_id: str, title: str, writer_short: Optional[str] = None) -> str:
    """Word 변경관리 문서 파일명 생성
    
    형식: [YYMMDD 처리자] 변경관리요청서 {change_id} {title}.docx
    """
    from datetime import datetime
    
    date_str = datetime.now().strftime("%y%m%d")
    writer_part = writer_short or "처리자"
    
    filename = f"[{date_str} {writer_part}] 변경관리요청서 {change_id} {title}.docx"
    return filename


def generate_excel_test_filename(change_id: str, title: str, writer_short: Optional[str] = None) -> str:
    """Excel 테스트 시나리오 파일명 생성
    
    형식: [YYMMDD 처리자] 테스트시나리오 {change_id} {title}.xlsx
    """
    from datetime import datetime
    
    date_str = datetime.now().strftime("%y%m%d")
    writer_part = writer_short or "처리자"
    
    filename = f"[{date_str} {writer_part}] 테스트시나리오 {change_id} {title}.xlsx"
    return filename


def generate_excel_list_filename() -> str:
    """Excel 변경관리 목록 파일명 생성
    
    형식: 변경관리목록_{YYYYMMDD}.xlsx
    """
    from datetime import datetime
    
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"변경관리목록_{date_str}.xlsx"
    return filename