"""
설정 로더 모듈

configparser를 사용하여 INI 형식의 설정 파일을 읽고 관리합니다.
"""

import os
import logging
from pathlib import Path
from configparser import ConfigParser
from typing import Dict, Any, Optional, Union


logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    설정 파일 로더 클래스

    INI 형식의 설정 파일을 읽고 설정값을 제공합니다.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        ConfigLoader 초기화

        Args:
            config_path: 설정 파일 경로 (None이면 기본 경로 사용)
        """
        self.config = ConfigParser()
        self.config_path = self._resolve_config_path(config_path)
        self._load_config()

    def _resolve_config_path(self, config_path: Optional[Path]) -> Path:
        """
        설정 파일 경로 결정

        Args:
            config_path: 사용자 지정 설정 파일 경로

        Returns:
            최종 설정 파일 경로
        """
        if config_path:
            return config_path

        # 현재 작업 디렉토리의 config.ini 확인
        current_config = Path.cwd() / "config.ini"
        if current_config.exists():
            return current_config

        # 패키지 내의 기본 config 디렉토리 확인
        package_root = Path(__file__).parent.parent.parent.parent
        default_config = package_root / "config" / "config.ini"
        if default_config.exists():
            return default_config

        # config 디렉토리의 기본 설정 파일
        config_dir = package_root / "config"
        if config_dir.exists():
            return config_dir / "config.ini"

        # 최후의 수단: 현재 디렉토리에 config.ini 생성
        return Path.cwd() / "config.ini"

    def _load_config(self) -> None:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                self.config.read(self.config_path, encoding="utf-8")
                logger.info(f"설정 파일 로드됨: {self.config_path}")
            else:
                logger.warning(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
                self._create_default_config()

        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            self._load_default_values()

    def _create_default_config(self) -> None:
        """기본 설정 파일 생성"""
        try:
            # 설정 디렉토리 생성
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # 기본 설정 값 설정
            self._load_default_values()

            # 설정 파일 저장
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)

            logger.info(f"기본 설정 파일 생성됨: {self.config_path}")

        except Exception as e:
            logger.error(f"기본 설정 파일 생성 실패: {e}")

    def _load_default_values(self) -> None:
        """기본 설정 값 로드"""
        # API 설정
        self.config["api"] = {
            "base_url": "http://localhost:8000",
            "timeout": "30",
            "max_retries": "3",
            "retry_delay": "1.0",
        }

        # CLI 설정
        self.config["cli"] = {
            "default_output_format": "text",
            "verbose": "false",
            "show_progress": "true",
        }

        # 로깅 설정
        self.config["logging"] = {
            "level": "INFO",
            "format": "%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s",
            "file_enabled": "false",
            "file_path": "ts-cli.log",
        }

        # VCS 설정
        self.config["vcs"] = {
            "git_timeout": "30",
            "max_diff_size": "1048576",  # 1MB
        }

    def get(
        self, section: str, key: str, default: Any = None, value_type: type = str
    ) -> Any:
        """
        설정 값 조회

        Args:
            section: 설정 섹션명
            key: 설정 키명
            default: 기본값
            value_type: 반환값 타입

        Returns:
            설정 값 (지정된 타입으로 변환됨)
        """
        try:
            if not self.config.has_section(section):
                return default

            if not self.config.has_option(section, key):
                return default

            value = self.config.get(section, key)

            # 타입 변환
            if value_type == bool:
                return value.lower() in ("true", "1", "yes", "on")
            elif value_type == int:
                return int(value)
            elif value_type == float:
                return float(value)
            else:
                return value

        except Exception as e:
            logger.warning(f"설정 값 조회 실패 ({section}.{key}): {e}")
            return default

    def set(self, section: str, key: str, value: Any) -> None:
        """
        설정 값 설정

        Args:
            section: 섹션명
            key: 설정 키
            value: 설정 값
        """
        section_added = False
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
                section_added = True

            self.config.set(section, key, str(value))

        except Exception as e:
            logger.error(f"설정 값 설정 실패 ({section}.{key}): {e}")
            # 예외 발생 시 추가된 섹션 제거
            if section_added:
                try:
                    self.config.remove_section(section)
                except Exception:
                    pass  # 섹션 제거 실패는 무시
            return

    def save(self) -> bool:
        """
        설정 파일 저장

        Returns:
            저장 성공 여부
        """
        try:
            # 디렉토리가 없으면 생성
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)
            logger.info(f"설정 파일 저장됨: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            return False

    def get_section(self, section: str) -> Dict[str, str]:
        """
        섹션 전체 조회

        Args:
            section: 섹션명

        Returns:
            섹션의 모든 설정을 담은 딕셔너리
        """
        try:
            if self.config.has_section(section):
                return dict(self.config.items(section))
            return {}

        except Exception as e:
            logger.warning(f"섹션 조회 실패 ({section}): {e}")
            return {}

    def get_all_sections(self) -> Dict[str, Dict[str, str]]:
        """
        모든 섹션 조회

        Returns:
            모든 설정을 담은 중첩 딕셔너리
        """
        result = {}
        for section_name in self.config.sections():
            result[section_name] = self.get_section(section_name)
        return result


# 전역 설정 로더 인스턴스
_config_loader: Optional[ConfigLoader] = None


def load_config(config_path: Optional[Union[str, Path]] = None) -> ConfigLoader:
    """
    설정 로더 초기화 및 반환

    Args:
        config_path: 설정 파일 경로

    Returns:
        ConfigLoader 인스턴스
    """
    global _config_loader

    if _config_loader is None or config_path is not None:
        path = Path(config_path) if config_path else None
        _config_loader = ConfigLoader(path)

    return _config_loader


def get_config() -> ConfigLoader:
    """
    현재 설정 로더 인스턴스 반환

    Returns:
        ConfigLoader 인스턴스

    Raises:
        RuntimeError: 설정 로더가 초기화되지 않은 경우
    """
    if _config_loader is None:
        return load_config()
    return _config_loader


def get_api_config() -> Dict[str, Any]:
    """
    API 설정 반환

    Returns:
        API 설정 딕셔너리
    """
    config = get_config()
    return {
        "base_url": config.get("api", "base_url"),
        "timeout": config.get("api", "timeout", 30, int),
        "max_retries": config.get("api", "max_retries", 3, int),
        "retry_delay": config.get("api", "retry_delay", 1.0, float),
    }


def get_cli_config() -> Dict[str, Any]:
    """
    CLI 설정 반환

    Returns:
        CLI 설정 딕셔너리
    """
    config = get_config()
    return {
        "default_output_format": config.get("cli", "default_output_format", "text"),
        "verbose": config.get("cli", "verbose", False, bool),
        "show_progress": config.get("cli", "show_progress", True, bool),
    }
