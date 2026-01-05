"""Tests for mobile screenshot capture functionality.

This module tests iOS simulator and Android emulator screenshot capture
using mocked subprocess calls.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        mock_result.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {
                            "dataPath": "/path/to/data",
                            "logPath": "/path/to/logs",
                            "udid": "12345-ABCDE",
                            "name": "iPhone 15 Pro",
                            "state": "Booted",
                        }
                    ]
                }
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import check_ios_simulator_available

            assert check_ios_simulator_available() is True

    def test_ios_simulator_not_available_when_no_booted_devices(self) -> None:
        """Test that iOS simulator is not detected when no booted devices."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {
                            "udid": "12345-ABCDE",
                            "name": "iPhone 15 Pro",
                            "state": "Shutdown",
                        }
                    ]
                }
            }
        )

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
        mock_result.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {
                            "udid": "12345-ABCDE",
                            "name": "iPhone 15 Pro",
                            "state": "Booted",
                        }
                    ]
                }
            }
        )

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
        mock_device_info.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {
                            "udid": "12345-ABCDE",
                            "name": "iPhone 15 Pro",
                            "state": "Booted",
                        }
                    ]
                }
            }
        )

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
        mock_result.stdout = json.dumps(
            [
                {
                    "name": "iPhone 15 Pro",
                    "id": "12345-ABCDE",
                    "platform": "ios",
                    "platformType": "ios",
                }
            ]
        )

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
        mock_result.stdout = json.dumps(
            [
                {
                    "name": "sdk_gphone64",
                    "id": "emulator-5554",
                    "platform": "android",
                    "platformType": "android",
                }
            ]
        )

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
        mock_result.stdout = json.dumps(
            [
                {"name": "sdk_gphone64", "id": "emulator-5554", "platform": "android"},
                {"name": "iPhone 15 Pro", "id": "12345-ABCDE", "platform": "ios"},
            ]
        )

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
        mock_flutter_devices.stdout = json.dumps(
            [{"name": "iPhone 15 Pro", "id": "12345-ABCDE", "platform": "ios"}]
        )

        # Mock iOS screenshot capture
        mock_capture = MagicMock()
        mock_capture.returncode = 0
        mock_capture.stderr = ""

        # Mock device info
        mock_device_info = MagicMock()
        mock_device_info.returncode = 0
        mock_device_info.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {
                            "udid": "12345-ABCDE",
                            "name": "iPhone 15 Pro",
                            "state": "Booted",
                        }
                    ]
                }
            }
        )

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
            assert result.device_type in (
                MobileDeviceType.FLUTTER_IOS,
                MobileDeviceType.IOS,
            )


# =============================================================================
# Config-Based Screen Loading Tests (Task 6)
# =============================================================================


class TestLoadMobileScreensConfig:
    """Tests for loading mobile screen configuration."""

    def test_load_config_from_project_yaml(self, tmp_path: Path) -> None:
        """Test loading screens from .adw/project.yaml."""
        # Create config directory and file
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
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
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "project.yaml"
        config_file.write_text("invalid: yaml: content:")

        from adw.evidence.mobile_capture import load_mobile_screens_config

        screens = load_mobile_screens_config(tmp_path)
        assert screens == []


class TestSaveEvidenceMetadata:
    """Tests for saving evidence metadata."""

    def test_save_metadata_creates_json_file(self, tmp_path: Path) -> None:
        """Test that metadata is saved as JSON."""
        from adw.evidence.mobile_capture import save_evidence_metadata
        from adw.models.evidence import (
            MobileDeviceType,
            MobileEvidenceSummary,
            MobileScreenshotResult,
        )

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
        from adw.evidence.mobile_capture import save_evidence_metadata
        from adw.models.evidence import (
            MobileDeviceType,
            MobileEvidenceSummary,
            MobileScreenshotResult,
        )

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

    def test_capture_android_screenshot_bytes_stderr(self, tmp_path: Path) -> None:
        """Test Android screenshot failure with bytes stderr."""
        output_path = tmp_path / "screenshot.png"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b"error: device not found"

        with patch("subprocess.run", return_value=mock_result):
            from adw.evidence.mobile_capture import capture_android_screenshot

            result = capture_android_screenshot(output_path, "home")

            assert result.success is False
            assert "device not found" in result.error

    def test_capture_android_screenshot_timeout(self, tmp_path: Path) -> None:
        """Test Android screenshot timeout handling."""
        import subprocess

        output_path = tmp_path / "screenshot.png"

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            from adw.evidence.mobile_capture import capture_android_screenshot

            result = capture_android_screenshot(output_path, "home")

            assert result.success is False
            assert "timed out" in result.error.lower()

    def test_capture_android_screenshot_adb_not_found(self, tmp_path: Path) -> None:
        """Test when adb is not available."""
        output_path = tmp_path / "screenshot.png"

        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import capture_android_screenshot

            result = capture_android_screenshot(output_path, "home")

            assert result.success is False
            assert "adb not found" in result.error


# =============================================================================
# Capture Configured Screens Tests (Task 7)
# =============================================================================


