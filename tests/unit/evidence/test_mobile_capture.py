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


# =============================================================================
# Flutter Support Tests (Task 4)
# =============================================================================


class TestDetectFlutterDevice:
    """Tests for Flutter device detection."""

    def test_detect_flutter_ios_device(self) -> None:
        """Test detecting a Flutter iOS device."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "name": "iPhone 15 Pro",
                "id": "12345-ABCDE",
                "platform": "ios",
                "platformType": "ios"
            }
        ])

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import detect_flutter_device
            result = detect_flutter_device()
            assert result is not None
            assert result["platform"] == "ios"
            assert result["id"] == "12345-ABCDE"

    def test_detect_flutter_android_device(self) -> None:
        """Test detecting a Flutter Android device."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "name": "sdk_gphone64",
                "id": "emulator-5554",
                "platform": "android",
                "platformType": "android"
            }
        ])

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import detect_flutter_device
            result = detect_flutter_device()
            assert result is not None
            assert result["platform"] == "android"

    def test_detect_flutter_no_devices(self) -> None:
        """Test when no Flutter devices available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import detect_flutter_device
            assert detect_flutter_device() is None

    def test_detect_flutter_not_installed(self) -> None:
        """Test graceful handling when flutter is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import detect_flutter_device
            assert detect_flutter_device() is None

    def test_flutter_prefers_ios_when_both_available(self) -> None:
        """Test that iOS is preferred when both platforms are available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "name": "sdk_gphone64",
                "id": "emulator-5554",
                "platform": "android"
            },
            {
                "name": "iPhone 15 Pro",
                "id": "12345-ABCDE",
                "platform": "ios"
            }
        ])

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import detect_flutter_device
            result = detect_flutter_device()
            # Should return first device (order preserved)
            assert result is not None


# =============================================================================
# Screen Navigation Tests (Task 5)
# =============================================================================


class TestNavigateIosDeeplink:
    """Tests for iOS deeplink navigation."""

    def test_navigate_ios_deeplink_success(self) -> None:
        """Test successful iOS deeplink navigation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import navigate_ios_deeplink
            assert navigate_ios_deeplink("myapp://home") is True

    def test_navigate_ios_deeplink_failure(self) -> None:
        """Test failed iOS deeplink navigation."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Unable to open URL"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import navigate_ios_deeplink
            assert navigate_ios_deeplink("myapp://invalid") is False

    def test_navigate_ios_deeplink_xcrun_not_found(self) -> None:
        """Test when xcrun is not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import navigate_ios_deeplink
            assert navigate_ios_deeplink("myapp://home") is False


class TestNavigateAndroidDeeplink:
    """Tests for Android deeplink navigation."""

    def test_navigate_android_deeplink_success(self) -> None:
        """Test successful Android deeplink navigation."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import navigate_android_deeplink
            assert navigate_android_deeplink("myapp://home") is True

    def test_navigate_android_deeplink_failure(self) -> None:
        """Test failed Android deeplink navigation."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Activity not found"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import navigate_android_deeplink
            assert navigate_android_deeplink("myapp://invalid") is False

    def test_navigate_android_deeplink_adb_not_found(self) -> None:
        """Test when adb is not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import navigate_android_deeplink
            assert navigate_android_deeplink("myapp://home") is False


class TestCaptureFlutterScreenshot:
    """Tests for Flutter screenshot capture."""

    def test_capture_flutter_ios_screenshot(self, tmp_path: Path) -> None:
        """Test Flutter screenshot capture on iOS."""
        output_path = tmp_path / "screenshot.png"

        # Mock flutter devices returning iOS
        mock_flutter_devices = MagicMock()
        mock_flutter_devices.returncode = 0
        mock_flutter_devices.stdout = json.dumps([{
            "name": "iPhone 15 Pro",
            "id": "12345-ABCDE",
            "platform": "ios"
        }])

        # Mock iOS screenshot capture
        mock_capture = MagicMock()
        mock_capture.returncode = 0
        mock_capture.stderr = ""

        # Mock device info
        mock_device_info = MagicMock()
        mock_device_info.returncode = 0
        mock_device_info.stdout = json.dumps({
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [{
                    "udid": "12345-ABCDE",
                    "name": "iPhone 15 Pro",
                    "state": "Booted"
                }]
            }
        })

        call_count = 0
        def mock_run(cmd, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "flutter" in cmd:
                return mock_flutter_devices
            if "screenshot" in cmd:
                output_path.write_bytes(b"fake png")
                return mock_capture
            return mock_device_info

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_flutter_screenshot
            result = capture_flutter_screenshot(output_path, "home")
            assert result.success is True
            assert result.device_type in (MobileDeviceType.FLUTTER_IOS, MobileDeviceType.IOS)


# =============================================================================
# Config-Based Screen Loading Tests (Task 6)
# =============================================================================


class TestLoadMobileScreensConfig:
    """Tests for loading mobile screen configuration."""

    def test_load_config_from_project_yaml(self, tmp_path: Path) -> None:
        """Test loading screens from .adw/project.yaml."""
        # Create config directory and file
        config_dir = tmp_path / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text("""
