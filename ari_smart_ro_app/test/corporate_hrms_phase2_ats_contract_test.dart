import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

String _read(String relativePath) => File(relativePath).readAsStringSync();

void main() {
  group('Corporate HRMS Phase-2 ATS Flutter contracts', () {
    test('HRMS command center exposes Talent Acquisition navigation', () {
      final source = _read('lib/screens/hrms/hrms_screen.dart');
      expect(source, contains("import 'recruitment_screen.dart';"));
      expect(source, contains('Talent Acquisition'));
      expect(source, contains('RecruitmentScreen'));
    });

    test('ATS service covers full controlled backend workflow', () {
      final source = _read('lib/services/corporate_hrms_service.dart');
      for (final endpoint in <String>[
        '/employees/hrms/recruitment/summary/',
        '/employees/hrms/recruitment/requisitions/',
        '/employees/hrms/recruitment/jobs/',
        '/employees/hrms/recruitment/candidates/',
        '/employees/hrms/recruitment/applications/',
        '/employees/hrms/recruitment/interviews/',
        '/employees/hrms/recruitment/offers/',
      ]) {
        expect(source, contains(endpoint), reason: 'Missing ATS endpoint $endpoint');
      }
      for (final method in <String>[
        'recruitmentSummary',
        'recruitmentRequisitions',
        'recruitmentJobs',
        'recruitmentCandidates',
        'recruitmentApplications',
        'recruitmentInterviews',
        'submitInterviewFeedback',
        'recruitmentDecision',
        'recruitmentOffers',
        'offerAction',
        'convertCandidate',
      ]) {
        expect(source, contains(method), reason: 'Missing service method $method');
      }
    });

    test('ATS workspace exposes enterprise workflow and dashboard metrics', () {
      final source = _read('lib/screens/hrms/recruitment_screen.dart');
      for (final label in <String>[
        'Recruitment Command Center',
        'Manpower Requisitions',
        'Job Openings',
        'Candidate Pipeline',
        'Interview Schedule',
        'Offers & Joining Conversion',
        'Open requisitions',
        'Pending approvals',
        'Open vacancies',
        'Interviews due',
        'Feedback pending',
        'Selected • no offer',
        'Offer approvals',
        'Awaiting response',
        'Accepted • joining',
        'Joined this month',
      ]) {
        expect(source, contains(label), reason: 'Missing ATS UI label $label');
      }
      expect(source, contains("_summary['ats']"));
      expect(source, contains("_summary['action_queue']"));
    });

    test('pipeline stages and exceptional exits remain explicit', () {
      final source = _read('lib/screens/hrms/recruitment_screen.dart');
      for (final stage in <String>[
        'APPLIED',
        'SCREENING',
        'INTERVIEW',
        'SELECTED',
        'OFFERED',
        'JOINED',
        'REJECTED',
        'WITHDRAWN',
      ]) {
        expect(source, contains("'$stage'"), reason: 'Missing pipeline stage $stage');
      }
      expect(source.contains('no frontend bypass'), isFalse);
      expect(source, contains('recruitmentDecision'));
    });

    test('interview feedback is clearly final and immutable', () {
      final source = _read('lib/screens/hrms/recruitment_screen.dart');
      expect(source, contains('Final interview feedback'));
      expect(source, contains('STRONG_HIRE'));
      expect(source, contains('NO_HIRE'));
      expect(source, contains('SUBMIT FINAL'));
      expect(source, contains('Submitting makes this feedback final and immutable.'));
      expect(source, contains('FINAL / READ ONLY'));
    });

    test('selection offer and conversion actions stay role gated', () {
      final source = _read('lib/screens/hrms/recruitment_screen.dart');
      expect(source, contains("bool get _canManage => const {'ADMIN', 'OFFICE'}.contains(_role)"));
      expect(source, contains("bool get _canApprove => _role == 'ADMIN'"));
      expect(source, contains("bool get _canInterview => const {'ADMIN', 'MANAGER'}.contains(_role)"));
      expect(source, contains("bool get _canConvert => _role == 'ADMIN'"));
      expect(source, contains('SELECT'));
      expect(source, contains('REJECT'));
      expect(source, contains('REOPEN'));
      expect(source, contains('SUBMIT APPROVAL'));
      expect(source, contains('ISSUE OFFER'));
      expect(source, contains('RECORD ACCEPTANCE'));
      expect(source, contains('CONVERT TO EMPLOYEE'));
      expect(source, contains('Admin vacancy override'));
      expect(source, contains('ONBOARDING / CREATED'));
    });

    test('ATS workspace preserves Android and Windows responsive navigation', () {
      final source = _read('lib/screens/hrms/recruitment_screen.dart');
      expect(source, contains('constraints.maxWidth >= 1050'));
      expect(source, contains('NavigationRail'));
      expect(source, contains('NavigationBar'));
      expect(source, contains('constraints.maxWidth >= 980'));
      expect(source, contains('SingleChildScrollView'));
      expect(source, contains('RefreshIndicator'));
      expect(source, contains('RETRY'));
    });
  });
}