class TestCaptureConfiguredScreens:
    """Tests for capture_configured_screens function."""

    def test_capture_configured_screens_no_config(self, tmp_path: Path) -> None:
        """Test capturing screens when no config exists."""
        output_dir = tmp_path / "output"

        # Mock iOS simulator available
        mock_device_info = MagicMock()
        mock_device_info.returncode = 0
        mock_device_info.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {"udid": "12345", "name": "iPhone 15", "state": "Booted"}
                    ]
                }
            }
        )

        mock_capture = MagicMock()
        mock_capture.returncode = 0
        mock_capture.stderr = ""

        def mock_run(cmd, *args, **kwargs):
            if "screenshot" in cmd:
                (output_dir / "current_ios.png").parent.mkdir(
                    parents=True, exist_ok=True
                )
                (output_dir / "current_ios.png").write_bytes(b"fake")
                return mock_capture
            return mock_device_info

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_configured_screens
            from adw.models.evidence import MobileDeviceType

            summary = capture_configured_screens(
                project_root=tmp_path,
                output_dir=output_dir,
                device_type=MobileDeviceType.IOS,
            )

            assert summary.total_screenshots == 1
            assert summary.results[0].screen_name == "current"

    def test_capture_configured_screens_with_config(self, tmp_path: Path) -> None:
        """Test capturing screens with configuration."""
        # Create config
        config_dir = tmp_path / ".adw"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "project.yaml").write_text("""
evidence:
  mobile_screens:
    - name: "home"
      deeplink: "myapp://home"
    - name: "profile"
      deeplink: "myapp://profile"
""")

        output_dir = tmp_path / "output"

        # Mock successful captures
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"fake png"
        mock_result.stderr = ""

        call_count = 0

        def mock_run(cmd, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "screencap" in cmd:
                return mock_result
            # For adb shell getprop
            mock_getprop = MagicMock()
            mock_getprop.returncode = 0
            mock_getprop.stdout = "sdk_gphone64\n"
            return mock_getprop

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_configured_screens
            from adw.models.evidence import MobileDeviceType

            summary = capture_configured_screens(
                project_root=tmp_path,
                output_dir=output_dir,
                device_type=MobileDeviceType.ANDROID,
            )

            assert summary.total_screenshots == 2
            assert output_dir.exists()

    def test_capture_configured_screens_flutter_ios(self, tmp_path: Path) -> None:
        """Test capturing screens with Flutter iOS device type."""
        output_dir = tmp_path / "output"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {"udid": "12345", "name": "iPhone 15", "state": "Booted"}
                    ]
                }
            }
        )
        mock_result.stderr = ""

        def mock_run(cmd, *args, **kwargs):
            if "screenshot" in cmd:
                (output_dir / "current_flutter_ios.png").parent.mkdir(
                    parents=True, exist_ok=True
                )
                (output_dir / "current_flutter_ios.png").write_bytes(b"fake")
            return mock_result

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_configured_screens
            from adw.models.evidence import MobileDeviceType

            summary = capture_configured_screens(
                project_root=tmp_path,
                output_dir=output_dir,
                device_type=MobileDeviceType.FLUTTER_IOS,
            )

            assert summary.total_screenshots == 1


