import os
import threading
from pathlib import Path
from typing import Any, Optional
import yaml


class ConfigManager:
    _instance: Optional["ConfigManager"] = None
    _lock = threading.Lock()

    def __init__(self, config_path: str):
        self._config_path = Path(config_path)
        self._data: dict = {}
        self._observer = None
        self.reload()

    @classmethod
    def get_instance(cls, config_path: str = "config/config.yaml") -> "ConfigManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config_path)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            if cls._instance and cls._instance._observer:
                cls._instance._observer.stop()
            cls._instance = None

    def reload(self) -> None:
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            print(f"[ConfigManager] 配置文件不存在：{self._config_path}，使用空配置")
            self._data = {}
        except yaml.YAMLError as e:
            print(f"[ConfigManager] 配置文件解析失败：{e}，使用空配置")
            self._data = {}
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        if url := os.environ.get("SEARXNG_URL"):
            self._set_nested("sources.searxng.url", url)
        if level := os.environ.get("LOG_LEVEL"):
            self._set_nested("logging.level", level)
        if proxy := os.environ.get("HTTP_PROXY"):
            self._set_nested("collector.proxy", proxy)

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def _set_nested(self, key: str, value: Any) -> None:
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def start_watching(self) -> None:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            config_manager = self

            class _Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if Path(event.src_path).resolve() == config_manager._config_path.resolve():
                        config_manager.reload()

            self._observer = Observer()
            self._observer.schedule(_Handler(), str(self._config_path.parent), recursive=False)
            self._observer.start()
        except ImportError:
            print("[ConfigManager] watchdog 未安装，跳过热更新")

    def stop_watching(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
