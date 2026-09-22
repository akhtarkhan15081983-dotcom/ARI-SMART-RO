import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class ClientObservabilityService {
  ClientObservabilityService._();

  static const MethodChannel _deviceChannel = MethodChannel(
    'com.arismartro.app/device_capabilities',
  );

  static bool _reporting = false;

  static Future<void> reportError(
    Object error,
    StackTrace stack, {
    String? screen,
    String? operation,
    String? phase,
  }) async {
    if (_reporting) return;
    _reporting = true;
    try {
      final hasSession = await ApiService.ensureValidSession();
      if (!hasSession) return;

      Map<String, dynamic> device = const {};
      try {
        device =
            await _deviceChannel.invokeMapMethod<String, dynamic>(
              'getDeviceHealth',
            ) ??
            const {};
      } catch (_) {
        // Device metadata is optional; error telemetry must remain best-effort.
      }

      final context = <String, dynamic>{
        if (screen?.trim().isNotEmpty == true) 'screen': screen!.trim(),
        if (operation?.trim().isNotEmpty == true) 'operation': operation!.trim(),
        if (phase?.trim().isNotEmpty == true) 'phase': phase!.trim(),
      };

      final payload = <String, dynamic>{
        'platform': device['platform']?.toString() ?? 'FLUTTER',
        'app_version': device['app_version']?.toString() ?? '',
        'app_build': device['app_build']?.toString() ?? '',
        'error_type': error.runtimeType.toString(),
        'message': _safeText(error.toString(), 1000),
        'stack': _safeText(stack.toString(), 8000),
        'context': context,
      };

      await http
          .post(
            Uri.parse('${ApiService.baseUrl}/reports/client-errors/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 8));
    } catch (_) {
      // Never turn telemetry failure into an application failure.
    } finally {
      _reporting = false;
    }
  }

  static String _safeText(String value, int maxLength) {
    final sanitized = value
        .replaceAll(RegExp(r'Bearer\s+[A-Za-z0-9._-]+'), 'Bearer [REDACTED]')
        .replaceAll(RegExp(r'password\s*[:=]\s*\S+', caseSensitive: false), 'password=[REDACTED]')
        .replaceAll(RegExp(r'token\s*[:=]\s*\S+', caseSensitive: false), 'token=[REDACTED]');
    return sanitized.length <= maxLength
        ? sanitized
        : sanitized.substring(0, maxLength);
  }
}
