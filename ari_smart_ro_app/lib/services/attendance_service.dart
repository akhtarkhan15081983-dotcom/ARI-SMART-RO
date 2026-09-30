import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/attendance_model.dart';
import 'api_service.dart';
import 'attendance_integrity_service.dart';
import 'device_identity_service.dart';
import 'offline_action_dead_letter_store.dart';
import 'offline_attendance_store.dart';

typedef AttendanceHeadersProvider = Future<Map<String, String>> Function();
typedef AttendanceDeviceIdProvider = Future<String> Function();
typedef AttendanceMockLocationProvider = Future<bool> Function();

class AttendanceService {
  AttendanceService({
    http.Client? client,
    AttendanceHeadersProvider? headersProvider,
    AttendanceDeviceIdProvider? deviceIdProvider,
    AttendanceMockLocationProvider? mockLocationProvider,
    OfflineAttendanceStore? offlineStore,
    OfflineActionDeadLetterStore? deadLetterStore,
    String? baseUrl,
    Duration requestTimeout = const Duration(seconds: 15),
    Duration uploadTimeout = const Duration(seconds: 30),
  }) : _client = client ?? http.Client(),
       _headersProvider = headersProvider ?? ApiService.authHeaders,
       _deviceIdProvider = deviceIdProvider ?? DeviceIdentityService.getOrCreate,
       _mockLocationProvider =
           mockLocationProvider ?? AttendanceIntegrityService.isCurrentLocationMocked,
       _offlineStore = offlineStore ?? OfflineAttendanceStore(),
       _deadLetterStore = deadLetterStore ?? OfflineActionDeadLetterStore(),
       _baseUrl = (baseUrl ?? ApiService.baseUrl).replaceFirst(RegExp(r'/$'), ''),
       _requestTimeout = requestTimeout,
       _uploadTimeout = uploadTimeout;

  final http.Client _client;
  final AttendanceHeadersProvider _headersProvider;
  final AttendanceDeviceIdProvider _deviceIdProvider;
  final AttendanceMockLocationProvider _mockLocationProvider;
  final OfflineAttendanceStore _offlineStore;
  final OfflineActionDeadLetterStore _deadLetterStore;
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
    final capturedAt = DateTime.now();
    final actionId = _offlineStore.newActionId();
    final deviceId = await _deviceIdProvider();
    final isMocked = await _mockLocationProvider();
    final request = http.MultipartRequest('POST', _uri('/attendance/check-in/'));

    final headers = await _headers();
    headers.removeWhere((key, _) => key.toLowerCase() == 'content-type');
    request.headers.addAll(headers);

    request.fields['latitude'] = latitude.toString();
    request.fields['longitude'] = longitude.toString();
    request.fields['device_id'] = deviceId;
    request.fields['is_mocked'] = isMocked ? 'true' : 'false';
    request.files.add(await http.MultipartFile.fromPath('selfie', selfiePath));

