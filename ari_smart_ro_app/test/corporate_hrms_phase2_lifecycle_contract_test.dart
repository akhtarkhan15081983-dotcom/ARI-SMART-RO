import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

String _read(String relativePath) => File(relativePath).readAsStringSync();

void main() {
  group('Corporate HRMS Phase-2 lifecycle Flutter contracts', () {
    test('service covers the complete lifecycle backend surface', () {
      final source = _read('lib/services/corporate_hrms_lifecycle_service.dart');
      for (final endpoint in <String>[
        '/employees/hrms/lifecycle/command-center/',
        '/employees/hrms/lifecycle/probation-queue/',
        '/employees/hrms/lifecycle/actions/',
        '/employees/hrms/lifecycle/employees/',
        '/employees/hrms/lifecycle/exits/',
        '/workflow/',
        '/clearances/',
        '/post-separation-letter/',
      ]) {
        expect(source, contains(endpoint), reason: 'Missing lifecycle endpoint $endpoint');
      }
      for (final method in <String>[
        'lifecycleCommandCenter',
        'lifecycleProbationQueue',
        'lifecycleTimeline',
        'lifecycleActions',
        'createLifecycleAction',
        'lifecycleWorkflow',
        'exitCases',
        'createExitCase',
        'exitCaseAction',
        'exitClearanceAction',
        'createPostSeparationLetter',
      ]) {
        expect(source, contains(method), reason: 'Missing lifecycle service method $method');
      }
    });

    test('workspace exposes corporate lifecycle command center', () {
      final source = _read('lib/screens/hrms/employee_lifecycle_screen.dart');
      for (final label in <String>[
        'Employee Lifecycle Command Center',
        'Probation overdue',
        'Confirmation pending',
        'Promotions',
        'Increments',
        'Transfers',
        'On notice',
        'Clearance pending',
        'Settlement pending',
        'Probation / Confirmation Queue',
        'Exit / Clearance / Separation',
      ]) {
        expect(source, contains(label), reason: 'Missing lifecycle UI label $label');
      }
    });

    test('all controlled employee lifecycle action types remain explicit', () {
      final source = _read('lib/screens/hrms/employee_lifecycle_screen.dart');
      for (final action in <String>[
        'PROBATION_REVIEW',
        'PROBATION_EXTENSION',
        'CONFIRMATION',
        'PROMOTION',
        'INCREMENT',
        'TRANSFER',
      ]) {
        expect(source, contains("'$action'"), reason: 'Missing action $action');
      }
      for (final workflow in <String>[
        'SUBMIT_MANAGER',
        'MANAGER_REVIEW',
        'HR_REVIEW',
        'PENDING_APPROVAL',
        'APPROVED',
        'APPLY',
      ]) {
        expect(source, contains(workflow), reason: 'Missing workflow state/action $workflow');
      }
    });

    test('exit controls preserve clearance and separation gates', () {
      final source = _read('lib/screens/hrms/employee_lifecycle_screen.dart');
      for (final value in <String>[
        'START NOTICE',
        'START CLEARANCE',
        'SETTLEMENT READY',
        'SUBMIT APPROVAL',
        'APPROVE EXIT',
        'SEPARATE',
        'CLEARED',
        'BLOCKED',
        'WAIVED',
        'EXPERIENCE LETTER',
        'RELIEVING LETTER',
      ]) {
        expect(source, contains(value), reason: 'Missing exit control $value');
      }
    });

    test('role-gated UI mirrors backend default segregation', () {
      final source = _read('lib/screens/hrms/employee_lifecycle_screen.dart');
      expect(source, contains("bool get _canManage => const {'ADMIN', 'OFFICE'}.contains(_role)"));
      expect(source, contains("bool get _canManagerReview => const {'ADMIN', 'MANAGER'}.contains(_role)"));
      expect(source, contains("bool get _canHrReview => const {'ADMIN', 'OFFICE'}.contains(_role)"));
      expect(source, contains("bool get _canApprove => _role == 'ADMIN'"));
      expect(source, contains("bool get _canExitManage => const {'ADMIN', 'OFFICE'}.contains(_role)"));
      expect(source, contains("bool get _canExitClearance => const {'ADMIN', 'MANAGER', 'OFFICE'}.contains(_role)"));
    });

    test('Android and Windows responsive states are explicit', () {
      final source = _read('lib/screens/hrms/employee_lifecycle_screen.dart');
      expect(source, contains('constraints.maxWidth >= 1180'));
      expect(source, contains('_desktop()'));
      expect(source, contains('_mobile()'));
      expect(source, contains('DataTable'));
      expect(source, contains('SingleChildScrollView'));
      expect(source, contains('RefreshIndicator'));
      expect(source, contains('RETRY'));
      expect(source, contains('No lifecycle actions match the current filters.'));
      expect(source, contains('Select an employee or lifecycle row to open the unified timeline.'));
    });
  });
}
