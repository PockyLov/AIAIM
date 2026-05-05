from __future__ import annotations

import logging
import threading
import time

from .collector_service import CollectorService


class HotkeyController:
    def __init__(self, service: CollectorService, interval_ms: int, logger: logging.Logger) -> None:
        self.service = service
        self.interval_s = interval_ms / 1000
        self.logger = logger
        self._running = threading.Event()
        self._stop = threading.Event()
        self._worker = threading.Thread(target=self._loop, name="aiaim-capture-loop", daemon=True)

    def run(self) -> None:
        from pynput import keyboard

        self._worker.start()
        self.logger.info("hotkeys ready F8=start/stop F9=single Esc=exit")
        print("Hotkeys: F8 start/stop continuous, F9 single screenshot, Esc exit")

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool | None:
            if key == keyboard.Key.f8:
                self.toggle()
            elif key == keyboard.Key.f9:
                self.service.capture_once("hotkey_single")
            elif key == keyboard.Key.esc:
                self.stop()
                return False
            return None

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
        self._worker.join(timeout=2)

    def toggle(self) -> None:
        if self._running.is_set():
            self._running.clear()
            self.logger.info("continuous capture stopped")
            print("Continuous capture stopped")
        else:
            self._running.set()
            self.logger.info("continuous capture started")
            print("Continuous capture started")

    def stop(self) -> None:
        self._running.clear()
        self._stop.set()
        self.logger.info("hotkey controller exiting")
        print("Exiting")

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self._running.is_set():
                self.service.capture_once("hotkey_continuous")
            time.sleep(self.interval_s)
