import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

String _read(String relativePath) => File(relativePath).readAsStringSync();

void main() {
  group('Corporate HRMS Phase-2 Digital HR Letters + BGV contracts', () {
    test('Corporate HRMS command center links HR Letters and BGV', () {
      final source = _read('lib/screens/hrms/hrms_screen.dart');
      expect(source, contains("import 'hr_letters_bgv_screen.dart';"));
      expect(source, contains('HR Letters & BGV'));
      expect(source, contains('HrLettersBgvScreen'));
    });

    test('service covers letters and BGV backend endpoints', () {
      final source = _read('lib/services/corporate_hrms_service.dart');
      for (final endpoint in <String>[
        '/employees/hrms/letters/dashboard/',
        '/employees/hrms/letters/templates/',
        '/employees/hrms/letters/workflows/',
        '/employees/hrms/letters/issued/',
        '/employees/hrms/bgv/policy/',
        '/employees/hrms/bgv/cases/',
      ]) {
        expect(source, contains(endpoint), reason: 'Missing endpoint $endpoint');
      }
      for (final method in <String>[
        'lettersDashboard',
        'letterTemplates',
        'createLetterTemplate',
        'letterWorkflows',
        'createLetterWorkflow',
        'letterWorkflowAction',
        'issuedLetters',
        'acknowledgeLetter',
        'bgvPolicy',
        'updateBgvPolicy',
        'bgvCases',
        'createBgvCase',
        'upsertBgvCheck',
        'decideBgv',
      ]) {
        expect(source, contains(method), reason: 'Missing service method $method');
      }
    });

    test('workspace exposes enterprise letters workflow', () {
      final source = _read('lib/screens/hrms/hr_letters_bgv_screen.dart');
      for (final label in <String>[
        'Digital HR Letters + BGV Command Center',
        'Letter Templates',
        'Letter Workflows',
        'Issued Letters • Read Only',
        'SUBMIT APPROVAL',
        'APPROVE',
        'REJECT',
        'ISSUE IMMUTABLE LETTER',
        'Issued snapshot is final and read-only.',
        'Acknowledgement due',
        'ACKNOWLEDGE',
        'DECLINE',
      ]) {
        expect(source, contains(label), reason: 'Missing letters UI contract $label');
      }
      expect(source, contains('SHA-256:'));
      expect(source, contains('createLetterTemplate'));
      expect(source, contains('createLetterWorkflow'));
      expect(source, contains('letterWorkflowAction'));
      expect(source, contains('acknowledgeLetter'));
    });

    test('workspace exposes BGV checklist, decisions and READY policy', () {
      final source = _read('lib/screens/hrms/hr_letters_bgv_screen.dart');
      for (final value in <String>[
        'Background Verification',
        'START BGV CASE',
        'Verification checklist',
        'IDENTITY',
        'ADDRESS',
        'EDUCATION',
        'EMPLOYMENT',
        'CRIMINAL_POLICE',
        'REFERENCE',
        'MARK CLEAR',
        'CONDITIONAL',
        'FAILED',
        'WAIVE WITH REASON',
        'BGV is mandatory before READY FOR DUTY',
        'BGV is optional before READY FOR DUTY',
        'Admin READY override remains reasoned and audited',
      ]) {
        expect(source, contains(value), reason: 'Missing BGV UI contract $value');
      }
      expect(source, contains('createBgvCase'));
      expect(source, contains('upsertBgvCheck'));
      expect(source, contains('decideBgv'));
      expect(source, contains('updateBgvPolicy'));
      expect(source, contains('Do not enter full Aadhaar/PAN numbers.'));
    });

    test('role gated controls are explicit', () {
      final source = _read('lib/screens/hrms/hr_letters_bgv_screen.dart');
      expect(source, contains("bool get _canManage => const {'ADMIN', 'OFFICE'}.contains(_role)"));
      expect(source, contains("bool get _canApprove => _role == 'ADMIN'"));
      expect(source, contains("bool get _canBgvManage => const {'ADMIN', 'OFFICE'}.contains(_role)"));
      expect(source, contains("bool get _canBgvDecide => _role == 'ADMIN'"));
    });

    test('Android and Windows responsive navigation remain explicit', () {
      final source = _read('lib/screens/hrms/hr_letters_bgv_screen.dart');
      expect(source, contains('constraints.maxWidth >= 1050'));
      expect(source, contains('NavigationRail'));
      expect(source, contains('NavigationBar'));
      expect(source, contains('RefreshIndicator'));
      expect(source, contains('SingleChildScrollView'));
      expect(source, contains('RETRY'));
      expect(source, contains('Wrap('));
    });
  });
}
