import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class RentManagementService {
  // ============================================================
  // GET ALL CUSTOMER RENT RECORDS
  // ============================================================

  static Future<Map<String, dynamic>> getRentManagement() async {
    final headers = await ApiService.authHeaders();

    final url = Uri.parse("${ApiService.baseUrl}/customers/rent-management/");

    final response = await http.get(url, headers: headers);

    print("========== RENT MANAGEMENT ==========");

    print("Status: ${response.statusCode}");

    print("Body: ${response.body}");

    print("====================================");

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    if (response.statusCode == 401) {
      throw Exception("Authentication expired. Please login again.");
    }

    if (response.statusCode == 403) {
      throw Exception("You do not have permission to view rent management.");
    }

    throw Exception(
      "Failed to load rent management. "
      "Status: ${response.statusCode}",
    );
  }

  // ============================================================
  // ADD RENT PAYMENT
  // ============================================================

  static Future<Map<String, dynamic>> addRentPayment({
    required int customerId,

    required double amount,

    required String paymentMode,

    String? paymentDate,

    String? remarks,
  }) async {
    final headers = await ApiService.authHeaders();

    final url = Uri.parse(
      "${ApiService.baseUrl}/customers/rent-management/payment/",
    );

    final body = <String, dynamic>{
      "customer_id": customerId,

      "amount": amount,

      "payment_mode": paymentMode,
    };

    if (paymentDate != null && paymentDate.isNotEmpty) {
      body["payment_date"] = paymentDate;
    }

    if (remarks != null && remarks.trim().isNotEmpty) {
      body["remarks"] = remarks.trim();
    }

    print("========== RENT PAYMENT ==========");

    print("URL: $url");

    print("BODY: ${jsonEncode(body)}");

    final response = await http.post(
      url,
      headers: headers,
      body: jsonEncode(body),
    );

    print("Status: ${response.statusCode}");

    print("Body: ${response.body}");

    print("==================================");

    if (response.statusCode == 201 || response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    if (response.statusCode == 401) {
      throw Exception("Authentication expired. Please login again.");
    }

    if (response.statusCode == 403) {
      final data = _decodeResponse(response.body);

      throw Exception(
        data["message"]?.toString() ??
            "You do not have permission to record rent payment.",
      );
    }

    if (response.statusCode == 400) {
      final data = _decodeResponse(response.body);

      final message = data["message"]?.toString();

      if (message != null && message.isNotEmpty) {
        throw Exception(message);
      }

      if (data["detail"] != null) {
        throw Exception(data["detail"].toString());
      }

      throw Exception("Invalid payment details.");
    }

    if (response.statusCode == 404) {
      final data = _decodeResponse(response.body);

      throw Exception(data["message"]?.toString() ?? "Customer not found.");
    }

    final data = _decodeResponse(response.body);

    throw Exception(
      data["message"]?.toString() ??
          "Failed to record rent payment. "
              "Status: ${response.statusCode}",
    );
  }

  // ============================================================
  // GET PAYMENT HISTORY
  //
  // Without customerId:
  //   All customer payments
  //
  // With customerId:
  //   Only selected customer's payments
  // ============================================================

  static Future<Map<String, dynamic>> getPaymentHistory({
    int? customerId,
  }) async {
    final headers = await ApiService.authHeaders();

    String endpoint =
        "${ApiService.baseUrl}"
        "/customers/rent-management/payments/";

    if (customerId != null) {
      endpoint = "$endpoint?customer_id=$customerId";
    }

    final url = Uri.parse(endpoint);

    print("========== PAYMENT HISTORY ==========");

    print("URL: $url");

    final response = await http.get(url, headers: headers);

    print("Status: ${response.statusCode}");

    print("Body: ${response.body}");

    print("=====================================");

    // ----------------------------------------------------------
    // SUCCESS
    // ----------------------------------------------------------

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    // ----------------------------------------------------------
    // AUTH
    // ----------------------------------------------------------

    if (response.statusCode == 401) {
      throw Exception("Authentication expired. Please login again.");
    }

    // ----------------------------------------------------------
    // PERMISSION
    // ----------------------------------------------------------

    if (response.statusCode == 403) {
      final data = _decodeResponse(response.body);

      throw Exception(
        data["message"]?.toString() ??
            "You do not have permission to view payment history.",
      );
    }

    // ----------------------------------------------------------
    // OTHER ERROR
    // ----------------------------------------------------------

    final data = _decodeResponse(response.body);

    throw Exception(
      data["message"]?.toString() ??
          "Failed to load payment history. "
              "Status: ${response.statusCode}",
    );
  }

  // ============================================================
  // DECODE ERROR RESPONSE
  // ============================================================

  static Map<String, dynamic> _decodeResponse(String body) {
    try {
      final decoded = jsonDecode(body);

      if (decoded is Map<String, dynamic>) {
        return decoded;
      }

      return {};
    } catch (_) {
      return {};
    }
  }
}
