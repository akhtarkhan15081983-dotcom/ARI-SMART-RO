import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/customer_model.dart';
import 'api_service.dart';

class CustomerService {
  final storage = const FlutterSecureStorage();

  // ============================================================
  // GET ALL CUSTOMERS
  // ============================================================
  // Used by Admin / Manager / Office customer list.
  // Backend endpoint:
  // /api/customers/
  // ============================================================
  Future<List<CustomerModel>> getCustomers() async {
    final token = await storage.read(key: "access");

    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/customers/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    print("CUSTOMER STATUS : ${response.statusCode}");
    print("CUSTOMER BODY : ${response.body}");

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      print("TOTAL CUSTOMERS : ${data.length}");

      return data
          .map((e) => CustomerModel.fromJson(e))
          .toList();
    }

    throw Exception(
      "Failed to load customers: ${response.statusCode}",
    );
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
    final token = await storage.read(key: "access");

    final response = await http.get(
      Uri.parse(
        "${ApiService.baseUrl}/customers/my-customers/",
      ),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    print("MY CUSTOMERS STATUS : ${response.statusCode}");
    print("MY CUSTOMERS BODY : ${response.body}");

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      print("MY CUSTOMERS TOTAL : ${data.length}");

      return data
          .map((e) => CustomerModel.fromJson(e))
          .toList();
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
      Uri.parse(
        "${ApiService.baseUrl}/customers/$customerId/assign/",
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        "employee_id": employeeId,
      }),
    );

    print("ASSIGN STATUS : ${response.statusCode}");
    print("ASSIGN BODY : ${response.body}");

    return response.statusCode == 200;
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

    double installationCharge = 0,
    double monthlyRent = 0,
    double securityDeposit = 0,
  }) async {
    final response = await http.post(
      Uri.parse(
        "${ApiService.baseUrl}/customers/walk-in/",
      ),
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

        "installation_charge": installationCharge,
        "monthly_rent": monthlyRent,
        "security_deposit": securityDeposit,
      }),
    );

    print("WALK-IN STATUS : ${response.statusCode}");
    print("WALK-IN BODY : ${response.body}");

    return jsonDecode(response.body);
  }
}