import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class EngineerMapService {
  Future<List<dynamic>> getEngineers() async {
    final token = await ApiService.getAccessToken();

    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/live-map/'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data is List ? data : <dynamic>[];
    }

    throw Exception('Unable to load engineers');
  }

  Future<Map<String, dynamic>?> getRoute({
    required double startLat,
    required double startLng,
    required double endLat,
    required double endLng,
  }) async {
    final url = Uri.parse(
      'https://router.project-osrm.org/route/v1/driving/'
      '$startLng,$startLat;'
      '$endLng,$endLat'
      '?overview=false',
    );

    final response = await http.get(url).timeout(const Duration(seconds: 10));

    if (response.statusCode != 200) return null;

    final data = jsonDecode(response.body);
    if (data['routes'] is! List || (data['routes'] as List).isEmpty) {
      return null;
    }

    final route = (data['routes'] as List).first as Map<String, dynamic>;
    return {'distance': route['distance'], 'duration': route['duration']};
  }

  /// Resolve a human-readable place only when an admin opens one employee.
  /// This deliberately avoids reverse-geocoding every marker on every 10-second
  /// refresh, which would be wasteful and unfriendly to the public OSM service.
  Future<String?> reverseGeocode({
    required double latitude,
    required double longitude,
  }) async {
    try {
      final uri = Uri.https(
        'nominatim.openstreetmap.org',
        '/reverse',
        <String, String>{
          'format': 'jsonv2',
          'lat': latitude.toString(),
          'lon': longitude.toString(),
          'zoom': '18',
          'addressdetails': '1',
        },
      );
      final response = await http.get(
        uri,
        headers: const {
          'User-Agent': 'ARI-SMART-RO/1.0 (employee-location-admin)',
          'Accept-Language': 'en',
        },
      ).timeout(const Duration(seconds: 8));
      if (response.statusCode != 200) return null;
      final data = jsonDecode(response.body);
      if (data is! Map) return null;
      final displayName = data['display_name']?.toString().trim();
      return displayName == null || displayName.isEmpty ? null : displayName;
    } catch (_) {
      return null;
    }
  }
}
