import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

String _read(String relativePath) => File(relativePath).readAsStringSync();

void main() {
  group('Corporate HRMS Phase-1 UI contracts', () {
    test('command center keeps desktop and mobile responsive navigation', () {
      final source = _read('lib/screens/hrms/hrms_screen.dart');
      expect(source, contains('NavigationRail'));
      expect(source, contains('NavigationBar'));
      expect(source, contains('MediaQuery.sizeOf(context).width'));
      expect(source, contains('Corporate HR Command Center'));
      expect(source, contains('Executive workforce snapshot'));
      expect(source, contains('Action queue'));
    });

    test('command center wires required HR quick actions', () {
      final source = _read('lib/screens/hrms/hrms_screen.dart');
      for (final action in <String>[
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
        'Employee Admin',
      ]) {
        expect(source, contains("'$action'"), reason: 'Missing quick action: $action');
      }
      expect(source, contains('CorporateJoiningWizard'));
      expect(source, contains('EmployeeHrFileScreen'));
      expect(source, contains('EmployeeManagementScreen'));
    });

    test('joining wizard is responsive and uploads actual documents', () {
      final source = _read('lib/screens/hrms/corporate_joining_wizard.dart');
      expect(source, contains('LayoutBuilder'));
      expect(source, contains('constraints.maxWidth >= 900'));
      expect(source, contains('NavigationRail'));
      expect(source, contains('Step('));
      expect(source, contains('Select & upload'));
      expect(source, contains('uploadEmployeeDocument'));
      expect(source, contains('FilePicker.platform.pickFiles'));
      expect(source, contains('reviewEmployeeDocument'));
      expect(source, contains('Required joining documents'));
      expect(source, contains('Ready-for-duty validation'));
    });

    test('digital employee HR file keeps hierarchy and audited document actions', () {
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
      expect(source, contains('Manager onboarding review'));
      expect(source, contains('HR onboarding review'));
      expect(source, contains('Employee Lifecycle workspace'));
      expect(source, contains('Probation, confirmation, promotion, increment, transfer, exit and clearance'));
      expect(source, contains("pushNamed('/hrms/lifecycle')"));
      expect(source, contains('UPLOAD DOCUMENT'));
      expect(source, contains("_reviewDocument(id, 'VERIFY')"));
      expect(source, contains("_reviewDocument(id, 'REJECT')"));
      expect(source, contains("_reviewDocument(id, 'EXPIRE')"));
      expect(source, contains('Audit history'));
    });

    test('corporate HRMS service uses multipart document upload contract', () {
      final source = _read('lib/services/corporate_hrms_service.dart');
      expect(source, contains('http.MultipartRequest'));
      expect(source, contains("request.files.add"));
      expect(source, contains('http.MultipartFile.fromBytes'));
      expect(source, contains('http.MultipartFile.fromPath'));
      expect(source, contains("'/employees/hrms/employees/\$employeeId/documents/'"));
    });
  });
}
