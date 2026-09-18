import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/installation_model.dart';
import 'api_service.dart';

class InstallationService {
  Future<bool> saveInstallation(InstallationModel installation) async {
    final token = await ApiService.getAccessToken();

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
