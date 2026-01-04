"""Mobile screenshot capture for iOS simulators and Android emulators.

This module provides functions to capture screenshots from mobile devices
during evidence gathering. It supports:
- iOS Simulator via xcrun simctl
- Android Emulator via adb
- Flutter projects (routes to appropriate platform)
"""

import json
import subprocess
from pathlib import Path

from adw.logging import LogCategory, get_logger
from adw.models.evidence import MobileDeviceType, MobileScreenshotResult


# =============================================================================
# iOS Simulator Functions
# =============================================================================


def check_ios_simulator_available() -> bool:
    """Check if an iOS Simulator is booted and available.

    Uses xcrun simctl to list booted devices. Returns True only if
    at least one device is in the "Booted" state.

    Returns:
        True if a simulator is booted, False otherwise

    Example:
        >>> if check_ios_simulator_available():
        ...     capture_ios_screenshot(output_path, "home")
    """
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False

        data = json.loads(result.stdout)
        devices = data.get("devices", {})

        # Check if any device is booted
        for runtime_devices in devices.values():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return True
        return False

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return False


def get_booted_simulator() -> dict[str, str] | None:
    """Get information about the booted iOS Simulator.

    Returns the first booted simulator found, including its UDID and name.

    Returns:
        Dictionary with 'udid' and 'name' keys, or None if no device is booted

    Example:
        >>> device = get_booted_simulator()
        >>> if device:
        ...     print(f"Using {device['name']}")
    """
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        devices = data.get("devices", {})

        # Find the first booted device
        for runtime, runtime_devices in devices.items():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return {
                        "udid": device.get("udid", ""),
                        "name": device.get("name", "Unknown"),
                        "runtime": runtime,
                    }
        return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def _get_ios_version_from_runtime(runtime: str) -> str | None:
    """Extract iOS version from runtime identifier.

    Args:
        runtime: Runtime identifier like "com.apple.CoreSimulator.SimRuntime.iOS-17-2"

    Returns:
        Version string like "17.2" or None if not parseable
    """
    # Format: com.apple.CoreSimulator.SimRuntime.iOS-17-2
    if "iOS-" in runtime:
        version_part = runtime.split("iOS-")[-1]
        return version_part.replace("-", ".")
    return None


def capture_ios_screenshot(
    output_path: Path,
    screen_name: str,
) -> MobileScreenshotResult:
    """Capture screenshot from booted iOS Simulator.

    Uses xcrun simctl io booted screenshot to capture the current screen.

    Args:
        output_path: Path where the screenshot should be saved
        screen_name: Name of the screen being captured

    Returns:
        MobileScreenshotResult with capture details and status

    Example:
        >>> result = capture_ios_screenshot(Path("/tmp/home.png"), "home")
        >>> if result.success:
        ...     print(f"Screenshot saved to {result.path}")
    """
    logger = get_logger()

    try:
        # Get device info first
        device_info = get_booted_simulator()
        device_name = device_info.get("name") if device_info else None
        os_version = (
            _get_ios_version_from_runtime(device_info.get("runtime", ""))
            if device_info
            else None
        )

        # Capture screenshot
        result = subprocess.run(
            ["xcrun", "simctl", "io", "booted", "screenshot", str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = result.stderr or "Screenshot capture failed"
            logger.warn(
                LogCategory.STATE,
                f"iOS screenshot capture failed: {error_msg}",
            )
            return MobileScreenshotResult(
                path=output_path,
                screen_name=screen_name,
                device_type=MobileDeviceType.IOS,
                device_name=device_name,
                os_version=os_version,
                success=False,
                error=error_msg,
            )

        logger.info(
            LogCategory.STATE,
            f"iOS screenshot captured: {screen_name} (device={device_name}, path={output_path})",
        )

        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.IOS,
            device_name=device_name,
            os_version=os_version,
            success=True,
        )

    except subprocess.TimeoutExpired:
        logger.warn(
            LogCategory.STATE,
            "iOS screenshot capture timed out",
        )
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.IOS,
            success=False,
            error="Screenshot capture timed out",
        )

    except FileNotFoundError:
        logger.warn(
            LogCategory.STATE,
            "xcrun not found - Xcode may not be installed",
        )
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.IOS,
            success=False,
            error="xcrun not found - Xcode may not be installed",
        )


# =============================================================================
# Android Emulator Functions
# =============================================================================


