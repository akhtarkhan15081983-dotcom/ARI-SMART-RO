import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/bag_item_model.dart';
import 'api_service.dart';

class BagService {
  final storage = const FlutterSecureStorage();

  Future<List<BagItemModel>> getMyBag() async {
    final token = await storage.read(key: "access");

    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/inventory/my-bag/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
    );

    print("MY BAG STATUS : ${response.statusCode}");
    print(response.body);

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      return data
          .map((e) => BagItemModel.fromJson(e))
          .toList();
    }

    throw Exception("Unable to load bag items");
  }
  Future<Map<String, dynamic>> verifyQRCode(
    String serialNumber,
  ) async {
    final token = await storage.read(key: "access");
    final engineerId = await storage.read(key: "user_id");

    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/inventory/verify/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
      body: jsonEncode({
        "engineer": int.parse(engineerId!),
        "serial_number": serialNumber,
      }),
    );

    print("VERIFY STATUS : ${response.statusCode}");
    print(response.body);

    return jsonDecode(response.body);
  }

}

