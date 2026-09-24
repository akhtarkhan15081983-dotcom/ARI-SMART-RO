import 'package:flutter/foundation.dart';
import 'package:posthog_flutter/posthog_flutter.dart';

class PostHogService {
  PostHogService._();

  static const String _projectToken =
      'phc_z4WuueMEeuUHbY2QVWvGPkTjsW6p9m5jK6gTvStfPvKN';
  static const String _host = 'https://us.i.posthog.com';

  static bool _initialized = false;

  static bool get _isSupportedPlatform {
    if (kIsWeb) return true;
    return defaultTargetPlatform == TargetPlatform.android ||
        defaultTargetPlatform == TargetPlatform.iOS ||
        defaultTargetPlatform == TargetPlatform.macOS;
  }

  static Future<void> initialize() async {
    if (_initialized || !_isSupportedPlatform) return;

    try {
      final config = PostHogConfig(_projectToken)
        ..host = _host
        ..captureApplicationLifecycleEvents = true
        ..sessionReplay = false
        ..surveys = false
        ..personProfiles = PostHogPersonProfiles.identifiedOnly;

      config.errorTrackingConfig
        ..inAppIncludes.add('package:ari_smart_ro_app')
        ..inAppByDefault = true
        ..captureFlutterErrors = true
        ..capturePlatformDispatcherErrors = true
        ..captureIsolateErrors = true
        ..captureNativeExceptions = !kIsWeb;

      await Posthog().setup(config);
      _initialized = true;

      await capture(
        'ari_app_started',
        properties: const {
          'product': 'ARI SMART RO',
          'telemetry_profile': 'privacy_safe_v1',
        },
      );
    } catch (_) {
      // Analytics must never prevent the application from starting.
    }
  }

  static Future<void> capture(
    String eventName, {
    Map<String, Object>? properties,
  }) async {
    if (!_initialized || !_isSupportedPlatform) return;
    try {
      await Posthog().capture(
        eventName: eventName,
        properties: properties,
      );
    } catch (_) {
      // Best-effort telemetry only.
    }
  }

  static Future<void> identifyEmployee({
    required String employeeId,
    required String role,
  }) async {
    if (!_initialized || !_isSupportedPlatform) return;

    final safeEmployeeId = employeeId.trim();
    if (safeEmployeeId.isEmpty) return;

    try {
      await Posthog().identify(
        userId: safeEmployeeId,
        userProperties: {
          'role': role.trim(),
        },
      );
    } catch (_) {
      // Best-effort telemetry only.
    }
  }

  static Future<void> resetIdentity() async {
    if (!_initialized || !_isSupportedPlatform) return;
    try {
      await Posthog().reset();
    } catch (_) {
      // Best-effort telemetry only.
    }
  }
}
