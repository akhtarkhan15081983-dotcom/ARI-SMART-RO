import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/profile_model.dart';
import 'api_service.dart';

class ProfileService {
  Future<ProfileModel> getProfile() async {
    final token = await ApiService.getAccessToken();

    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/employees/profile/"),
      headers: {
        "Authorization": "Bearer $token",
      },
    );

    if (response.statusCode == 200) {
      return ProfileModel.fromJson(
        jsonDecode(response.body),
      );
    }

    throw Exception("Unable to load profile");
  }
}