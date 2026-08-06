import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/customer_model.dart';
import 'api_service.dart';

class CustomerService {
  final storage = const FlutterSecureStorage();

  Future<List<CustomerModel>> getCustomers() async {
    final token = await storage.read(key: "access");

    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/customers/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      return data
          .map((e) => CustomerModel.fromJson(e))
          .toList();
    }

    throw Exception("Failed to load customers");
  }
}