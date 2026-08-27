import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class CustomerAuthResult {
  const CustomerAuthResult({
    required this.success,
    required this.message,
  });

  final bool success;
  final String message;
}

class CustomerAuthService {
  Future<CustomerAuthResult> register({
    required String firstName,
    required String lastName,
    required String phone,
    required String password,
  }) {
    return _post(
      '/auth/register/',
      {
        'first_name': firstName,
        'last_name': lastName,
        'phone': phone,
        'password': password,
      },
      successCodes: const {201},
    );
  }

  Future<CustomerAuthResult> sendOtp(String phone) {
    return _post(
      '/auth/send-otp/',
      {'phone': phone},
      successCodes: const {200},
    );
  }

  Future<CustomerAuthResult> verifyOtp({
    required String phone,
    required String otp,
    required String password,
  }) {
    return _post(
      '/auth/verify-otp/',
      {
        'phone': phone,
        'otp': otp,
        'password': password,
      },
      successCodes: const {200},
    );
  }

  Future<CustomerAuthResult> _post(
    String path,
    Map<String, String> body, {
    required Set<int> successCodes,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}$path'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 20));

      final decoded = jsonDecode(response.body);
      final data = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{};
      final message = _messageFrom(data);
      return CustomerAuthResult(
        success: successCodes.contains(response.statusCode),
        message: message,
      );
    } catch (_) {
      return const CustomerAuthResult(
        success: false,
        message: 'Unable to connect. Please try again.',
      );
    }
  }

  String _messageFrom(Map<String, dynamic> data) {
    final message = data['message'];
    if (message is String && message.trim().isNotEmpty) {
      return message;
    }
    final errors = data['errors'];
    if (errors is Map) {
      return errors.values
          .expand((value) => value is List ? value : [value])
          .join(' ');
    }
    return 'Request could not be completed.';
  }
}
