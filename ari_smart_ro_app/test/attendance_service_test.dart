import 'dart:convert';

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