evidence:
  mobile_screens:
    - name: "home"
      deeplink: "myapp://home"
      capture_delay_ms: 500
    - name: "profile"
      deeplink: "myapp://profile/123"
""")

        from adw.evidence.mobile_capture import load_mobile_screens_config
        screens = load_mobile_screens_config(tmp_path)

        assert len(screens) == 2
        assert screens[0].name == "home"
        assert screens[0].deeplink == "myapp://home"
        assert screens[1].name == "profile"

    def test_load_config_empty_when_no_file(self, tmp_path: Path) -> None:
        """Test empty list when no config file exists."""
        from adw.evidence.mobile_capture import load_mobile_screens_config
        screens = load_mobile_screens_config(tmp_path)
        assert screens == []

    def test_load_config_handles_invalid_yaml(self, tmp_path: Path) -> None:
        """Test graceful handling of invalid YAML."""
        config_dir = tmp_path / ".adw"
        config_dir.mkdir()
        config_file = config_dir / "project.yaml"
        config_file.write_text("invalid: yaml: content:")

        from adw.evidence.mobile_capture import load_mobile_screens_config
        screens = load_mobile_screens_config(tmp_path)
        assert screens == []


class TestSaveEvidenceMetadata:
    """Tests for saving evidence metadata."""

    def test_save_metadata_creates_json_file(self, tmp_path: Path) -> None:
        """Test that metadata is saved as JSON."""
        from adw.models.evidence import (
            MobileDeviceType,
            MobileEvidenceSummary,
            MobileScreenshotResult,
        )
        from adw.evidence.mobile_capture import save_evidence_metadata

        results = [
            MobileScreenshotResult(
                path=tmp_path / "home_ios.png",
                screen_name="home",
                device_type=MobileDeviceType.IOS,
                device_name="iPhone 15",
                os_version="17.2",
                success=True,
            ),
        ]
        summary = MobileEvidenceSummary(
            total_screenshots=1,
            successful=1,
            failed=0,
            results=results,
        )

        metadata_path = save_evidence_metadata(tmp_path, summary)

        assert metadata_path.exists()
        assert metadata_path.name == "metadata.json"

        # Verify JSON content
        content = json.loads(metadata_path.read_text())
        assert content["total_screenshots"] == 1
        assert content["successful"] == 1
        assert len(content["screenshots"]) == 1
        assert content["screenshots"][0]["screen_name"] == "home"

    def test_metadata_includes_all_fields(self, tmp_path: Path) -> None:
        """Test that metadata includes all required fields."""
        from adw.models.evidence import (
            MobileDeviceType,
            MobileEvidenceSummary,
            MobileScreenshotResult,
        )
        from adw.evidence.mobile_capture import save_evidence_metadata

        results = [
            MobileScreenshotResult(
                path=tmp_path / "test.png",
                screen_name="test",
                device_type=MobileDeviceType.ANDROID,
                device_name="sdk_gphone64",
                os_version="14",
                success=True,
            ),
        ]
        summary = MobileEvidenceSummary(
            total_screenshots=1,
            successful=1,
            failed=0,
            results=results,
        )

        metadata_path = save_evidence_metadata(tmp_path, summary)
        content = json.loads(metadata_path.read_text())

        # Check screenshot entry
        screenshot = content["screenshots"][0]
        assert "screen_name" in screenshot
        assert "device_type" in screenshot
        assert "device_name" in screenshot
        assert "os_version" in screenshot
        assert "file" in screenshot
        assert "success" in screenshot
        assert "captured_at" in screenshot


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_sanitize_spaces(self) -> None:
        """Test that spaces are replaced with underscores."""
        from adw.evidence.mobile_capture import _sanitize_filename
        assert _sanitize_filename("home screen") == "home_screen"

    def test_sanitize_special_chars(self) -> None:
        """Test that special characters are removed."""
        from adw.evidence.mobile_capture import _sanitize_filename
        assert _sanitize_filename("profile/edit") == "profile_edit"
        assert _sanitize_filename("user@profile") == "userprofile"

    def test_sanitize_lowercase(self) -> None:
        """Test that result is lowercase."""
        from adw.evidence.mobile_capture import _sanitize_filename
        assert _sanitize_filename("HomeScreen") == "homescreen"


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
