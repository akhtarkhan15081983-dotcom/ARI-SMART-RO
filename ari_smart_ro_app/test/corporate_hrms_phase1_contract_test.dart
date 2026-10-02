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
      expect(source, contains('Workforce structure'));
      expect(source, contains("workforce['department_mix']"));
      expect(source, contains("workforce['designation_mix']"));
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

    test('joining wizard is responsive and uploads actual documents', () {
      final source = _read('lib/screens/hrms/corporate_joining_wizard.dart');

      expect(source, contains('MediaQuery.sizeOf(context).width >= 900'));
      expect(source, contains('StepperType.horizontal'));
      expect(source, contains('StepperType.vertical'));
      for (final step in <String>[
        'Personal',
        'Employment',
        'Payroll',
        'Documents',
        'Controls',
        'Review',
      ]) {
        expect(source, contains("title: const Text('$step')"));
      }
      for (final type in <String>[
        'PHOTO',
        'AADHAAR',
        'PAN',
        'ADDRESS_PROOF',
        'BANK_PROOF',
        'QUALIFICATION',
        'PREVIOUS_EMPLOYMENT',
        'OTHER',
      ]) {
        expect(source, contains("'$type'"), reason: 'Missing document type $type');
      }
      expect(source, contains('FilePicker.platform.pickFiles'));
      expect(source, contains('uploadEmployeeDocument'));
      expect(source, contains('READY FOR DUTY'));
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
      expect(source, contains('Manager review'));
      expect(source, contains('HR review'));
      expect(source, contains('Extend probation'));
      expect(source, contains('Confirm employee'));
      expect(source, contains('UPLOAD DOCUMENT'));
      expect(source, contains("_reviewDocument(id, 'VERIFY')"));
      expect(source, contains("_reviewDocument(id, 'REJECT')"));
      expect(source, contains("_reviewDocument(id, 'EXPIRE')"));
      expect(source, contains('Audit history'));
    });

    test('corporate HRMS service uses multipart document upload contract', () {
      final source = _read('lib/services/corporate_hrms_service.dart');

      expect(source, contains('http.MultipartRequest'));
      expect(source, contains("headers.remove('Content-Type')"));
      expect(source, contains("request.fields['document_type']"));
      expect(source, contains("/documents/"));
      expect(source, contains('reviewEmployeeDocument'));
    });
  });
}
