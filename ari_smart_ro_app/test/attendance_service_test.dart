import 'dart:convert';
import 'dart:io';

import 'package:ari_smart_ro_app/services/attendance_service.dart';
import 'package:ari_smart_ro_app/services/offline_attendance_store.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class _InspectingBaseClient extends http.BaseClient {
  _InspectingBaseClient(this.handler);

  final Future<http.StreamedResponse> Function(http.BaseRequest request) handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) => handler(request);
}

void main() {
  group('AttendanceService', () {
    test('todayAttendance parses successful response', () async {
      final client = MockClient((request) async {
        expect(request.url.toString(), 'https://example.test/api/attendance/today/');
        expect(request.headers['Authorization'], 'Bearer test-token');
        return http.Response(
          jsonEncode({
            'id': 1,
            'employee_name': 'Rajkumar',
            'date': '2026-09-22',
            'check_in': '2026-09-22T09:00:00+05:30',
            'working_hours': '4.50',
            'regular_working_hours': '4.50',
            'overtime_working_hours': '0.00',
            'status': 'PRESENT',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = AttendanceService(
        client: client,
        baseUrl: 'https://example.test/api',
        headersProvider: () async => {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json',
        },
      );

      final attendance = await service.todayAttendance();

      expect(attendance, isNotNull);
      expect(attendance!.employeeName, 'Rajkumar');
      expect(attendance.workingHours, 4.5);
    });

    test('checkIn sends mocked-location integrity signal', () async {
      final temp = await Directory.systemTemp.createTemp('ari-attendance-test-');
      final selfie = File('${temp.path}/selfie.jpg');
      await selfie.writeAsBytes(<int>[1, 2, 3, 4]);

      try {
        final client = _InspectingBaseClient((request) async {
          expect(request, isA<http.MultipartRequest>());
          final multipart = request as http.MultipartRequest;
          expect(multipart.url.toString(), 'https://example.test/api/attendance/check-in/');
          expect(multipart.fields['latitude'], '27.149028');
          expect(multipart.fields['longitude'], '78.045');
          expect(multipart.fields['device_id'], 'test-device');
          expect(multipart.fields['is_mocked'], 'true');
          expect(multipart.files, hasLength(1));
          expect(multipart.files.single.field, 'selfie');

          return http.StreamedResponse(
            Stream<List<int>>.value(
              utf8.encode(
                jsonEncode({
                  'success': false,
                  'code': 'MOCK_LOCATION_DETECTED',
                  'message': 'Mock/fake GPS location detected. Attendance is blocked.',
                }),
              ),
            ),
            403,
            headers: {'content-type': 'application/json'},
          );
        });

        final service = AttendanceService(
          client: client,
          baseUrl: 'https://example.test/api',
          headersProvider: () async => {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json',
          },
          deviceIdProvider: () async => 'test-device',
          mockLocationProvider: () async => true,
        );

        final result = await service.checkIn(
          latitude: 27.149028,
          longitude: 78.045,
          selfiePath: selfie.path,
        );

        expect(result.success, isFalse);
        expect(result.statusCode, 403);
        expect(result.message, contains('Mock/fake GPS'));
      } finally {
        await temp.delete(recursive: true);
      }
    });

    test('checkOut returns stable offline result on network failure', () async {
      final client = MockClient((request) async {
        throw Exception('network down');
      });

      final service = AttendanceService(
        client: client,
        baseUrl: 'https://example.test/api',
        headersProvider: () async => {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json',
        },
        requestTimeout: const Duration(milliseconds: 50),
      );

      final result = await service.checkOut();

      expect(result.success, isFalse);
      expect(result.statusCode, 0);
      expect(result.message, contains('Unable to connect'));
    });

    test('online check-in survives restart offline and offline checkout closes shift', () async {
      final temp = await Directory.systemTemp.createTemp('ari-attendance-restart-');
      final selfie = File('${temp.path}/selfie.jpg');
      await selfie.writeAsBytes(<int>[1, 2, 3, 4]);
      final store = OfflineAttendanceStore(rootDirectoryOverride: temp);
      final checkInAt = DateTime.now().subtract(const Duration(minutes: 10));

      try {
        final onlineClient = _InspectingBaseClient((request) async {
          expect(request.url.path, '/api/attendance/check-in/');
          return http.StreamedResponse(
            Stream<List<int>>.value(
              utf8.encode(jsonEncode({
                'success': true,
                'message': 'Check In Successful',
                'attendance': {
                  'check_in': checkInAt.toUtc().toIso8601String(),
                },
              })),
            ),
            201,
            headers: {'content-type': 'application/json'},
          );
        });
        final onlineService = AttendanceService(
          client: onlineClient,
          baseUrl: 'https://example.test/api',
          headersProvider: () async => {'Authorization': 'Bearer test-token'},
          deviceIdProvider: () async => 'test-device',
          mockLocationProvider: () async => false,
          offlineStore: store,
        );

        final checkIn = await onlineService.checkIn(
          latitude: 27.149028,
          longitude: 78.045,
          selfiePath: selfie.path,
        );
        expect(checkIn.success, isTrue);
        expect(checkIn.queuedOffline, isFalse);

        final offlineClient = MockClient((request) async {
          throw Exception('network down');
        });
        final restartedService = AttendanceService(
          client: offlineClient,
          baseUrl: 'https://example.test/api',
          headersProvider: () async => {'Authorization': 'Bearer test-token'},
          offlineStore: OfflineAttendanceStore(rootDirectoryOverride: temp),
          requestTimeout: const Duration(milliseconds: 50),
        );

        final restored = await restartedService.todayAttendance();
        expect(restored, isNotNull);
        expect(restored!.checkIn, isNotNull);
        expect(restored.checkOut, isNull);
        expect(restored.remarks, contains('Recovered'));

        final checkOut = await restartedService.checkOut();
        expect(checkOut.success, isTrue);
        expect(checkOut.queuedOffline, isTrue);

        final closed = await restartedService.todayAttendance();
        expect(closed, isNotNull);
        expect(closed!.checkOut, isNotNull);
        expect(await store.count(), 1);
      } finally {
        await temp.delete(recursive: true);
      }
    });

    test('history tolerates malformed success payload', () async {
      final client = MockClient((request) async => http.Response('{}', 200));

      final service = AttendanceService(
        client: client,
        baseUrl: 'https://example.test/api',
        headersProvider: () async => {
          'Authorization': 'Bearer test-token',
          'Content-Type': 'application/json',
        },
      );

      final history = await service.history();

      expect(history, isEmpty);
    });
  });
}
