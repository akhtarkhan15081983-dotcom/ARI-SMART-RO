import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/engineer_model.dart';
import 'api_service.dart';

class EngineerService {

  // ============================================================
  // GET ENGINEERS
  // ============================================================
  // Existing endpoint.
  // Used wherever only engineers are required.
  // ============================================================

  Future<List<EngineerModel>> getEngineers() async {

    final response = await http.get(
      Uri.parse(
        "${ApiService.baseUrl}/employees/engineers/",
      ),
      headers: await ApiService.authHeaders(),
    );

    print("ENGINEER STATUS : ${response.statusCode}");
    print("ENGINEER BODY : ${response.body}");

    if (response.statusCode == 200) {

      final List data = jsonDecode(response.body);

      return data
          .map((e) => EngineerModel.fromJson(e))
          .toList();
    }

    throw Exception(
      "Unable to load engineers",
    );
  }

  // ============================================================
  // GET ASSIGNMENT EMPLOYEES
  // ============================================================
  // Returns:
  // ENGINEER + OFFICE
  //
  // Backend endpoint:
  // /api/employees/assignment-employees/
  // ============================================================

  Future<List<EngineerModel>> getAssignmentEmployees() async {

    final response = await http.get(
      Uri.parse(
        "${ApiService.baseUrl}/employees/assignment-employees/",
      ),
      headers: await ApiService.authHeaders(),
    );

    print(
      "ASSIGNMENT EMPLOYEES STATUS : ${response.statusCode}",
    );

    print(
      "ASSIGNMENT EMPLOYEES BODY : ${response.body}",
    );

    if (response.statusCode == 200) {

      final List data = jsonDecode(response.body);

      print(
        "ASSIGNMENT EMPLOYEES TOTAL : ${data.length}",
      );

      return data
          .map((e) => EngineerModel.fromJson(e))
          .toList();
    }

    throw Exception(
      "Unable to load assignment employees",
    );
  }
}