import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

String _read(String relativePath) => File(relativePath).readAsStringSync();

void main() {
  group('Corporate HRMS Phase-2 lifecycle integration contracts', () {
    test('app registers direct lifecycle workspace route', () {
      final app = _read('lib/app.dart');
      expect(app, contains("import 'screens/hrms/employee_lifecycle_screen.dart';"));
      expect(app, contains("'/hrms/lifecycle'"));
      expect(app, contains('EmployeeLifecycleScreen'));
    });

    test('lifecycle workspace uses dedicated Phase-2 service contract', () {
      final screen = _read('lib/screens/hrms/employee_lifecycle_screen.dart');
      final service = _read('lib/services/corporate_hrms_lifecycle_service.dart');
      expect(screen, contains('lifecycleCommandCenter'));
      expect(screen, contains('lifecycleProbationQueue'));
      expect(screen, contains('lifecycleTimeline'));
      expect(screen, contains('exitCases'));
      expect(service, contains('/employees/hrms/lifecycle/actions/'));
      expect(service, contains('/employees/hrms/lifecycle/exits/'));
      expect(service, contains('/timeline/'));
    });

    test('HRMS command center exposes visible lifecycle entry', () {
      final hrms = _read('lib/screens/hrms/hrms_screen.dart');
      expect(hrms, contains("'Employee Lifecycle'"));
      expect(hrms, contains("pushNamed('/hrms/lifecycle')"));
    });

    test('digital HR file routes sensitive transitions to Phase-2 workspace', () {
      final file = _read('lib/screens/hrms/employee_hr_file_screen.dart');
      expect(file, contains('Employee Lifecycle workspace'));
      expect(file, contains("pushNamed('/hrms/lifecycle')"));
      expect(file, isNot(contains("_lifecycleAction('CONFIRM')")));
      expect(file, isNot(contains("_lifecycleAction('START_NOTICE')")));
      expect(file, isNot(contains("_lifecycleAction('SEPARATE')")));
      expect(file, isNot(contains("'EXTEND_PROBATION'")));
      expect(file, contains("_lifecycleAction('MANAGER_REVIEW'"));
      expect(file, contains("_lifecycleAction('HR_REVIEW'"));
      expect(file, contains("_lifecycleAction('OVERRIDE_READY'"));
    });
  });
}
