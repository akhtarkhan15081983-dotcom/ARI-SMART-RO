import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/installation_model.dart';
import 'api_service.dart';

class InstallationService {
  final storage = const FlutterSecureStorage();

  Future<bool> saveInstallation(InstallationModel installation) async {
    final token = await storage.read(key: "access");

    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/installations/complete/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
      body: jsonEncode(installation.toJson()),
    );

    print("Status Code : ${response.statusCode}");
    print("Response : ${response.body}");

    return response.statusCode == 201;
  }
}
