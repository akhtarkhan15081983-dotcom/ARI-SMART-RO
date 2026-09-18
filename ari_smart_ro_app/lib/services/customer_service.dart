import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/customer_model.dart';
import 'api_service.dart';

class CustomerService {
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

      return data.map((e) => CustomerModel.fromJson(e)).toList();
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

      return data.map((e) => CustomerModel.fromJson(e)).toList();
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
