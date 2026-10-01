import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/login_response.dart';
import '../services/api_service.dart';

class LoginController {
  String lastError = '';
  String mfaChallenge = '';
  String mfaDestination = '';

  bool get requiresMfa => mfaChallenge.isNotEmpty;

  Future<bool> login({required String phone, required String password}) async {
    final identifier = phone.trim();
    try {
      lastError = '';
      mfaChallenge = '';
      mfaDestination = '';
      http.Response response;
      final looksLikePhone = RegExp(r'^\d{10}$').hasMatch(identifier);

      if (looksLikePhone) {
        final primary = await http
            .post(
              Uri.parse('${ApiService.baseUrl}/auth/login/'),
              headers: await ApiService.deviceHeaders(),
              body: jsonEncode({'phone': identifier, 'password': password}),
            )
            .timeout(const Duration(seconds: 20));

        if (primary.statusCode == 200 || primary.statusCode == 202) {
          response = primary;
        } else {
          final customerFallback =
              await _customerReferenceLogin(identifier, password);
          response = customerFallback.statusCode == 200
              ? customerFallback
              : primary;
        }
      } else {
        response = await _customerReferenceLogin(identifier, password);
      }

      if (response.statusCode == 202) {
        final payload = jsonDecode(response.body) as Map<String, dynamic>;
        if (payload['mfa_required'] == true) {
          mfaChallenge = payload['challenge']?.toString() ?? '';
          mfaDestination = payload['destination']?.toString() ?? '';
          if (mfaChallenge.isNotEmpty) return false;
        }
      }

      if (response.statusCode != 200) {
        try {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          lastError = data['message']?.toString() ?? 'Unable to login.';
        } catch (_) {
          lastError = 'Unable to login. Please try again.';
        }
        return false;
      }

      return _saveLoginResponse(response);
    } catch (_) {
      lastError = 'Server connection failed. Check your internet and try again.';
      return false;
    }
  }

  Future<bool> verifyAdminMfa(String otp) async {
    if (mfaChallenge.isEmpty) {
      lastError = 'Admin verification session is missing. Sign in again.';
      return false;
    }
    try {
      lastError = '';
      final response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/auth/admin/mfa/verify/'),
            headers: await ApiService.deviceHeaders(),
            body: jsonEncode({
              'challenge': mfaChallenge,
              'otp': otp.trim(),
            }),
          )
          .timeout(const Duration(seconds: 20));

      if (response.statusCode != 200) {
        try {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          lastError = data['message']?.toString() ?? 'Admin verification failed.';
        } catch (_) {
          lastError = 'Admin verification failed. Please try again.';
        }
        return false;
      }

      final saved = await _saveLoginResponse(response);
      if (saved) {
        mfaChallenge = '';
        mfaDestination = '';
      }
      return saved;
    } catch (_) {
      lastError = 'Server connection failed during admin verification.';
      return false;
    }
  }

  Future<bool> _saveLoginResponse(http.Response response) async {
    final data = LoginResponse.fromJson(jsonDecode(response.body));
    await ApiService.saveLoginData(
      accessToken: data.access,
      refreshToken: data.refresh,
      role: data.user.role,
      userId: data.user.id.toString(),
    );
    return true;
  }

  Future<http.Response> _customerReferenceLogin(
    String identifier,
    String password,
  ) async {
    return http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/existing-customer/login/'),
          headers: await ApiService.deviceHeaders(),
          body: jsonEncode({'identifier': identifier, 'password': password}),
        )
        .timeout(const Duration(seconds: 20));
  }
}
