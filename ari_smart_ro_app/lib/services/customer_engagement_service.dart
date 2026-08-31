import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class CustomerEngagementData {
  const CustomerEngagementData({
    required this.items,
    required this.paymentAlert,
    required this.unreadCount,
  });
  final List<Map<String, dynamic>> items;
  final Map<String, dynamic>? paymentAlert;
  final int unreadCount;

  static const empty = CustomerEngagementData(
    items: [],
    paymentAlert: null,
    unreadCount: 0,
  );
}

class CustomerEngagementService {
  const CustomerEngagementService();

  Future<CustomerEngagementData> fetch() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/auth/customer-engagement/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 15));
    if (response.statusCode == 401 || response.statusCode == 403) {
      return CustomerEngagementData.empty;
    }
    if (response.statusCode != 200) {
      throw Exception('Unable to load your alerts.');
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return CustomerEngagementData(
      items: (data['items'] as List<dynamic>? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(),
      paymentAlert: data['payment_alert'] == null
          ? null
          : Map<String, dynamic>.from(data['payment_alert'] as Map),
      unreadCount: (data['unread_count'] as num?)?.toInt() ?? 0,
    );
  }

  Future<void> markRead(int id) async {
    await http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/customer-engagement/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'engagement_id': id}),
        )
        .timeout(const Duration(seconds: 10));
  }
}
