#!/usr/bin/env bash
set -euo pipefail

APK="${1:-ari_smart_ro_app/build/app/outputs/flutter-apk/app-debug.apk}"
PACKAGE="${2:-com.arismartro.app.posthogtest}"
PACKAGE_ERROR="${RUNNER_TEMP:-/tmp}/ari-package-error.txt"
PACKAGE_LIST="${RUNNER_TEMP:-/tmp}/ari-packages.txt"

if [[ ! -f "$APK" ]]; then
  echo "::error title=Android APK install failure::Expected APK was not found at $APK."
  exit 87
fi

adb wait-for-device

echo "Waiting for Android package service readiness..."
package_ready=0
for attempt in $(seq 1 45); do
  if adb shell cmd package list packages >"$PACKAGE_LIST" 2>"$PACKAGE_ERROR"; then
    package_ready=1
    break
  fi
  echo "Package service not ready yet (attempt $attempt/45)."
  sleep 2
done

if [[ "$package_ready" -ne 1 ]]; then
  echo "::error title=Android emulator infrastructure failure::Android package service never became healthy after emulator boot."
  cat "$PACKAGE_ERROR" || true
  adb shell service check package || true
  adb devices -l || true
  adb logcat -d -t 300 || true
  exit 86
fi

install_output=""
if ! install_output="$(adb install -r "$APK" 2>&1)"; then
  printf '%s\n' "$install_output"
  if ! adb shell cmd package list packages >/dev/null 2>&1; then
    echo "::error title=Android emulator infrastructure failure::APK install lost access to a healthy Android package service."
    adb shell service check package || true
    exit 86
  fi
  echo "::error title=Android APK install failure::Android package service is healthy but adb install failed."
  adb logcat -d -t 300 || true
  exit 87
fi
printf '%s\n' "$install_output"

if ! adb shell pm path "$PACKAGE" | grep -q '^package:'; then
  echo "::error title=Android APK install failure::adb reported install success but package $PACKAGE is not registered."
  adb shell dumpsys package "$PACKAGE" || true
  exit 87
fi

adb shell am force-stop "$PACKAGE"
launch_output="$(adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 2>&1 || true)"
printf '%s\n' "$launch_output"
if ! grep -q 'Events injected: 1' <<<"$launch_output"; then
  echo "::error title=Android application launch failure::The installed APK did not accept a launcher event."
  adb shell cmd package resolve-activity --brief "$PACKAGE" || true
  adb logcat -d -t 400 || true
  exit 88
fi

sleep 10
pid="$(adb shell pidof "$PACKAGE" | tr -d '\r' || true)"
if [[ -z "$pid" ]]; then
  echo "::error title=Android application runtime failure::APK installed and launched, but the app process did not survive the smoke window."
  adb shell dumpsys activity processes | tail -n 200 || true
  adb logcat -d -t 500 || true
  exit 1
fi

echo "ARI SMART RO Android startup smoke test passed with PID $pid."
