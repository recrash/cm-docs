(*
TestscenarioMaker CLI Helper App
macOS 헬퍼 앱용 AppleScript

이 스크립트는 testscenariomaker:// URL 프로토콜을 통해 호출될 때 실행됩니다.
웹 브라우저의 샌드박스 제약을 우회하여 CLI를 독립적인 프로세스로 실행합니다.

작동 원리:
1. 브라우저가 testscenariomaker:// URL을 클릭
2. macOS가 이 헬퍼 앱을 실행
3. 헬퍼 앱이 내장된 CLI를 백그라운드에서 독립 실행
4. CLI가 샌드박스 제약 없이 네트워크 통신 및 파일 접근 가능
*)

on open location this_URL
	try
		-- 디버깅을 위한 로그 함수
		my log_debug("URL 프로토콜 처리 시작: " & this_URL)
		
		-- URL 유효성 검증
		if not (this_URL starts with "testscenariomaker://") then
			my log_error("올바르지 않은 URL 형식: " & this_URL)
			display dialog "올바르지 않은 URL 형식입니다." & return & "예상 형식: testscenariomaker://path" buttons {"확인"} default button 1 with icon stop
			return
		end if
		
		-- 헬퍼 앱 자신의 경로 획득
		set app_path to path to me
		my log_debug("헬퍼 앱 경로: " & (POSIX path of app_path))
		
		-- 내장된 CLI 실행파일의 전체 경로 생성
		set cli_path to POSIX path of app_path & "Contents/Resources/TestscenarioMaker-CLI"
		my log_debug("CLI 경로: " & cli_path)
		
		-- CLI 파일 존재 여부 확인
		try
			do shell script "test -f " & quoted form of cli_path
		on error
			my log_error("CLI 실행파일을 찾을 수 없습니다: " & cli_path)
			display dialog "CLI 실행파일을 찾을 수 없습니다." & return & "경로: " & cli_path buttons {"확인"} default button 1 with icon stop
			return
		end try
		
		-- CLI 실행 권한 확인
		try
			do shell script "test -x " & quoted form of cli_path
		on error
			my log_error("CLI 실행파일에 실행 권한이 없습니다: " & cli_path)
			display dialog "CLI 실행파일에 실행 권한이 없습니다." & return & "다음 명령어로 권한을 부여하세요:" & return & "chmod +x " & cli_path buttons {"확인"} default button 1 with icon caution
			return
		end try
		
				-- URL을 CLI 인자로 전달하여 Terminal에서 실행 (디버깅 가능)
		-- 터미널 환경과 유사하게 만들기 위해 환경 변수와 작업 디렉토리 설정
		set escaped_cli_path to quoted form of cli_path
		set escaped_url to quoted form of this_URL
		
		-- Terminal에서 실행 (실시간 출력 확인 가능)
		set cli_command to "export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin && export LANG=ko_KR.UTF-8 && echo '=== TestscenarioMaker CLI 실행 ===' && echo 'URL: " & this_URL & "' && echo '' && " & escaped_cli_path & " " & escaped_url
		
		my log_debug("실행할 명령어: " & cli_command)
		
		-- Terminal을 통해 CLI 실행 (포그라운드)
		tell application "Terminal"
			activate
			do script cli_command
		end tell
		
		my log_debug("CLI 실행 완료 - Terminal에서 실행 중")
		
	on error error_message number error_number
		-- 오류 처리 및 로깅
		my log_error("AppleScript 오류 발생: " & error_message & " (코드: " & error_number & ")")
		
		-- 사용자에게 오류 알림 (개발/디버깅 시에만 표시)
		-- 실제 배포 시에는 이 부분을 주석 처리할 수 있습니다
		display dialog "TestscenarioMaker CLI 실행 중 오류가 발생했습니다." & return & return & "오류: " & error_message & return & "코드: " & error_number buttons {"확인"} default button 1 with icon stop
	end try
end open location

-- 디버그 로그 함수
on log_debug(message)
	my write_log("DEBUG", message)
end log_debug

-- 오류 로그 함수  
on log_error(message)
	my write_log("ERROR", message)
	
	-- 콘솔에도 출력 (Console.app에서 확인 가능)
	do shell script "echo '[TestscenarioMaker Helper] ERROR: " & message & "' >> /dev/stderr"
end log_error

-- 로그 파일 작성 함수
on write_log(level, message)
	try
		-- 사용자 임시 디렉토리에 로그 파일 생성
		set log_file to (path to temporary items folder as text) & "TestscenarioMaker_Helper.log"
		set log_path to POSIX path of log_file
		
		-- 현재 시간 가져오기
		set current_date to (current date) as string
		
		-- 로그 메시지 구성
		set log_entry to "[" & current_date & "] " & level & ": " & message & return
		
		-- 로그 파일에 추가 (파일이 없으면 생성)
		do shell script "echo " & quoted form of log_entry & " >> " & quoted form of log_path
		
	on error
		-- 로그 작성 실패는 무시 (무한 루프 방지)
	end try
end write_log

-- 앱이 일반적인 방법으로 실행되었을 때의 처리
on run
	display dialog "TestscenarioMaker CLI Helper App" & return & return & "이 앱은 웹 브라우저에서 testscenariomaker:// 링크를 통해 자동으로 실행됩니다." & return & return & "직접 실행하실 필요는 없습니다." buttons {"확인"} default button 1 with icon note
end run