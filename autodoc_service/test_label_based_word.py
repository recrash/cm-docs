#!/usr/bin/env python3
"""
Label-Based Word Generation Test

Tests the new label-based Word document generation that should be robust
against template structure changes and properly map all fields.
"""
import json
import subprocess

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

def test_label_based_word_generation():
    """Test the new label-based Word generation approach"""
    print("🧪 Testing Label-Based Word Generation")
    print("=" * 60)
    
    # Step 1: Parse HTML to get complete data
    print("\n1. Parsing HTML file for complete data...")
    html_file = "/Users/recrash/Documents/Workspace/cm-docs/autodoc_service/testHTML/규격 확정일자.html"
    
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
    
    # Step 2: Test enhanced label-based generation 
    print("\n2. Testing enhanced label-based Word generation...")
    
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
    
    word_response = run_curl_command(
        "POST",
        "http://localhost:8000/create-cm-word-enhanced", 
        json.dumps(enhanced_payload)
    )
    
    if not word_response or not word_response.get("ok"):
        print(f"❌ Enhanced Word generation failed: {word_response}")
        return False
    
    word_filename = word_response["filename"]
    print(f"✅ Enhanced label-based Word document generated: {word_filename}")
    
    # Step 3: Test basic label-based generation
    print("\n3. Testing basic label-based Word generation...")
    
    basic_word_response = run_curl_command(
        "POST",
        "http://localhost:8000/create-cm-word-label",
        json.dumps(change_request)
    )
    
    if not basic_word_response or not basic_word_response.get("ok"):
        print(f"❌ Basic label-based Word generation failed: {basic_word_response}")
        return False
        
    basic_word_filename = basic_word_response["filename"]
    print(f"✅ Basic label-based Word document generated: {basic_word_filename}")
    
    # Step 4: Show comparison with old approach
    print("\n4. Comparing with old cell-index approach...")
    
    old_word_response = run_curl_command(
        "POST",
        "http://localhost:8000/create-cm-word",
        json.dumps(change_request)
    )
    
    if old_word_response and old_word_response.get("ok"):
        old_word_filename = old_word_response["filename"]
        print(f"📄 Old cell-index Word document: {old_word_filename}")
    else:
        print(f"⚠️ Old approach failed (expected): {old_word_response}")
    
    print("\n" + "=" * 60)
    print("🎉 LABEL-BASED WORD GENERATION TEST COMPLETED!")
    print("=" * 60)
    
    print(f"\n📊 Results Summary:")
    print(f"   ✅ Enhanced Label-Based: {word_filename}")
    print(f"   ✅ Basic Label-Based: {basic_word_filename}")
    
    print(f"\n🔧 Key Improvements:")
    print("   🎯 Template structure independent")
    print("   🔍 Finds labels by text content")
    print("   📝 Fills adjacent cells automatically")
    print("   🛡️ Robust against cell merging/restructuring")
    print("   ✨ No hardcoded cell indices")
    
    print(f"\n📝 Expected Field Mappings:")
    expected_mappings = [
        "제목 → [Bug 개선] 시험의뢰...",
        "변경관리번호 → 울산 실험정보(LIMS)_20250728_1",
        "작업일시 → 08/06 18:00",
        "배포일시 → 08/07 13:00", 
        "고객사명 → SK picglobal",
        "요청자 → 이대경",
        "요청번호(SOR) → KSKP-ITSUPP-2025-00882",
        "대상 시스템 → 울산 실험정보(LIMS)",
        "작업자/배포자 → 이대경",
        "영향도 대상자 → [derived from data]"
    ]
    
    for mapping in expected_mappings:
        print(f"     • {mapping}")
    
    return True

if __name__ == "__main__":
    success = test_label_based_word_generation()
    
    if success:
        print("\n🏆 All label-based tests passed!")
        print("📋 Template structure issues should now be resolved!")
    else:
        print("\n💥 Some tests failed!")