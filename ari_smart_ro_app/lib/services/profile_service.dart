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

  Future<void> updateProfile(Map<String, dynamic> data) async {
    final token = await ApiService.getAccessToken();

    final response = await http.put(
      Uri.parse("${ApiService.baseUrl}/employees/profile/"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
      body: jsonEncode(data),
    );

    print("UPDATE STATUS : ${response.statusCode}");
    print("UPDATE BODY : ${response.body}");

    if (response.statusCode != 200) {
      throw Exception("Unable to update profile");
    }
  }
  
  Future<void> changePassword({
    required String oldPassword,
    required String newPassword,
  }) async {

    final token = await ApiService.getAccessToken();

    final response = await http.post(

      Uri.parse("${ApiService.baseUrl}/auth/change-password/"),

      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },

      body: jsonEncode({

        "old_password": oldPassword,
        "new_password": newPassword,

      }),

    );

    print("PASSWORD STATUS : ${response.statusCode}");
    print("PASSWORD BODY : ${response.body}");

    if (response.statusCode == 200) {

      final data = jsonDecode(response.body);

      await ApiService.storage.write(
        key: "access",
        value: data["access"],
      );

      await ApiService.storage.write(
        key: "refresh",
        value: data["refresh"],
      );
      print("NEW ACCESS TOKEN SAVED");
      print(data["access"]);

      return;

    }

    if (response.statusCode != 200) {
      throw Exception("Unable to change password");
    }

  }
}