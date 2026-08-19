import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/asset_model.dart';
import 'api_service.dart';

class AssetService {
  Future<List<AssetModel>> getAssets() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/assets/"),
      headers: await ApiService.authHeaders(),
    );

    print(response.body);
    print("STATUS CODE : ${response.statusCode}");
    print("BODY : ${response.body}");

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);

      return data
          .map((e) => AssetModel.fromJson(e))
          .toList();
    }

    throw Exception("Unable to load assets");
  }
}