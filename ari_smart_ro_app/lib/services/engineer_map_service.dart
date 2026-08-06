import 'dart:convert';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class EngineerMapService {

  Future<List<dynamic>> getEngineers() async {

    final token = await ApiService.getAccessToken();

    final response = await http.get(

      Uri.parse("${ApiService.baseUrl}/employees/live-map/"),

      headers: {

        "Authorization": "Bearer $token",

      },

    );

    if (response.statusCode == 200) {

      final data = jsonDecode(response.body);

        print(data);

        return data;

    }

    throw Exception("Unable to load engineers");

  }

  Future<Map<String, dynamic>?> getRoute({
  required double startLat,
  required double startLng,
  required double endLat,
  required double endLng,
}) async {

  final url = Uri.parse(
    "https://router.project-osrm.org/route/v1/driving/"
    "$startLng,$startLat;"
    "$endLng,$endLat"
    "?overview=false",
  );

  final response = await http.get(url);

  if (response.statusCode != 200) {
    return null;
  }

  final data = jsonDecode(response.body);

  if (data["routes"] == null || data["routes"].isEmpty) {
    return null;
  }

  final route = data["routes"][0];

  return {
    "distance": route["distance"],
    "duration": route["duration"],
  };
}

}