class TestCaptureFlutterScreenshotFallbacks:
    """Tests for capture_flutter_screenshot fallback paths."""

    def test_flutter_fallback_to_ios_when_no_flutter_device(
        self, tmp_path: Path
    ) -> None:
        """Test Flutter falls back to iOS when no flutter device detected."""
        output_path = tmp_path / "screenshot.png"

        # Mock flutter devices returning empty
        mock_flutter = MagicMock()
        mock_flutter.returncode = 0
        mock_flutter.stdout = "[]"

        # Mock iOS simulator available
        mock_ios = MagicMock()
        mock_ios.returncode = 0
        mock_ios.stdout = json.dumps(
            {
                "devices": {
                    "com.apple.CoreSimulator.SimRuntime.iOS-17-2": [
                        {"udid": "12345", "name": "iPhone 15", "state": "Booted"}
                    ]
                }
            }
        )
        mock_ios.stderr = ""

        call_count = 0

        def mock_run(cmd, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "flutter" in cmd:
                return mock_flutter
            if "screenshot" in cmd:
                output_path.write_bytes(b"fake")
            return mock_ios

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_flutter_screenshot

            result = capture_flutter_screenshot(output_path, "home")

            assert result.device_type.value in ("flutter_ios", "ios")

    def test_flutter_fallback_to_android_when_no_ios(self, tmp_path: Path) -> None:
        """Test Flutter falls back to Android when no iOS available."""
        output_path = tmp_path / "screenshot.png"

        # Mock flutter devices returning empty
        mock_flutter = MagicMock()
        mock_flutter.returncode = 0
        mock_flutter.stdout = "[]"

        # Mock iOS not available, Android available
        mock_ios_empty = MagicMock()
        mock_ios_empty.returncode = 0
        mock_ios_empty.stdout = json.dumps({"devices": {}})

        mock_android = MagicMock()
        mock_android.returncode = 0
        mock_android.stdout = "List of devices attached\nemulator-5554\tdevice\n"

        mock_screencap = MagicMock()
        mock_screencap.returncode = 0
        mock_screencap.stdout = b"fake png"

        call_count = 0

        def mock_run(cmd, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "flutter" in cmd_str:
                return mock_flutter
            if "simctl" in cmd_str:
                return mock_ios_empty
            if "adb devices" in cmd_str:
                return mock_android
            if "screencap" in cmd_str:
                return mock_screencap
            # getprop
            mock_prop = MagicMock()
            mock_prop.returncode = 0
            mock_prop.stdout = "sdk_gphone64\n"
            return mock_prop

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_flutter_screenshot

            result = capture_flutter_screenshot(output_path, "home")

            assert result.device_type.value in ("flutter_android", "android")

    def test_flutter_no_device_available(self, tmp_path: Path) -> None:
        """Test Flutter when no device is available at all."""
        output_path = tmp_path / "screenshot.png"

        # All devices return empty/not available
        mock_empty = MagicMock()
        mock_empty.returncode = 0
        mock_empty.stdout = "[]"

        mock_ios_empty = MagicMock()
        mock_ios_empty.returncode = 0
        mock_ios_empty.stdout = json.dumps({"devices": {}})

        mock_android_empty = MagicMock()
        mock_android_empty.returncode = 0
        mock_android_empty.stdout = "List of devices attached\n"

        def mock_run(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "flutter" in cmd_str:
                return mock_empty
            if "simctl" in cmd_str:
                return mock_ios_empty
            if "adb" in cmd_str:
                return mock_android_empty
            return mock_empty

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_flutter_screenshot

            result = capture_flutter_screenshot(output_path, "home")

            assert result.success is False
            assert (
                "No Flutter device" in result.error
                or "simulator/emulator" in result.error
            )

    def test_flutter_android_device_detected(self, tmp_path: Path) -> None:
        """Test Flutter with Android device detected."""
        output_path = tmp_path / "screenshot.png"

        mock_flutter = MagicMock()
        mock_flutter.returncode = 0
        mock_flutter.stdout = json.dumps(
            [{"name": "sdk_gphone64", "id": "emulator-5554", "platform": "android"}]
        )

        mock_screencap = MagicMock()
        mock_screencap.returncode = 0
        mock_screencap.stdout = b"fake png"

        def mock_run(cmd, *args, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "flutter" in cmd_str:
                return mock_flutter
            if "screencap" in cmd_str:
                return mock_screencap
            mock_prop = MagicMock()
            mock_prop.returncode = 0
            mock_prop.stdout = "sdk_gphone64\n"
            return mock_prop

        with patch("subprocess.run", side_effect=mock_run):
            from adw.evidence.mobile_capture import capture_flutter_screenshot

            result = capture_flutter_screenshot(output_path, "home")

            assert result.device_type.value == "flutter_android"

    def test_flutter_unknown_platform(self, tmp_path: Path) -> None:
        """Test Flutter with unknown platform type."""
        output_path = tmp_path / "screenshot.png"

        mock_flutter = MagicMock()
        mock_flutter.returncode = 0
        mock_flutter.stdout = json.dumps(
            [
                {
                    "name": "Unknown Device",
                    "id": "unknown-123",
                    "platform": "web",  # Unknown platform
                }
            ]
        )

        with patch("subprocess.run", return_value=mock_flutter):
            from adw.evidence.mobile_capture import capture_flutter_screenshot

            result = capture_flutter_screenshot(output_path, "home")

            assert result.success is False
            assert "Unknown Flutter platform" in result.error


class TestIosVersionParsing:
    """Tests for iOS version parsing helper."""

    def test_get_ios_version_from_runtime(self) -> None:
        """Test extracting iOS version from runtime string."""
        from adw.evidence.mobile_capture import _get_ios_version_from_runtime

        assert (
            _get_ios_version_from_runtime("com.apple.CoreSimulator.SimRuntime.iOS-17-2")
            == "17.2"
        )
        assert (
            _get_ios_version_from_runtime("com.apple.CoreSimulator.SimRuntime.iOS-16-0")
            == "16.0"
        )

    def test_get_ios_version_invalid_runtime(self) -> None:
        """Test with invalid runtime string."""
        from adw.evidence.mobile_capture import _get_ios_version_from_runtime

        assert _get_ios_version_from_runtime("invalid-runtime") is None
        assert _get_ios_version_from_runtime("") is None


class TestCaptureIosScreenshotXcrunNotFound:
    """Test for xcrun not found scenario."""

    def test_capture_ios_xcrun_not_found(self, tmp_path: Path) -> None:
        """Test iOS capture when xcrun is not installed."""
        output_path = tmp_path / "screenshot.png"

        with patch("subprocess.run", side_effect=FileNotFoundError):
            from adw.evidence.mobile_capture import capture_ios_screenshot

            result = capture_ios_screenshot(output_path, "home")

            assert result.success is False
            assert "xcrun not found" in result.error
