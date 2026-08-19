import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class ReferralService {
  Future<Map<String, dynamic>> getReferralSummary() async {
    return _request('GET', '/referrals/me/');
  }

  Future<Map<String, dynamic>> getWalletHistory() async {
    return _request('GET', '/referrals/wallet/history/');
  }

  Future<Map<String, dynamic>> claimReferral(String referralCode) async {
    return _request(
      'POST',
      '/referrals/claim/',
      body: {'referral_code': referralCode.trim().toUpperCase()},
    );
  }

  Future<Map<String, dynamic>> claimWelcomeReward() async {
    return _request('POST', '/referrals/welcome/claim/');
  }

  Future<Map<String, dynamic>> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final headers = await ApiService.authHeaders();
    final uri = Uri.parse('${ApiService.baseUrl}$path');

    late http.Response response;
    if (method == 'POST') {
      response = await http.post(
        uri,
        headers: headers,
        body: jsonEncode(body ?? <String, dynamic>{}),
      );
    } else {
      response = await http.get(uri, headers: headers);
    }

    Map<String, dynamic> data = <String, dynamic>{};
    if (response.body.isNotEmpty) {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) data = decoded;
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(data['message'] ?? 'Referral request failed.');
    }
    return data;
  }
}
