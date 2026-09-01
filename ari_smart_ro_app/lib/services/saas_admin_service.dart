import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class SaasAdminService {
  const SaasAdminService();

  Future<Map<String, dynamic>> dashboard() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/saas/super-admin/dashboard/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<bool> canAccess() async {
    try {
      await dashboard();
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> plans() async {
    final response = await http
        .get(Uri.parse('${ApiService.baseUrl}/saas/plans/'))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data['plans'] as List<dynamic>? ?? const [])
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
  }

  Future<Map<String, dynamic>> onboardCompany(
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/onboard/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> companyDetails(int companyId) async {
    final response = await http
        .get(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/$companyId/',
          ),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return Map<String, dynamic>.from(data['company'] as Map);
  }

  Future<void> updateCompany(
    int companyId,
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/$companyId/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<void> updateSubscriptionStatus(int companyId, String status) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/$companyId/subscription-status/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'status': status}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<Map<String, dynamic>> updateCompanyLifecycle(
    int companyId,
    String action,
    String reason,
  ) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/$companyId/lifecycle/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'action': action, 'reason': reason}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<List<Map<String, dynamic>>> lifecycleHistory(int companyId) async {
    final response = await http
        .get(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/$companyId/lifecycle-history/',
          ),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return (data['events'] as List<dynamic>? ?? const [])
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
  }

  Future<void> permanentlyDeleteCompany(
    int companyId,
    String confirmation,
    String reason,
  ) async {
    final response = await http
        .delete(
          Uri.parse(
            '${ApiService.baseUrl}/saas/super-admin/companies/$companyId/lifecycle/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'confirmation': confirmation, 'reason': reason}),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['message'] ?? data['detail'] ?? 'SaaS request failed.')
          .toString();
    } catch (_) {
      return 'SaaS request failed (HTTP ${response.statusCode}).';
    }
  }
}
