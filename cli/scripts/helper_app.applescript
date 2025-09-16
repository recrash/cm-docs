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

		-- 중복 프로세스 체크 및 정리 (macOS 특화 로직)
		my log_debug("기존 TestscenarioMaker 프로세스 체크 중...")
		my cleanup_existing_processes()

		-- 세션 ID 추출 (URL에서)
		set session_id to my extract_session_id(this_URL)
		if session_id is not "" then
			my log_debug("감지된 세션 ID: " & session_id)
			-- 세션별 프로세스 정리
			my cleanup_session_processes(session_id)
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

-- 기존 TestscenarioMaker 프로세스 정리 함수
on cleanup_existing_processes()
	try
		my log_debug("모든 TestscenarioMaker 관련 프로세스 정리 시작")

		-- TestscenarioMaker-CLI 프로세스 찾기 및 정리
		set cli_processes to do shell script "pgrep -f 'TestscenarioMaker-CLI' || true"
		if cli_processes is not "" then
			my log_debug("발견된 CLI 프로세스: " & cli_processes)
			do shell script "pkill -f 'TestscenarioMaker-CLI' || true"
			my log_debug("기존 CLI 프로세스들을 정리했습니다")
		else
			my log_debug("실행 중인 CLI 프로세스가 없습니다")
		end if

		-- ts-cli 프로세스 찾기 및 정리 (Python으로 실행된 경우)
		set python_processes to do shell script "pgrep -f 'ts-cli' || true"
		if python_processes is not "" then
			my log_debug("발견된 Python CLI 프로세스: " & python_processes)
			do shell script "pkill -f 'ts-cli' || true"
			my log_debug("기존 Python CLI 프로세스들을 정리했습니다")
		else
			my log_debug("실행 중인 Python CLI 프로세스가 없습니다")
		end if

	on error error_message
		my log_error("프로세스 정리 중 오류: " & error_message)
	end try
end cleanup_existing_processes

-- URL에서 세션 ID 추출 함수
on extract_session_id(url_string)
	try
		my log_debug("세션 ID 추출 시도: " & url_string)

		-- sessionId= 파라미터 찾기
		set session_pattern to "sessionId="
		set session_start to offset of session_pattern in url_string

		if session_start > 0 then
			-- sessionId= 다음부터 추출
			set session_value_start to session_start + (length of session_pattern)
			set remaining_url to text session_value_start thru -1 of url_string

			-- & 문자로 구분되는 다음 파라미터까지 또는 끝까지
			set ampersand_pos to offset of "&" in remaining_url
			if ampersand_pos > 0 then
				set session_id to text 1 thru (ampersand_pos - 1) of remaining_url
			else
				set session_id to remaining_url
			end if

			my log_debug("추출된 세션 ID: " & session_id)
			return session_id
		else
			my log_debug("URL에서 sessionId 파라미터를 찾을 수 없습니다")
			return ""
		end if

	on error error_message
		my log_error("세션 ID 추출 중 오류: " & error_message)
		return ""
	end try
end extract_session_id

-- 특정 세션 ID와 관련된 프로세스 정리 함수
on cleanup_session_processes(session_id)
	try
		my log_debug("세션 " & session_id & "와 관련된 프로세스 정리 시작")

		-- 세션 ID가 포함된 프로세스 찾기 (명령줄 인자에서)
		set session_processes to do shell script "pgrep -f '" & session_id & "' || true"
		if session_processes is not "" then
			my log_debug("발견된 세션 관련 프로세스: " & session_processes)

			-- 해당 프로세스들에게 SIGTERM 신호 전송 (우아한 종료)
			do shell script "pkill -TERM -f '" & session_id & "' || true"
			my log_debug("세션 관련 프로세스들에게 종료 신호를 전송했습니다")

			-- 3초 대기 후 강제 종료 확인
			delay 3
			set remaining_processes to do shell script "pgrep -f '" & session_id & "' || true"
			if remaining_processes is not "" then
				my log_debug("일부 프로세스가 여전히 실행 중입니다. 강제 종료를 시도합니다.")
				do shell script "pkill -KILL -f '" & session_id & "' || true"
				my log_debug("세션 관련 프로세스들을 강제 종료했습니다")
			end if
		else
			my log_debug("해당 세션과 관련된 실행 중인 프로세스가 없습니다")
		end if

	on error error_message
		my log_error("세션 프로세스 정리 중 오류: " & error_message)
	end try
end cleanup_session_processes

-- 앱이 일반적인 방법으로 실행되었을 때의 처리
on run
	display dialog "TestscenarioMaker CLI Helper App" & return & return & "이 앱은 웹 브라우저에서 testscenariomaker:// 링크를 통해 자동으로 실행됩니다." & return & return & "직접 실행하실 필요는 없습니다." buttons {"확인"} default button 1 with icon note
end run