import 'dart:convert';
import 'dart:io';

import 'package:ari_smart_ro_app/services/attendance_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

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
        final client = MockClient((request) async {
          expect(request, isA<http.MultipartRequest>());
          final multipart = request as http.MultipartRequest;
          expect(multipart.fields['latitude'], '27.149028');
          expect(multipart.fields['longitude'], '78.045');
          expect(multipart.fields['device_id'], 'test-device');
          expect(multipart.fields['is_mocked'], 'true');
          return http.Response(
            jsonEncode({'success': false, 'code': 'MOCK_LOCATION_DETECTED'}),
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