def check_android_emulator_available() -> bool:
    """Check if an Android Emulator is running and available.

    Uses adb devices to list connected devices. Returns True only if
    at least one emulator or device is in the "device" state.

    Returns:
        True if an emulator is running, False otherwise

    Example:
        >>> if check_android_emulator_available():
        ...     capture_android_screenshot(output_path, "home")
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False

        # Parse adb devices output
        # Format: "List of devices attached\nemulator-5554\tdevice\n"
        lines = result.stdout.strip().split("\n")
        for line in lines[1:]:  # Skip header line
            if "\tdevice" in line:
                return True
        return False

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_running_emulator() -> str | None:
    """Get the serial number of the running Android emulator.

    Returns the first device/emulator found in the "device" state.

    Returns:
        Device serial (e.g., "emulator-5554") or None if no device is running

    Example:
        >>> serial = get_running_emulator()
        >>> if serial:
        ...     print(f"Using emulator: {serial}")
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        # Parse adb devices output
        lines = result.stdout.strip().split("\n")
        for line in lines[1:]:  # Skip header line
            if "\tdevice" in line:
                return line.split("\t")[0]
        return None

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _get_android_device_info() -> tuple[str | None, str | None]:
    """Get Android device name and OS version.

    Returns:
        Tuple of (device_name, os_version) or (None, None) if unavailable
    """
    try:
        # Get device model
        model_result = subprocess.run(
            ["adb", "shell", "getprop", "ro.product.model"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        device_name = (
            model_result.stdout.strip() if model_result.returncode == 0 else None
        )

        # Get Android version
        version_result = subprocess.run(
            ["adb", "shell", "getprop", "ro.build.version.release"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        os_version = (
            version_result.stdout.strip() if version_result.returncode == 0 else None
        )

        return device_name, os_version

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None, None


def capture_android_screenshot(
    output_path: Path,
    screen_name: str,
) -> MobileScreenshotResult:
    """Capture screenshot from running Android Emulator.

    Uses adb exec-out screencap to capture the current screen.

    Args:
        output_path: Path where the screenshot should be saved
        screen_name: Name of the screen being captured

    Returns:
        MobileScreenshotResult with capture details and status

    Example:
        >>> result = capture_android_screenshot(Path("/tmp/home.png"), "home")
        >>> if result.success:
        ...     print(f"Screenshot saved to {result.path}")
    """
    logger = get_logger()

    try:
        # Capture screenshot (binary output)
        result = subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            stderr = result.stderr
            if isinstance(stderr, bytes):
                error_msg = stderr.decode("utf-8", errors="replace")
            elif stderr:
                error_msg = str(stderr)
            else:
                error_msg = "Screenshot capture failed"
            logger.warn(
                LogCategory.STATE,
                f"Android screenshot capture failed: {error_msg}",
            )
            return MobileScreenshotResult(
                path=output_path,
                screen_name=screen_name,
                device_type=MobileDeviceType.ANDROID,
                success=False,
                error=error_msg,
            )

        # Write binary data to file
        output_path.write_bytes(result.stdout)

        # Get device info
        device_name, os_version = _get_android_device_info()

        logger.info(
            LogCategory.STATE,
            f"Android screenshot captured: {screen_name} (device={device_name}, path={output_path})",
        )

        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.ANDROID,
            device_name=device_name,
            os_version=os_version,
            success=True,
        )

    except subprocess.TimeoutExpired:
        logger.warn(
            LogCategory.STATE,
            "Android screenshot capture timed out",
        )
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.ANDROID,
            success=False,
            error="Screenshot capture timed out",
        )

    except FileNotFoundError:
        logger.warn(
            LogCategory.STATE,
            "adb not found - Android SDK may not be installed",
        )
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.ANDROID,
            success=False,
            error="adb not found - Android SDK may not be installed",
        )


# =============================================================================
# Flutter Cross-Platform Functions
# =============================================================================


def detect_flutter_device() -> dict[str, str] | None:
    """Detect the active Flutter device (iOS or Android).

    Uses `flutter devices --machine` to list connected devices and
    returns the first available device.

    Returns:
        Dictionary with device info including 'platform' ('ios' or 'android'),
        or None if no device is available

    Example:
        >>> device = detect_flutter_device()
        >>> if device:
        ...     print(f"Using {device['platform']} device: {device['name']}")
    """
    try:
        result = subprocess.run(
            ["flutter", "devices", "--machine"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None

        devices = json.loads(result.stdout)
        if not devices:
            return None

        # Return first available device
        return devices[0]

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


# =============================================================================
# Screen Navigation Functions
# =============================================================================


def navigate_ios_deeplink(deeplink: str) -> bool:
    """Navigate iOS Simulator to a deeplink URL.

    Uses xcrun simctl openurl to open the deeplink in the booted simulator.

    Args:
        deeplink: The deeplink URL to open (e.g., "myapp://profile/123")

    Returns:
        True if navigation succeeded, False otherwise

    Example:
        >>> if navigate_ios_deeplink("myapp://home"):
        ...     time.sleep(0.5)  # Wait for navigation
        ...     capture_ios_screenshot(...)
    """
    logger = get_logger()

    try:
        result = subprocess.run(
            ["xcrun", "simctl", "openurl", "booted", deeplink],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            logger.warn(
                LogCategory.STATE,
                f"iOS deeplink navigation failed: {result.stderr}",
            )
            return False

        logger.debug(
            LogCategory.STATE,
            f"Navigated iOS simulator to: {deeplink}",
        )
        return True

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def navigate_android_deeplink(deeplink: str) -> bool:
    """Navigate Android Emulator to a deeplink URL.

    Uses adb shell am start to open the deeplink.

    Args:
        deeplink: The deeplink URL to open (e.g., "myapp://profile/123")

    Returns:
        True if navigation succeeded, False otherwise

    Example:
        >>> if navigate_android_deeplink("myapp://home"):
        ...     time.sleep(0.5)  # Wait for navigation
        ...     capture_android_screenshot(...)
    """
    logger = get_logger()

    try:
        result = subprocess.run(
            [
                "adb", "shell", "am", "start",
                "-a", "android.intent.action.VIEW",
                "-d", deeplink,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            logger.warn(
                LogCategory.STATE,
                f"Android deeplink navigation failed: {result.stderr}",
            )
            return False

        logger.debug(
            LogCategory.STATE,
            f"Navigated Android emulator to: {deeplink}",
        )
        return True

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def capture_flutter_screenshot(
    output_path: Path,
    screen_name: str,
) -> MobileScreenshotResult:
    """Capture screenshot from Flutter project's active device.

    Detects whether the Flutter project is running on iOS or Android,
    then routes to the appropriate capture method.

    Args:
        output_path: Path where the screenshot should be saved
        screen_name: Name of the screen being captured

    Returns:
        MobileScreenshotResult with capture details and status

    Example:
        >>> result = capture_flutter_screenshot(Path("/tmp/home.png"), "home")
        >>> if result.success:
        ...     print(f"Captured on {result.device_type}")
    """
    logger = get_logger()

    # Detect which platform Flutter is using
    device = detect_flutter_device()

    if device is None:
        logger.warn(
            LogCategory.STATE,
            "No Flutter device detected - checking native simulators/emulators",
        )
        # Fall back to checking native platforms
        if check_ios_simulator_available():
            result = capture_ios_screenshot(output_path, screen_name)
            # Mark as Flutter iOS
            return MobileScreenshotResult(
                path=result.path,
                screen_name=result.screen_name,
                device_type=MobileDeviceType.FLUTTER_IOS,
                device_name=result.device_name,
                os_version=result.os_version,
                success=result.success,
                error=result.error,
            )
        elif check_android_emulator_available():
            result = capture_android_screenshot(output_path, screen_name)
            return MobileScreenshotResult(
                path=result.path,
                screen_name=result.screen_name,
                device_type=MobileDeviceType.FLUTTER_ANDROID,
                device_name=result.device_name,
                os_version=result.os_version,
                success=result.success,
                error=result.error,
            )
        else:
            return MobileScreenshotResult(
                path=output_path,
                screen_name=screen_name,
                device_type=MobileDeviceType.FLUTTER_IOS,  # Default
                success=False,
                error="No Flutter device or simulator/emulator available",
            )

    # Route based on detected platform
    platform = device.get("platform", "").lower()

    if platform == "ios":
        logger.info(
            LogCategory.STATE,
            f"Flutter using iOS device: {device.get('name', 'Unknown')}",
        )
        result = capture_ios_screenshot(output_path, screen_name)
        return MobileScreenshotResult(
            path=result.path,
            screen_name=result.screen_name,
            device_type=MobileDeviceType.FLUTTER_IOS,
            device_name=result.device_name,
            os_version=result.os_version,
            success=result.success,
            error=result.error,
        )

    elif platform == "android":
        logger.info(
            LogCategory.STATE,
            f"Flutter using Android device: {device.get('name', 'Unknown')}",
        )
        result = capture_android_screenshot(output_path, screen_name)
        return MobileScreenshotResult(
            path=result.path,
            screen_name=result.screen_name,
            device_type=MobileDeviceType.FLUTTER_ANDROID,
            device_name=result.device_name,
            os_version=result.os_version,
            success=result.success,
            error=result.error,
        )

    else:
        logger.warn(
            LogCategory.STATE,
            f"Unknown Flutter platform: {platform}",
        )
        return MobileScreenshotResult(
            path=output_path,
            screen_name=screen_name,
            device_type=MobileDeviceType.FLUTTER_IOS,
            success=False,
            error=f"Unknown Flutter platform: {platform}",
        )
