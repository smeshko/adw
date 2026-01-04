"""Tests for mobile screenshot capture functionality.

This module tests iOS simulator and Android emulator screenshot capture
using mocked subprocess calls.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adw.models.evidence import MobileDeviceType


# =============================================================================
# iOS Simulator Tests (Task 2)
# =============================================================================


class TestCheckIosSimulatorAvailable:
    """Tests for iOS simulator availability check."""

    def test_ios_simulator_available_when_booted(self) -> None:
        """Test that iOS simulator is detected when booted."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                    {
                        "dataPath": "/path/to/data",
                        "logPath": "/path/to/logs",
                        "udid": "12345-ABCDE",
                        "name": "iPhone 15 Pro",
                        "state": "Booted"
                    }
                ]
            }
        })

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_ios_simulator_available
            assert check_ios_simulator_available() is True

    def test_ios_simulator_not_available_when_no_booted_devices(self) -> None:
        """Test that iOS simulator is not detected when no booted devices."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                    {
                        "udid": "12345-ABCDE",
                        "name": "iPhone 15 Pro",
                        "state": "Shutdown"
                    }
                ]
            }
        })

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_ios_simulator_available
            assert check_ios_simulator_available() is False

    def test_ios_simulator_not_available_when_xcrun_not_found(self) -> None:
        """Test graceful handling when xcrun is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import check_ios_simulator_available
            assert check_ios_simulator_available() is False

    def test_ios_simulator_not_available_when_command_fails(self) -> None:
        """Test handling when simctl command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_ios_simulator_available
            assert check_ios_simulator_available() is False

    def test_ios_simulator_not_available_when_invalid_json(self) -> None:
        """Test handling when simctl returns invalid JSON."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_ios_simulator_available
            assert check_ios_simulator_available() is False

    def test_ios_simulator_not_available_when_timeout(self) -> None:
        """Test handling when command times out."""
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 10)):
            from adw.evidence.mobile_capture import check_ios_simulator_available
            assert check_ios_simulator_available() is False


class TestGetBootedSimulator:
    """Tests for getting booted simulator info."""

    def test_get_booted_simulator_returns_udid(self) -> None:
        """Test that get_booted_simulator returns the UDID of booted device."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                    {
                        "udid": "12345-ABCDE",
                        "name": "iPhone 15 Pro",
                        "state": "Booted"
                    }
                ]
            }
        })

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import get_booted_simulator
            result = get_booted_simulator()
            assert result is not None
            assert result["udid"] == "12345-ABCDE"
            assert result["name"] == "iPhone 15 Pro"

    def test_get_booted_simulator_returns_none_when_no_device(self) -> None:
        """Test that get_booted_simulator returns None when no device is booted."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"devices": {}})

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import get_booted_simulator
            assert get_booted_simulator() is None


class TestCaptureIosScreenshot:
    """Tests for iOS screenshot capture."""

    def test_capture_ios_screenshot_success(self, tmp_path: Path) -> None:
        """Test successful iOS screenshot capture."""
        output_path = tmp_path / "screenshot.png"

        # Mock successful screenshot capture
        mock_capture = MagicMock()
        mock_capture.returncode = 0
        mock_capture.stderr = ""

        # Mock device info
        mock_device_info = MagicMock()
        mock_device_info.returncode = 0
        mock_device_info.stdout = json.dumps({
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                    {
                        "udid": "12345-ABCDE",
                        "name": "iPhone 15 Pro",
                        "state": "Booted"
                    }
                ]
            }
        })

        def mock_run(cmd, *args, **kwargs):
            if "screenshot" in cmd:
                # Create a fake screenshot file
                output_path.write_bytes(b"fake png data")
                return mock_capture
            return mock_device_info

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_ios_screenshot
            result = capture_ios_screenshot(output_path, "home")

            assert result.success is True
            assert result.screen_name == "home"
            assert result.device_type == MobileDeviceType.IOS
            assert result.error is None

    def test_capture_ios_screenshot_failure(self, tmp_path: Path) -> None:
        """Test failed iOS screenshot capture."""
        output_path = tmp_path / "screenshot.png"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "No booted devices available"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import capture_ios_screenshot
            result = capture_ios_screenshot(output_path, "home")

            assert result.success is False
            assert result.error is not None
            assert "No booted devices available" in result.error

    def test_capture_ios_screenshot_timeout(self, tmp_path: Path) -> None:
        """Test iOS screenshot capture timeout handling."""
        import subprocess
        output_path = tmp_path / "screenshot.png"

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            from adw.evidence.mobile_capture import capture_ios_screenshot
            result = capture_ios_screenshot(output_path, "home")

            assert result.success is False
            assert result.error is not None
            assert "timed out" in result.error.lower()


# =============================================================================
# Android Emulator Tests (Task 3)
# =============================================================================


class TestCheckAndroidEmulatorAvailable:
    """Tests for Android emulator availability check."""

    def test_android_emulator_available_when_running(self) -> None:
        """Test that Android emulator is detected when running."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "List of devices attached\nemulator-5554\tdevice\n"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_android_emulator_available
            assert check_android_emulator_available() is True

    def test_android_emulator_not_available_when_no_devices(self) -> None:
        """Test that Android emulator is not detected when no devices."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "List of devices attached\n"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_android_emulator_available
            assert check_android_emulator_available() is False

    def test_android_emulator_not_available_when_adb_not_found(self) -> None:
        """Test graceful handling when adb is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import check_android_emulator_available
            assert check_android_emulator_available() is False


class TestGetRunningEmulator:
    """Tests for getting running emulator info."""

    def test_get_running_emulator_returns_serial(self) -> None:
        """Test that get_running_emulator returns the device serial."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "List of devices attached\nemulator-5554\tdevice\n"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import get_running_emulator
            assert get_running_emulator() == "emulator-5554"

    def test_get_running_emulator_returns_none_when_no_device(self) -> None:
        """Test that get_running_emulator returns None when no device."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "List of devices attached\n"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import get_running_emulator
            assert get_running_emulator() is None


class TestCaptureAndroidScreenshot:
    """Tests for Android screenshot capture."""

    def test_capture_android_screenshot_success(self, tmp_path: Path) -> None:
        """Test successful Android screenshot capture."""
        output_path = tmp_path / "screenshot.png"

        # Mock successful screenshot capture (binary data)
        mock_capture = MagicMock()
        mock_capture.returncode = 0
        mock_capture.stdout = b"fake png data"

        # Mock device info
        mock_getprop = MagicMock()
        mock_getprop.returncode = 0
        mock_getprop.stdout = "sdk_gphone64\n"

        call_count = 0
        def mock_run(cmd, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "screencap" in cmd:
                return mock_capture
            return mock_getprop

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_android_screenshot
            result = capture_android_screenshot(output_path, "home")

            assert result.success is True
            assert result.screen_name == "home"
            assert result.device_type == MobileDeviceType.ANDROID

    def test_capture_android_screenshot_failure(self, tmp_path: Path) -> None:
        """Test failed Android screenshot capture."""
        output_path = tmp_path / "screenshot.png"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: no devices/emulators found"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import capture_android_screenshot
            result = capture_android_screenshot(output_path, "home")

            assert result.success is False
            assert result.error is not None
