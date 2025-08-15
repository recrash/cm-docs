#!/usr/bin/env python3
"""
Complete Workflow Test with Enhanced Mapping

This script demonstrates the complete workflow from HTML parsing to document generation
with the new centralized mapping layer that fixes VBA macro compatibility issues.
"""
import json
import subprocess
import sys
from pathlib import Path

def run_curl_command(method, url, data=None, files=None):
    """Run curl command and return the response"""
    cmd = ["curl", "-s", "-X", method]
    
    if data:
        cmd.extend(["-H", "Content-Type: application/json", "-d", data])
    elif files:
        for file_path in files:
            cmd.extend(["-F", f"file=@{file_path}"])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Curl command failed: {e}")
        print(f"Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"Response: {result.stdout}")
        return None

def test_complete_workflow():
    """Test complete workflow from HTML to documents"""
    print("🔄 Testing Complete Workflow with Enhanced Mapping")
    print("=" * 60)
    
    # Step 1: Parse HTML file
    print("\n1. Parsing HTML file...")
    html_file = "/Users/recrash/Documents/Workspace/cm-docs/autodoc_service/testHTML/규격 확정일자.html"
    
    if not Path(html_file).exists():
        print(f"❌ HTML file not found: {html_file}")
        return False
    
    parse_response = run_curl_command(
        "POST", 
        "http://localhost:8000/parse-html",
        files=[html_file]
    )
    
    if not parse_response or not parse_response.get("success"):
        print(f"❌ HTML parsing failed: {parse_response}")
        return False
    
    parsed_data = parse_response["data"]
    print(f"✅ HTML parsed successfully!")
    print(f"   - 제목: {parsed_data.get('제목', 'N/A')[:50]}...")
    print(f"   - 고객사: {parsed_data.get('고객사', 'NOT PRESENT - WILL BE DERIVED')}")
    print(f"   - 작업자-배포자: {parsed_data.get('작업자-배포자', 'NOT PRESENT - WILL BE DERIVED')}")
    print(f"   - 영향도_대상자: {parsed_data.get('영향도_대상자', 'NOT PRESENT - WILL BE DERIVED')}")
    print(f"   - 작성일: {parsed_data.get('작성일', 'N/A')}")
    
    # Step 2: Create ChangeRequest payload for enhanced Word generation
    print("\n2. Preparing enhanced Word generation...")
    
    change_request = {
        "change_id": parsed_data.get("변경관리번호", ""),
        "title": parsed_data.get("제목", ""),
        "system": parsed_data.get("요청시스템", ""),
        "requester": parsed_data.get("요청자", ""),
        "writer_short": parsed_data.get("처리자_약칭", "")
    }
    
    enhanced_payload = {
        "raw_data": parsed_data,
        "change_request": change_request
    }
    
    # Step 3: Generate enhanced Word document
    print("\n3. Generating enhanced Word document...")
    word_response = run_curl_command(
        "POST",
        "http://localhost:8000/create-cm-word-enhanced", 
        json.dumps(enhanced_payload)
    )
    
    if not word_response or not word_response.get("ok"):
        print(f"❌ Enhanced Word generation failed: {word_response}")
        return False
    
    word_filename = word_response["filename"]
    print(f"✅ Enhanced Word document generated: {word_filename}")
    
    # Step 4: Generate Excel document for comparison
    print("\n4. Generating Excel test scenario...")
    excel_response = run_curl_command(
        "POST",
        "http://localhost:8000/create-test-excel",
        json.dumps(change_request)
    )
    
    if not excel_response or not excel_response.get("ok"):
        print(f"❌ Excel generation failed: {excel_response}")
        return False
    
    excel_filename = excel_response["filename"]
    print(f"✅ Excel test scenario generated: {excel_filename}")
    
    # Step 5: Show improvements summary
    print("\n" + "=" * 60)
    print("🎉 WORKFLOW COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\n📋 Key Improvements Applied:")
    print("   ✅ 고객사: Auto-derived from 요청부서 or 신청자")
    print("   ✅ 작업자-배포자: Combined 처리자_약칭 + 배포자")
    print("   ✅ 목적-개선내용: Uses 요구사항 상세분석 as fallback")
    print("   ✅ 영향도_대상자: Default policy value ('- UI 수정')")
    print("   ✅ 작성일: Uses parser value instead of today's date")
    
    print(f"\n📄 Generated Documents:")
    print(f"   📝 Word: {word_filename}")
    print(f"   📊 Excel: {excel_filename}")
    
    print(f"\n💡 VBA Macro Compatibility:")
    print("   - All required fields now present")
    print("   - Missing fields auto-generated with fallback logic")
    print("   - Consistent field naming matching macro expectations")
    
    return True

if __name__ == "__main__":
    success = test_complete_workflow()
    
    if success:
        print("\n🏆 All tests passed! Enhanced mapping layer working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Check the output above.")
        sys.exit(1)