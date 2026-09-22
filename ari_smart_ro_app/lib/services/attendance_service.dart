import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/attendance_model.dart';
import 'api_service.dart';
import 'device_identity_service.dart';

typedef AttendanceHeadersProvider = Future<Map<String, String>> Function();
typedef AttendanceDeviceIdProvider = Future<String> Function();

class AttendanceService {
  AttendanceService({
    http.Client? client,
    AttendanceHeadersProvider? headersProvider,
    AttendanceDeviceIdProvider? deviceIdProvider,
    String? baseUrl,
    Duration requestTimeout = const Duration(seconds: 15),
    Duration uploadTimeout = const Duration(seconds: 30),
  }) : _client = client ?? http.Client(),
       _headersProvider = headersProvider ?? ApiService.authHeaders,
       _deviceIdProvider = deviceIdProvider ?? DeviceIdentityService.getOrCreate,
       _baseUrl = (baseUrl ?? ApiService.baseUrl).replaceFirst(RegExp(r'/$'), ''),
       _requestTimeout = requestTimeout,
       _uploadTimeout = uploadTimeout;

  final http.Client _client;
  final AttendanceHeadersProvider _headersProvider;
  final AttendanceDeviceIdProvider _deviceIdProvider;
  final String _baseUrl;
  final Duration _requestTimeout;
  final Duration _uploadTimeout;

  Uri _uri(String path) => Uri.parse('$_baseUrl$path');

  Future<Map<String, String>> _headers() => _headersProvider();

  Future<http.Response> _get(String path) async {
    try {
      return await _client
          .get(_uri(path), headers: await _headers())
          .timeout(_requestTimeout);
    } catch (_) {
      throw const AttendanceServiceException(
        'Unable to connect to the server. Check the network and try again.',
      );
    }
  }

  Future<http.Response> _post(String path, {Object? body}) async {
    try {
      return await _client
          .post(_uri(path), headers: await _headers(), body: body)
          .timeout(_requestTimeout);
    } catch (_) {
      throw const AttendanceServiceException(
        'Unable to connect to the server. Check the network and try again.',
      );
    }
  }

  Future<AttendanceActionResult> checkIn({
    required double latitude,
    required double longitude,
    required String selfiePath,
  }) async {
    final request = http.MultipartRequest('POST', _uri('/attendance/check-in/'));

    final headers = await _headers();
    headers.removeWhere((key, _) => key.toLowerCase() == 'content-type');
    request.headers.addAll(headers);

    request.fields['latitude'] = latitude.toString();
    request.fields['longitude'] = longitude.toString();
    request.fields['device_id'] = await _deviceIdProvider();
    request.files.add(await http.MultipartFile.fromPath('selfie', selfiePath));

    try {
      final response = await _client.send(request).timeout(_uploadTimeout);
      final body =
          await response.stream.bytesToString().timeout(_requestTimeout);
      final success = response.statusCode == 200 || response.statusCode == 201;
      String message =
          success ? 'Checked in successfully.' : 'Check-in failed.';
      double? distanceMeters;

      try {
        final decoded = jsonDecode(body);
        if (decoded is Map<String, dynamic>) {
          final serverMessage = decoded['message'] ?? decoded['detail'];
          if (serverMessage != null &&
              serverMessage.toString().trim().isNotEmpty) {
            message = serverMessage.toString().trim();
          }
          final distance = decoded['distance_from_office_meters'];
          if (distance is num) distanceMeters = distance.toDouble();
        }
      } catch (_) {
        // Keep the fallback for non-JSON proxy/server responses.
      }

      return AttendanceActionResult(
        success: success,
        message: message,
        statusCode: response.statusCode,
        distanceFromOfficeMeters: distanceMeters,
      );
    } catch (_) {
      return const AttendanceActionResult(
        success: false,
        message:
            'Unable to connect to the server. Check the network and try again.',
        statusCode: 0,
      );
    }
  }

  Future<AttendanceActionResult> checkOut() async {
    try {
      final response = await _post('/attendance/check-out/');
      final success = response.statusCode == 200 || response.statusCode == 201;
      return AttendanceActionResult(
        success: success,
        message: _message(
          response,
          success ? 'Checked out successfully.' : 'Check-out failed.',
        ),
        statusCode: response.statusCode,
      );
    } on AttendanceServiceException catch (error) {
      return AttendanceActionResult(
        success: false,
        message: error.message,
        statusCode: 0,
      );
    }
  }

  Future<Map<String, dynamic>> overtimeStatus() async {
    final response = await _get('/attendance/overtime/');
    if (response.statusCode != 200) {
      throw AttendanceServiceException(
        _message(response, 'Unable to load overtime status.'),
      );
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<String> requestOvertime({
    required double hours,
    required String reason,
  }) async {
    final response = await _post(
      '/attendance/overtime/',
      body: jsonEncode({'hours': hours, 'reason': reason}),
    );
    if (response.statusCode != 201) {
      throw AttendanceServiceException(
        _message(response, 'Unable to request overtime.'),
      );
    }
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['message'] ?? 'Overtime request sent.').toString();
  }

  Future<String> startOvertime() async {
    final response = await _post('/attendance/overtime/start/');
    if (response.statusCode != 200) {
      throw AttendanceServiceException(
        _message(response, 'Unable to start overtime.'),
      );
    }
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['message'] ?? 'Approved overtime started.').toString();
  }

  Future<String> stopOvertime() async {
    final response = await _post('/attendance/overtime/stop/');
    if (response.statusCode != 200) {
      throw AttendanceServiceException(
        _message(response, 'Unable to stop overtime.'),
      );
    }
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return (data['message'] ?? 'Overtime stopped.').toString();
  }

  String _message(http.Response response, String fallback) {
    try {
      final data = jsonDecode(response.body);
      if (data is Map) {
        return (data['detail'] ?? data['message'] ?? fallback).toString();
      }
    } catch (_) {
      // Use a stable fallback when a proxy/server returns non-JSON content.
    }
    return fallback;
  }

  Future<AttendanceModel?> todayAttendance() async {
    try {
      final response = await _get('/attendance/today/');
      if (response.statusCode != 200) return null;
      return AttendanceModel.fromJson(
        Map<String, dynamic>.from(jsonDecode(response.body) as Map),
      );
    } on AttendanceServiceException {
      return null;
    }
  }

  Future<List<AttendanceModel>> history() async {
    try {
      final response = await _get('/attendance/history/');
      if (response.statusCode != 200) return <AttendanceModel>[];

      final decoded = jsonDecode(response.body);
      if (decoded is! List) return <AttendanceModel>[];
      return decoded
          .whereType<Map>()
          .map(
            (row) => AttendanceModel.fromJson(
              Map<String, dynamic>.from(row),
            ),
          )
          .toList(growable: false);
    } on AttendanceServiceException {
      return <AttendanceModel>[];
    }
  }
}

class AttendanceServiceException implements Exception {
  const AttendanceServiceException(this.message);

  final String message;

  @override
  String toString() => message;
}

class AttendanceActionResult {
  final bool success;
  final String message;
  final int statusCode;
  final double? distanceFromOfficeMeters;

  const AttendanceActionResult({
    required this.success,
    required this.message,
    required this.statusCode,
    this.distanceFromOfficeMeters,
  });
}