    try {
      final response = await _client.send(request).timeout(_uploadTimeout);
      final body = await response.stream.bytesToString().timeout(_requestTimeout);
      final success = response.statusCode == 200 || response.statusCode == 201;
      String message = success ? 'Checked in successfully.' : 'Check-in failed.';
      double? distanceMeters;
      DateTime? serverCheckIn;

      try {
        final decoded = jsonDecode(body);
        if (decoded is Map<String, dynamic>) {
          final serverMessage = decoded['message'] ?? decoded['detail'];
          if (serverMessage != null && serverMessage.toString().trim().isNotEmpty) {
            message = serverMessage.toString().trim();
          }
          final distance = decoded['distance_from_office_meters'];
          if (distance is num) distanceMeters = distance.toDouble();
          final attendance = decoded['attendance'];
          if (attendance is Map) {
            serverCheckIn = DateTime.tryParse(
              attendance['check_in']?.toString() ?? '',
            );
          }
        }
      } catch (_) {
        // Keep the fallback for non-JSON proxy/server responses.
      }

      if (success) {
        await _persistSnapshotSafely(checkIn: serverCheckIn ?? capturedAt);
      }
      return AttendanceActionResult(
        success: success,
        message: message,
        statusCode: response.statusCode,
        distanceFromOfficeMeters: distanceMeters,
      );
    } catch (_) {
      if (isMocked) {
        return const AttendanceActionResult(
          success: false,
          message: 'Mock/fake GPS location is not allowed for attendance.',
          statusCode: 403,
        );
      }
      try {
        final preservedSelfie = await _offlineStore.preserveSelfie(selfiePath, actionId);
        await _offlineStore.enqueue({
          'action_id': actionId,
          'action': 'CHECK_IN',
          'captured_at': capturedAt.toUtc().toIso8601String(),
          'latitude': latitude,
          'longitude': longitude,
          'device_id': deviceId,
          'is_mocked': false,
          'selfie_path': preservedSelfie,
        });
        await _persistSnapshotSafely(checkIn: capturedAt);
        return const AttendanceActionResult(
          success: true,
          queuedOffline: true,
          message: 'No network. Check-in saved securely on this phone and will sync automatically.',
          statusCode: 202,
        );
      } catch (_) {
        return const AttendanceActionResult(
          success: false,
          message: 'Unable to connect and the offline check-in could not be saved safely. Please try again.',
          statusCode: 0,
        );
      }
    }
  }

  Future<AttendanceActionResult> checkOut() async {
    final capturedAt = DateTime.now();
    try {
      final response = await _post('/attendance/check-out/');
      final success = response.statusCode == 200 || response.statusCode == 201;
      DateTime? serverCheckOut;
      if (success) {
        try {
          final decoded = jsonDecode(response.body);
          if (decoded is Map) {
            serverCheckOut = DateTime.tryParse(
              decoded['check_out']?.toString() ?? '',
            );
          }
        } catch (_) {}
        await _closeSnapshotSafely(serverCheckOut ?? capturedAt);
      }
      return AttendanceActionResult(
        success: success,
        message: _message(
          response,
          success ? 'Checked out successfully.' : 'Check-out failed.',
        ),
        statusCode: response.statusCode,
      );
    } on AttendanceServiceException catch (error) {
      try {
        final actionId = _offlineStore.newActionId();
        await _offlineStore.enqueue({
          'action_id': actionId,
          'action': 'CHECK_OUT',
          'captured_at': capturedAt.toUtc().toIso8601String(),
        });
        await _closeSnapshotSafely(capturedAt);
        return const AttendanceActionResult(
          success: true,
          queuedOffline: true,
          message: 'No network. Check-out saved securely and will sync automatically.',
          statusCode: 202,
        );
      } catch (_) {
        return AttendanceActionResult(
          success: false,
          message: error.message,
          statusCode: 0,
        );
      }
    }
  }

  Future<OfflineAttendanceSyncResult> syncPendingOfflineActions() async {
    List<Map<String, dynamic>> pending;
    try {
      pending = await _offlineStore.pending();
    } catch (_) {
      return const OfflineAttendanceSyncResult();
    }

    var synced = 0;
    var rejected = 0;
    for (final action in pending) {
      final actionId = (action['action_id'] ?? '').toString();
      if (actionId.isEmpty) continue;
      final request = http.MultipartRequest('POST', _uri('/attendance/offline-sync/'));
      try {
        final headers = await _headers();
        headers.removeWhere((key, _) => key.toLowerCase() == 'content-type');
        request.headers.addAll(headers);
        for (final entry in action.entries) {
          if (entry.key == 'selfie_path' || entry.value == null) continue;
          request.fields[entry.key] = entry.value.toString();
        }
        final selfiePath = action['selfie_path']?.toString();
        if (selfiePath != null && selfiePath.isNotEmpty) {
          request.files.add(await http.MultipartFile.fromPath('selfie', selfiePath));
        }

        final response = await _client.send(request).timeout(_uploadTimeout);
        final body = await response.stream.bytesToString().timeout(_requestTimeout);
        if (response.statusCode == 200 || response.statusCode == 201) {
          await _applyActionToSnapshot(action);
          await _offlineStore.remove(actionId);
          synced++;
          continue;
        }
        if (response.statusCode >= 400 && response.statusCode < 500) {
          String detail = 'Offline attendance action was rejected by the server.';
          try {
            final decoded = jsonDecode(body);
            if (decoded is Map) {
              detail = (decoded['message'] ?? decoded['detail'] ?? detail).toString();
            }
          } catch (_) {}
          await _deadLetterStore.append(
            action: action,
            reason: 'ATTENDANCE_OFFLINE_SYNC_REJECTED',
            detail: detail,
          );
          await _offlineStore.remove(actionId, deleteMedia: false);
          rejected++;
          continue;
        }
        break;
      } catch (_) {
        // Transient connectivity/server failure: preserve the queue untouched.
        break;
      }
    }
    return OfflineAttendanceSyncResult(synced: synced, rejected: rejected);
  }

  Future<void> _applyActionToSnapshot(Map<String, dynamic> action) async {
    final captured = DateTime.tryParse(action['captured_at']?.toString() ?? '');
    if (captured == null) return;
    final type = action['action']?.toString().toUpperCase();
    if (type == 'CHECK_IN') {
      await _persistSnapshotSafely(checkIn: captured);
    } else if (type == 'CHECK_OUT') {
      await _closeSnapshotSafely(captured);
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
    } catch (_) {}
    return fallback;
  }

  Future<AttendanceModel?> todayAttendance() async {
    try {
      await syncPendingOfflineActions();
      final response = await _get('/attendance/today/');
      if (response.statusCode == 200) {
        final attendance = AttendanceModel.fromJson(
          Map<String, dynamic>.from(jsonDecode(response.body) as Map),
        );
        await _refreshSnapshotFromAttendance(attendance);
        return attendance;
      }
    } on AttendanceServiceException {
      // Fall back to durable local state below.
    } catch (_) {
      // Fall back to durable local state below.
    }
    return _offlineAttendanceFallback();
  }

  Future<void> _refreshSnapshotFromAttendance(AttendanceModel attendance) async {
    final checkIn = DateTime.tryParse(attendance.checkIn ?? '');
    if (checkIn == null) return;
    final checkOut = DateTime.tryParse(attendance.checkOut ?? '');
    await _persistSnapshotSafely(checkIn: checkIn, checkOut: checkOut);
  }

  Future<AttendanceModel?> _offlineAttendanceFallback() async {
    try {
      final now = DateTime.now();
      final snapshot = await _offlineStore.todayShiftSnapshot(now: now);
      DateTime? checkIn = DateTime.tryParse(
        snapshot?['check_in']?.toString() ?? '',
      )?.toLocal();
      DateTime? checkOut = DateTime.tryParse(
        snapshot?['check_out']?.toString() ?? '',
      )?.toLocal();

      final pending = await _offlineStore.pending();
      for (final action in pending) {
        final capturedRaw = action['captured_at']?.toString();
        if (capturedRaw == null) continue;
        final captured = DateTime.tryParse(capturedRaw)?.toLocal();
        if (captured == null || !_sameLocalDay(captured, now)) continue;
        final type = action['action']?.toString().toUpperCase();
        if (type == 'CHECK_IN') checkIn ??= captured;
        if (type == 'CHECK_OUT') checkOut ??= captured;
      }
      if (checkIn == null) return null;
      final effectiveEnd = checkOut ?? now;
      final elapsed = effectiveEnd.isAfter(checkIn)
          ? effectiveEnd.difference(checkIn)
          : Duration.zero;
      final cappedSeconds = elapsed.inSeconds.clamp(
        0,
        const Duration(hours: 8).inSeconds,
      );
      final hours = cappedSeconds / 3600.0;
      return AttendanceModel(
        id: 0,
        employeeName: '',
        date: _localDate(checkIn),
        checkIn: checkIn.toIso8601String(),
        checkOut: checkOut?.toIso8601String(),
        workingHours: hours,
        regularWorkingHours: hours,
        regularShiftEndAt: checkIn.add(const Duration(hours: 8)).toIso8601String(),
        status: 'PRESENT',
        remarks: pending.isEmpty
            ? 'Recovered from secure local attendance snapshot.'
            : 'Pending secure offline attendance sync.',
        identityReviewStatus: 'PENDING',
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> _persistSnapshotSafely({
    required DateTime checkIn,
    DateTime? checkOut,
  }) async {
    try {
      await _offlineStore.saveShiftSnapshot(
        checkIn: checkIn,
        checkOut: checkOut,
      );
    } catch (_) {
      // A local persistence issue must not turn a confirmed server action into
      // a false failure; pending actions still provide an additional fallback.
    }
  }

  Future<void> _closeSnapshotSafely(DateTime checkOut) async {
    try {
      await _offlineStore.closeShiftSnapshot(checkOut);
    } catch (_) {
      // Preserve server success even if local health/storage is degraded.
    }
  }

  bool _sameLocalDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  String _localDate(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  Future<List<AttendanceModel>> history() async {
    try {
      final response = await _get('/attendance/history/');
      if (response.statusCode != 200) return <AttendanceModel>[];
      final decoded = jsonDecode(response.body);
      if (decoded is! List) return <AttendanceModel>[];
      return decoded
          .whereType<Map>()
          .map((row) => AttendanceModel.fromJson(Map<String, dynamic>.from(row)))
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
  final bool queuedOffline;

  const AttendanceActionResult({
    required this.success,
    required this.message,
    required this.statusCode,
    this.distanceFromOfficeMeters,
    this.queuedOffline = false,
  });
}

class OfflineAttendanceSyncResult {
  final int synced;
  final int rejected;

  const OfflineAttendanceSyncResult({this.synced = 0, this.rejected = 0});

  bool get changed => synced > 0 || rejected > 0;
}
