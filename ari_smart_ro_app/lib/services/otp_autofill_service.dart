import 'dart:async';

import 'package:smart_auth/smart_auth.dart';

class OtpAutofillService {
  OtpAutofillService._();

  static final OtpAutofillService instance = OtpAutofillService._();

  final SmartAuth _smartAuth = SmartAuth.instance;

  Future<String?> listenForUserConsent({
    Duration timeout = const Duration(minutes: 2),
  }) async {
    try {
      final result = await _smartAuth
          .getSmsWithUserConsentApi(matcher: r'\b\d{6}\b')
          .timeout(timeout);
      if (!result.hasData) return null;
      final code = result.requireData.code?.trim();
      return RegExp(r'^\d{6}$').hasMatch(code ?? '') ? code : null;
    } on TimeoutException {
      await _smartAuth.removeUserConsentApiListener();
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<String?> listenForRetriever({
    Duration timeout = const Duration(minutes: 2),
  }) async {
    try {
      final result = await _smartAuth
          .getSmsWithRetrieverApi(matcher: r'\b\d{6}\b')
          .timeout(timeout);
      if (!result.hasData) return null;
      final code = result.requireData.code?.trim();
      return RegExp(r'^\d{6}$').hasMatch(code ?? '') ? code : null;
    } on TimeoutException {
      await _smartAuth.removeSmsRetrieverApiListener();
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<String?> getAppSignature() async {
    try {
      final result = await _smartAuth.getAppSignature();
      return result.hasData ? result.requireData.trim() : null;
    } catch (_) {
      return null;
    }
  }

  Future<void> stop() async {
    await _smartAuth.removeUserConsentApiListener();
    await _smartAuth.removeSmsRetrieverApiListener();
  }
}
