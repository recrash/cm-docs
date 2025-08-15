#!/usr/bin/env python3
"""
Enhanced Word Document Generation Test

Tests the new centralized mapping layer and enhanced Word generation.
"""
import json
import requests

# Raw parsed data from HTML (this would normally come from /parse-html endpoint)
raw_data = {
    "제목": "[Bug 개선] 시험의뢰 시 규격 확정일자에 최신 버전이 자동 매핑되도록 시스템 구조 개선",
    "문서번호": "KSKP-ITSUPP-2025-00882",
    "신청자": "이대경/Manager/IT운영팀/SK picglobal",
    "요청자": "이대경",
    "요청부서": "SK picglobal",
    "요청시스템_원본": "생산파트(MES) / 울산 실험정보(LIMS)",
    "요청시스템": "울산 실험정보(LIMS)",
    "변경관리번호": "울산 실험정보(LIMS)_20250728_1",
    "시스템": "LIMS-001",
    "시스템_약칭": "LIMS",
    "의뢰내용": "현재 구성된 시스템 구조 상 [규격]의 확정일자가 하루당 1개의 verison이 매핑되지 않으면 오래된 version이 시험의뢰되도록 설계되어 있음 -.이 부분을 최신 Version의 시험의뢰가 되도록 설계 변경요청사항",
    "요청사유": "시험의뢰 시 규격 확정일자에 최신 버전이 자동 매핑되도록 시스템 구조 개선이 필요",
    "완료희망일": "2025-08-08",
    "처리자": "이대경/Manager/생산운영",
    "처리자_약칭": "이대경",
    "개발등급": "5등급 - 3~5M/D",
    "요구사항 상세분석": "하나의 채취장소에 대해 규격의 확정일자가 동일하고 VERSION이 상이한 기준정보가 발생된다면 시험의뢰 시 시험항목의 LIST는 최신 VERSION의 규격이 보이고 있으나 결과입력에서 확인할 때 오래된 버전이 보이는 현상에 대한 정상화 작업 (현재 시스템 사용은 확정일자 1일 당 VERSION 1개만 사용되도록 구성됨)",
    "작업예상일자": "2025-08-04 ~ 2025-08-08",
    "검토의견": "1. 개발 일정(작업 일정) : 08/06 2. 배포 일정(전달/조치 일정) : 08/07 3. 현업과 배포일정(전달/조치 일정) 확인 유무 : N/A 4. DB변동유무: N 5. 일정 Rolling : 업무 현황에 따라 한 주 연기할 수 있음",
    "작성일": "08/06",
    "작업일시": "08/06 18:00",
    "배포일정": "08/07",
    "배포일시": "08/07 13:00",
    "DB변동유무": "N",
    "DB변동유무_사유": "",
    "테스트일자": "2025-08-06 13:06:59",
    "테스트결과": "개발서버 테스트 완료",
    "테스트완료여부": "완료",
    "기안일": "2025-07-28 21:55:44",
    "기안일_가공": "2025/07/28",
    "배포자": "이대경",
    "대무자": "김용진"
}

# ChangeRequest data (basic structure required by the API)
change_request = {
    "change_id": "울산 실험정보(LIMS)_20250728_1",
    "title": "[Bug 개선] 시험의뢰 시 규격 확정일자에 최신 버전이 자동 매핑되도록 시스템 구조 개선",
    "system": "울산 실험정보(LIMS)",
    "requester": "이대경",
    "writer_short": "이대경"
}

# Test the enhanced Word generation
def test_enhanced_word_generation():
    url = "http://localhost:8000/create-cm-word-enhanced"
    
    payload = {
        "raw_data": raw_data,
        "change_request": change_request
    }
    
    print("Testing enhanced Word generation with centralized mapping...")
    print(f"URL: {url}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Generated file: {result['filename']}")
            return result['filename']
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

if __name__ == "__main__":
    filename = test_enhanced_word_generation()
    
    if filename:
        print(f"\n📄 Word document generated successfully: {filename}")
        print("\nKey improvements:")
        print("- 고객사: Auto-derived from 요청부서 (SK picglobal)")
        print("- 작업자-배포자: Combined from 처리자_약칭/배포자 (이대경 / 이대경)")
        print("- 목적-개선내용: Used 요구사항 상세분석 as fallback")
        print("- 영향도_대상자: Default policy value (- UI 수정)")
        print("- 작성일: Used parser value (08/06) instead of today")
    else:
        print("\n❌ Test failed!")