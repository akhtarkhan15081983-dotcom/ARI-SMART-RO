import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/customer_model.dart';
import 'api_service.dart';

class CustomerService {
  List<CustomerModel> _sortByOldCardSerial(List<CustomerModel> customers) {
    final sorted = List<CustomerModel>.from(customers);

    ({String prefix, int? number, String raw}) key(CustomerModel customer) {
      final raw = customer.oldCardNumber.trim();
      if (raw.isEmpty) {
        return (prefix: '\uFFFF', number: null, raw: '');
      }

      final normalized = raw.toUpperCase().replaceAll(RegExp(r'\s+'), ' ').trim();
      final match = RegExp(r'^(.*?)(\d+)\s*$').firstMatch(normalized);
      if (match == null) {
        return (prefix: normalized, number: null, raw: normalized);
      }

      final prefix = (match.group(1) ?? '').trim();
      final number = int.tryParse(match.group(2) ?? '');
      return (prefix: prefix, number: number, raw: normalized);
    }

    sorted.sort((a, b) {
      final ka = key(a);
      final kb = key(b);

      final prefixCompare = ka.prefix.compareTo(kb.prefix);
      if (prefixCompare != 0) return prefixCompare;

      if (ka.number != null && kb.number != null) {
        final numberCompare = ka.number!.compareTo(kb.number!);
        if (numberCompare != 0) return numberCompare;
      } else if (ka.number != null) {
        return -1;
      } else if (kb.number != null) {
        return 1;
      }

      final rawCompare = ka.raw.compareTo(kb.raw);
      if (rawCompare != 0) return rawCompare;

      return a.customerName.toLowerCase().compareTo(
        b.customerName.toLowerCase(),
      );
    });

    return sorted;
  }
  // ============================================================
  // GET ALL CUSTOMERS
  // ============================================================
  // Used by Admin / Manager / Office customer list.
  // Backend endpoint:
  // /api/customers/
  // ============================================================
  Future<List<CustomerModel>> getCustomers() async {
    final token = await ApiService.getAccessToken();

    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/customers/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      return _sortByOldCardSerial(
        data.map((e) => CustomerModel.fromJson(e)).toList(),
      );
    }

    throw Exception("Failed to load customers: ${response.statusCode}");
  }

  // ============================================================
  // GET MY / ASSIGNED CUSTOMERS
  // ============================================================
  // Used by Engineer.
  // Backend endpoint:
  // /api/customers/my-customers/
  //
  // Backend will return only customers linked to jobs
  // assigned to the logged-in engineer.
  // ============================================================
  Future<List<CustomerModel>> getMyCustomers() async {
    final token = await ApiService.getAccessToken();

    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/customers/my-customers/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      return _sortByOldCardSerial(
        data.map((e) => CustomerModel.fromJson(e)).toList(),
      );
    }

    throw Exception(
      "Failed to load assigned customers: ${response.statusCode}",
    );
  }

  // ============================================================
  // ASSIGN CUSTOMER
  // ============================================================
  // Backend endpoint:
  // POST /api/customers/<customerId>/assign/
  //
  // employee_id can point to:
  // ENGINEER or OFFICE employee.
  // ============================================================
  Future<bool> assignCustomer({
    required int customerId,
    required int employeeId,
  }) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/customers/$customerId/assign/"),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({"employee_id": employeeId}),
    );

    return response.statusCode == 200;
  }

  // ============================================================
  // BULK CUSTOMER IMPORT
  // ============================================================
  Future<Map<String, dynamic>> bulkImportCustomers({
    required String filename,
    required Uint8List bytes,
    bool previewOnly = false,
  }) async {
    final token = await ApiService.getAccessToken();
    final request = http.MultipartRequest(
      "POST",
      Uri.parse("${ApiService.baseUrl}/customers/bulk-import/"),
    );

    request.headers["Authorization"] = "Bearer $token";
    request.fields["preview_only"] = previewOnly ? "true" : "false";
    request.files.add(
      http.MultipartFile.fromBytes("file", bytes, filename: filename),
    );

    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode != 200) {
      throw Exception(data["detail"]?.toString() ?? "Customer import failed.");
    }

    return data;
  }

  Future<Map<String, dynamic>> customerLifecycle({
    required int customerId,
    required String action,
    double purchaseAmount = 0,
    double securityAdjusted = 0,
    DateTime? conversionDate,
    String notes = "",
    String reason = "",
    String confirm = "",
  }) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/customers/$customerId/lifecycle/"),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        "action": action,
        "purchase_amount": purchaseAmount,
        "security_adjusted": securityAdjusted,
        "conversion_date": conversionDate == null
            ? ""
            : "${conversionDate.year.toString().padLeft(4, '0')}-${conversionDate.month.toString().padLeft(2, '0')}-${conversionDate.day.toString().padLeft(2, '0')}",
        "notes": notes,
        "reason": reason,
        "confirm": confirm,
      }),
    );

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode != 200) {
      throw Exception(
        (data["detail"] ?? data["message"] ?? "Customer action failed.").toString(),
      );
    }
    return data;
  }

  // ============================================================
  // CREATE WALK-IN CUSTOMER
  // ============================================================
  Future<Map<String, dynamic>> createWalkInCustomer({
    required String name,
    required String phone,

    String alternatePhone = "",

    required String address,
    required String area,
    required String city,
    required String state,
    required String pincode,

    double? latitude,
    double? longitude,

    required int roModel,
    required int assetId,

    double totalAmountReceived = 600,
    double monthlyRent = 0,
  }) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/customers/walk-in/"),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        "name": name,
        "phone": phone,
        "alternate_phone": alternatePhone,

        "address": address,
        "area": area,
        "city": city,
        "state": state,
        "pincode": pincode,

        "latitude": latitude,
        "longitude": longitude,

        "ro_model": roModel,
        "asset_id": assetId,

        "total_amount_received": totalAmountReceived,
        "monthly_rent": monthlyRent,
      }),
    );

    return jsonDecode(response.body);
  }
}
