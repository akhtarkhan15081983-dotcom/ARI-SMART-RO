import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../models/profile_model.dart';
import 'api_service.dart';

class ProfileService {
  Future<ProfileModel> getProfile() async {
    final response = await http.get(
      Uri.parse("${ApiService.baseUrl}/employees/profile/"),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      return ProfileModel.fromJson(jsonDecode(response.body));
    }
    throw Exception("Unable to load profile");
  }

  Future<void> enrollFace({
    required String photoPath,
    required String deviceId,
  }) async {
    final request = http.MultipartRequest(
      "POST",
      Uri.parse("${ApiService.baseUrl}/employees/face-enrollment/"),
    );
    final headers = await ApiService.authHeaders();
    headers.removeWhere((key, _) => key.toLowerCase() == "content-type");
    request.headers.addAll(headers);
    request.fields["device_id"] = deviceId;
    request.files.add(
      await http.MultipartFile.fromPath(
        "photo",
        photoPath,
        filename: "face_enrollment.jpg",
        contentType: MediaType("image", "jpeg"),
      ),
    );

    final response = await request.send();
    final body = await response.stream.bytesToString();
    if (response.statusCode != 200 && response.statusCode != 201) {
      String message = "Unable to enroll face";
      try {
        final data = jsonDecode(body);
        message = data["message"]?.toString() ?? message;
      } catch (_) {}
      throw Exception(message);
    }
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    final response = await http.put(
      Uri.parse("${ApiService.baseUrl}/employees/profile/"),
      headers: await ApiService.authHeaders(),
      body: jsonEncode(data),
    );
    if (response.statusCode != 200) {
      throw Exception("Unable to update profile");
    }
  }

  Future<void> changePassword({
    required String oldPassword,
    required String newPassword,
  }) async {
    final response = await http.post(
      Uri.parse("${ApiService.baseUrl}/auth/change-password/"),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        "old_password": oldPassword,
        "new_password": newPassword,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      await ApiService.storage.write(key: "access", value: data["access"]);
      await ApiService.storage.write(key: "refresh", value: data["refresh"]);
      return;
    }
    throw Exception("Unable to change password");
  }
}
