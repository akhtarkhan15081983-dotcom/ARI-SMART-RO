import 'package:flutter/services.dart';

class ReferralLinkService {
  ReferralLinkService._();

  static const _channel = MethodChannel('com.arismartro.app/referral');
  static String? _pendingCode;

  static String? takePendingCode() {
    final code = _pendingCode;
    _pendingCode = null;
    return code;
  }

  static Future<void> initialize(
    Future<void> Function(String code) onCode,
  ) async {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'openReferral') {
        final code = call.arguments?.toString().trim() ?? '';
        if (code.isNotEmpty) {
          _pendingCode = code;
          await onCode(code);
        }
      }
    });
    try {
      final code = await _channel.invokeMethod<String>(
        'getInitialReferralCode',
      );
      if (code != null && code.trim().isNotEmpty) {
        _pendingCode = code.trim();
      }
    } on MissingPluginException {
      // Non-Android platforms continue with manual referral-code entry.
    }
  }
}
