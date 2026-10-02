import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

String _read(String relativePath) => File(relativePath).readAsStringSync();

void main() {
  group('Corporate HRMS Phase-1 UI contracts', () {
    test('command center keeps desktop and mobile responsive navigation', () {
      final source = _read('lib/screens/hrms/hrms_screen.dart');

      expect(source, contains('width >= 1050'));
      expect(source, contains('NavigationRail'));
      expect(source, contains('NavigationBar'));
      expect(source, contains('Corporate HR Command Center'));
      expect(source, contains('Active workforce'));
      expect(source, contains('Present today'));
      expect(source, contains('Pending onboarding'));
      expect(source, contains('Confirmation due'));
      expect(source, contains('Notice period'));
      expect(source, contains('Department structure'));
      expect(source, contains('Designation structure'));
    });

    test('command center wires required HR quick actions', () {
      final source = _read('lib/screens/hrms/hrms_screen.dart');

      for (final label in <String>[
        'New Joining',
        'Employee Directory',
        'Attendance',
        'Leave',
        'Payroll',
        'Documents',
        'Training',
        'Performance',
        'Career Movement',
        'Exit Management',
        'HR Reports',
      ]) {
        expect(source, contains(label), reason: 'Missing quick action: $label');
      }

      expect(source, contains('CorporateJoiningWizard'));
      expect(source, contains('EmployeeHrFileScreen'));
      expect(source, contains('AttendanceScreen'));
      expect(source, contains('TrainingScreen'));
    });

    test('joining wizard switches stepper layout for desktop and mobile', () {
      final source = _read('lib/screens/hrms/corporate_joining_wizard.dart');

      expect(source, contains('MediaQuery.sizeOf(context).width >= 900'));
      expect(source, contains('StepperType.horizontal'));
      expect(source, contains('StepperType.vertical'));
      expect(source, contains("title: const Text('Personal')"));
      expect(source, contains("title: const Text('Employment')"));
      expect(source, contains("title: const Text('Compensation')"));
      expect(source, contains("title: const Text('Documents')"));
      expect(source, contains("title: const Text('Security')"));
      expect(source, contains("title: const Text('Training')"));
      expect(source, contains("title: const Text('Final Review')"));
    });

    test('digital employee HR file keeps professional tab hierarchy', () {
      final source = _read('lib/screens/hrms/employee_hr_file_screen.dart');

      for (final tab in <String>[
        'OVERVIEW',
        'DOCUMENTS',
        'ATTENDANCE',
        'LEAVE',
        'PAYROLL',
        'TRAINING',
        'PERFORMANCE',
        'CAREER & AUDIT',
      ]) {
        expect(source, contains("Tab(text: '$tab')"), reason: 'Missing HR file tab: $tab');
      }
      expect(source, contains('READY FOR DUTY'));
      expect(source, contains('Probation & confirmation'));
      expect(source, contains('MANAGER REVIEW'));
      expect(source, contains('HR REVIEW'));
      expect(source, contains('EXTEND PROBATION'));
      expect(source, contains('CONFIRM EMPLOYEE'));
    });
  });
}
