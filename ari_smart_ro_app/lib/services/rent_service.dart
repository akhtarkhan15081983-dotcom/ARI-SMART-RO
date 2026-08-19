import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/rent_model.dart';
import 'api_service.dart';

class RentService {

  // ============================================================
  // GET CUSTOMER RENT DETAILS
  // ============================================================

  Future<RentModel> getRentDetails() async {

    final response = await http.get(
      Uri.parse(
        "${ApiService.baseUrl}/customers/rent/",
      ),
      headers: await ApiService.authHeaders(),
    );

    print("========================================");
    print("RENT API");
    print("STATUS : ${response.statusCode}");
    print("BODY   : ${response.body}");
    print("========================================");

    if (response.statusCode == 200) {

      final data = jsonDecode(response.body);

      return RentModel.fromJson(data);
    }

    if (response.statusCode == 401) {
      throw Exception(
        "Session expired. Please login again.",
      );
    }

    if (response.statusCode == 403) {
      throw Exception(
        "You are not authorized to view rent details.",
      );
    }

    if (response.statusCode == 404) {
      throw Exception(
        "Customer profile not found.",
      );
    }

    try {

      final data = jsonDecode(response.body);

      if (data is Map &&
          data["message"] != null) {

        throw Exception(
          data["message"].toString(),
        );
      }

    } catch (_) {}

    throw Exception(
      "Failed to load rent details. "
      "Status: ${response.statusCode}",
    );
  }
}