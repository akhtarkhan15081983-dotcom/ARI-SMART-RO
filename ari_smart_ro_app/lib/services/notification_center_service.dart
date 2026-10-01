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

  Future<void> _syncCustomerRoAlarms() async {
    try {
      final role = (await ApiService.getRole() ?? '')
          .trim()
          .toUpperCase()
          .replaceAll('ROLE_', '');
      if (role != 'CUSTOMER') return;
      await http
          .post(
            Uri.parse('${ApiService.baseUrl}/assets/ro-alarms/refresh/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode({'horizon_days': 7}),
          )
          .timeout(const Duration(seconds: 20));
    } catch (_) {
      // Alarm sync must never block the notification center.
    }
  }

  Future<NotificationCenterData> fetch() async {
    await _syncCustomerRoAlarms();
    const pageSize = 200;
    var page = 1;
    var unreadCount = 0;
    final items = <Map<String, dynamic>>[];

    while (true) {
      final response = await http
          .get(
            Uri.parse('${ApiService.baseUrl}/auth/notifications/').replace(
              queryParameters: {
                'page': '$page',
                'page_size': '$pageSize',
              },
            ),
            headers: await ApiService.authHeaders(),
          )
          .timeout(const Duration(seconds: 20));
      if (response.statusCode != 200) throw Exception(_message(response));
      final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
      if (page == 1) {
        unreadCount = (data['unread_count'] as num?)?.toInt() ?? 0;
      }
      final pageItems = (data['items'] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(growable: false);
      items.addAll(pageItems);
      if (data['has_more'] != true || pageItems.isEmpty) break;
      page = (data['next_page'] as num?)?.toInt() ?? (page + 1);
    }

    return NotificationCenterData(
      items: items,
      unreadCount: unreadCount,
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

  Future<List<Map<String, dynamic>>> adminCampaigns() =>
      _fetchAllAdminRows(
        '/auth/admin/notification-campaigns/',
        'campaigns',
      );

  Future<Map<String, dynamic>> createCampaign(Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/auth/admin/notification-campaigns/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode(payload),
    );
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<List<Map<String, dynamic>>> adminOffers() =>
      _fetchAllAdminRows('/auth/admin/offers/', 'offers');

  Future<List<Map<String, dynamic>>> adminOfferCustomers() =>
      _fetchAllAdminRows(
        '/auth/admin/offers/customers/',
        'customers',
        pageSize: 500,
      );

  Future<List<Map<String, dynamic>>> _fetchAllAdminRows(
    String path,
    String key, {
    int pageSize = 200,
  }) async {
    var page = 1;
    final rows = <Map<String, dynamic>>[];

    while (true) {
      final response = await http.get(
        Uri.parse('${ApiService.baseUrl}$path').replace(
          queryParameters: {
            'page': '$page',
            'page_size': '$pageSize',
          },
        ),
        headers: await ApiService.authHeaders(),
      );
      if (response.statusCode != 200) throw Exception(_message(response));
      final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
      final pageRows = (data[key] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(growable: false);
      rows.addAll(pageRows);
      if (data['has_more'] != true || pageRows.isEmpty) break;
      page = (data['next_page'] as num?)?.toInt() ?? (page + 1);
    }
    return rows;
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
