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

    test('backend compatibility route is explicitly guarded', () {
      final config = _read('../backend/config/urls.py');
      final guard = _read('../backend/employees/hr_phase2_legacy_guard.py');
      expect(config, contains('GuardedEmployeeHrLifecycleActionAPIView'));
      expect(config, contains('hrms-employee-lifecycle-action-guarded'));
      for (final action in <String>[
        'EXTEND_PROBATION',
        'CONFIRM',
        'START_NOTICE',
        'SEPARATE',
      ]) {
        expect(guard, contains('"$action"'));
      }
      expect(guard, contains('PHASE2_LIFECYCLE_REQUIRED'));
    });
  });
}
