import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';
import 'referral_service.dart';

class CustomerOnboardingService {
  Future<void> register({
    required String firstName,
    required String lastName,
    required String phone,
    required String password,
  }) async {
    final response = await _post('/auth/register/', {
      'first_name': firstName.trim(),
      'last_name': lastName.trim(),
      'phone': phone.trim(),
      'password': password,
    });
    if (response.statusCode != 201) throw Exception(_message(response));
  }

  Future<void> sendOtp(String phone) async {
    final response = await _post('/auth/send-otp/', {'phone': phone.trim()});
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<Map<String, dynamic>> verifyAndLogin({
    required String phone,
    required String otp,
    required String password,
    String referralCode = '',
  }) async {
    final response = await _post('/auth/verify-otp/', {
      'phone': phone.trim(),
      'otp': otp.trim(),
      'new_password': password,
    });
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final user = Map<String, dynamic>.from(data['user'] as Map);
    await ApiService.saveLoginData(
      accessToken: data['access'].toString(),
      refreshToken: data['refresh']?.toString(),
      role: user['role']?.toString(),
      userId: user['id']?.toString(),
    );
    final code = referralCode.trim();
    if (code.isNotEmpty) {
      try {
        await ReferralService().claimReferral(code);
      } catch (error) {
        data['referral_warning'] = error.toString().replaceFirst(
          'Exception: ',
          '',
        );
      }
    }
    return data;
  }

  Future<Map<String, dynamic>> startSimVerification({
    required String phone,
    required String password,
  }) async {
    final response = await _post('/auth/sim-verification/start/', {
      'phone': phone.trim(),
      'new_password': password,
    });
    if (response.statusCode != 201) throw Exception(_message(response));
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> pollSimVerification({
    required int challengeId,
    required String pollSecret,
    String referralCode = '',
  }) async {
    final response = await _post('/auth/sim-verification/poll/', {
      'challenge_id': challengeId,
      'poll_secret': pollSecret,
    });
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (data['status'] != 'VERIFIED') return data;
    final user = Map<String, dynamic>.from(data['user'] as Map);
    await ApiService.saveLoginData(
      accessToken: data['access'].toString(),
      refreshToken: data['refresh']?.toString(),
      role: user['role']?.toString(),
      userId: user['id']?.toString(),
    );
    final code = referralCode.trim();
    if (code.isNotEmpty) {
      try {
        await ReferralService().claimReferral(code);
      } catch (error) {
        data['referral_warning'] = error.toString().replaceFirst(
          'Exception: ',
          '',
        );
      }
    }
    return data;
  }

  Future<http.Response> _post(String path, Map<String, dynamic> body) async {
    return http
        .post(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 20));
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (data['message'] != null) return data['message'].toString();
      final errors = data['errors'];
      if (errors is Map && errors.isNotEmpty) {
        final value = errors.values.first;
        if (value is List && value.isNotEmpty) return value.first.toString();
        return value.toString();
      }
    } catch (_) {}
    return 'Unable to continue. Please try again.';
  }
}
