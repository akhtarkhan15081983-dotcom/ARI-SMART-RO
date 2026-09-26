import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class NotificationCenterData {
  const NotificationCenterData({
    required this.items,
    required this.unreadCount,
  });

  final List<Map<String, dynamic>> items;
  final int unreadCount;
}

class NotificationCenterService {
  const NotificationCenterService();

  Future<NotificationCenterData> fetch() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/auth/notifications/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return NotificationCenterData(
      items: (data['items'] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
      unreadCount: (data['unread_count'] as num?)?.toInt() ?? 0,
    );
  }

  Future<void> markRead(int id) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/notifications/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'notification_id': id}),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<void> markAllRead() async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/notifications/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'mark_all': true}),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<List<Map<String, dynamic>>> adminCampaigns() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/auth/admin/notification-campaigns/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['campaigns'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<Map<String, dynamic>> createCampaign(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/admin/notification-campaigns/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode(payload),
    );
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<List<Map<String, dynamic>>> adminOffers() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/auth/admin/offers/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['offers'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<List<Map<String, dynamic>>> adminOfferCustomers() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/auth/admin/offers/customers/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['customers'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<Map<String, dynamic>> createOffer(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/admin/offers/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode(payload),
    );
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  String _message(http.Response response) {
    try {
      final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
      return (data['detail'] ?? data['message'] ?? 'Request failed.').toString();
    } catch (_) {
      return 'Request failed (HTTP ${response.statusCode}).';
    }
  }
}
