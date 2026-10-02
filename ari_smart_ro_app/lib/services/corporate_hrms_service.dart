import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class CorporateHrmsService {
  Future<Map<String, dynamic>> dashboard() =>
      _getMap('/employees/hrms/corporate-dashboard/');

  Future<List<Map<String, dynamic>>> directory() async {
    final data = await _getMap('/employees/hrms/directory/');
    return _rows(data, 'employees');
  }

  Future<Map<String, dynamic>> employeeFile(int employeeId) =>
      _getMap('/employees/hrms/employees/$employeeId/');

  Future<Map<String, dynamic>> employeeDocuments(int employeeId) =>
      _getMap('/employees/hrms/employees/$employeeId/documents/');

  Future<Map<String, dynamic>> recruitmentSummary() =>
      _getMap('/employees/hrms/recruitment/summary/');

  Future<List<Map<String, dynamic>>> recruitmentRequisitions() async =>
      _rows(await _getMap('/employees/hrms/recruitment/requisitions/'), 'requisitions');

  Future<List<Map<String, dynamic>>> recruitmentJobs() async =>
      _rows(await _getMap('/employees/hrms/recruitment/jobs/'), 'jobs');

  Future<List<Map<String, dynamic>>> recruitmentCandidates({String query = ''}) async {
    final suffix = query.trim().isEmpty ? '' : '?q=${Uri.encodeQueryComponent(query.trim())}';
    return _rows(await _getMap('/employees/hrms/recruitment/candidates/$suffix'), 'candidates');
  }

  Future<List<Map<String, dynamic>>> recruitmentApplications({String stage = ''}) async {
    final suffix = stage.trim().isEmpty ? '' : '?stage=${Uri.encodeQueryComponent(stage.trim().toUpperCase())}';
    return _rows(await _getMap('/employees/hrms/recruitment/applications/$suffix'), 'applications');
  }

  Future<List<Map<String, dynamic>>> recruitmentInterviews() async =>
      _rows(await _getMap('/employees/hrms/recruitment/interviews/'), 'interviews');

  Future<List<Map<String, dynamic>>> recruitmentOffers() async =>
      _rows(await _getMap('/employees/hrms/recruitment/offers/'), 'offers');

  Future<Map<String, dynamic>> createRequisition(Map<String, dynamic> payload) =>
      _postMap('/employees/hrms/recruitment/requisitions/', payload, successCodes: const {201});

  Future<Map<String, dynamic>> requisitionAction(int id, String action, {String reason = ''}) =>
      _postMap('/employees/hrms/recruitment/requisitions/$id/action/', {
        'action': action,
        if (reason.trim().isNotEmpty) 'reason': reason.trim(),
      });

  Future<Map<String, dynamic>> createInterview(Map<String, dynamic> payload) =>
      _postMap('/employees/hrms/recruitment/interviews/', payload, successCodes: const {201});

  Future<Map<String, dynamic>> interviewAction(int id, String action, {String reason = ''}) =>
      _postMap('/employees/hrms/recruitment/interviews/$id/action/', {
        'action': action,
        if (reason.trim().isNotEmpty) 'reason': reason.trim(),
      });

  Future<Map<String, dynamic>> submitInterviewFeedback(
    int interviewId,
    Map<String, dynamic> payload,
  ) => _postMap(
        '/employees/hrms/recruitment/interviews/$interviewId/feedback/',
        payload,
        successCodes: const {201},
      );

  Future<Map<String, dynamic>> recruitmentDecision(
    int applicationId,
    String action, {
    required String reason,
  }) =>
      _postMap('/employees/hrms/recruitment/applications/$applicationId/decision/', {
        'action': action,
        'reason': reason.trim(),
      });

  Future<Map<String, dynamic>> createCandidateOffer(Map<String, dynamic> payload) =>
      _postMap('/employees/hrms/recruitment/offers/', payload, successCodes: const {201});

  Future<Map<String, dynamic>> offerAction(
    int offerId,
    String action, {
    String reason = '',
    Map<String, dynamic> evidence = const {},
  }) =>
      _postMap('/employees/hrms/recruitment/offers/$offerId/action/', {
        'action': action,
        if (reason.trim().isNotEmpty) 'reason': reason.trim(),
        if (evidence.isNotEmpty) 'evidence': evidence,
      });

  Future<Map<String, dynamic>> convertCandidate(
    int applicationId, {
    bool capacityOverride = false,
    String overrideReason = '',
  }) =>
      _postMap('/employees/hrms/recruitment/applications/$applicationId/convert/', {
        if (capacityOverride) 'capacity_override': true,
        if (overrideReason.trim().isNotEmpty) 'override_reason': overrideReason.trim(),
      }, successCodes: const {200, 201});

  Future<Map<String, dynamic>> lettersDashboard() =>
      _getMap('/employees/hrms/letters/dashboard/');

  Future<List<Map<String, dynamic>>> letterTemplates({String type = ''}) async {
    final suffix = type.trim().isEmpty ? '' : '?letter_type=${Uri.encodeQueryComponent(type.trim().toUpperCase())}';
    return _rows(await _getMap('/employees/hrms/letters/templates/$suffix'), 'templates');
  }

  Future<Map<String, dynamic>> createLetterTemplate(Map<String, dynamic> payload) =>
      _postMap('/employees/hrms/letters/templates/', payload, successCodes: const {201});

  Future<Map<String, dynamic>> letterTemplateAction(int id, String action) =>
      _postMap('/employees/hrms/letters/templates/$id/action/', {'action': action});

  Future<List<Map<String, dynamic>>> letterWorkflows({String status = ''}) async {
    final suffix = status.trim().isEmpty ? '' : '?status=${Uri.encodeQueryComponent(status.trim().toUpperCase())}';
    return _rows(await _getMap('/employees/hrms/letters/workflows/$suffix'), 'workflows');
  }

  Future<Map<String, dynamic>> createLetterWorkflow(Map<String, dynamic> payload) =>
      _postMap('/employees/hrms/letters/workflows/', payload, successCodes: const {201});

  Future<Map<String, dynamic>> letterWorkflowAction(
    int id,
    String action, {
    String reason = '',
  }) =>
      _postMap('/employees/hrms/letters/workflows/$id/action/', {
        'action': action,
        if (reason.trim().isNotEmpty) 'reason': reason.trim(),
      });

  Future<List<Map<String, dynamic>>> issuedLetters({int? employeeId}) async {
    final suffix = employeeId == null ? '' : '?employee_id=$employeeId';
    return _rows(await _getMap('/employees/hrms/letters/issued/$suffix'), 'letters');
  }

  Future<Map<String, dynamic>> acknowledgeLetter(
    int letterId,
    String status, {
    String note = '',
    Map<String, dynamic> evidence = const {},
  }) =>
      _postMap('/employees/hrms/letters/issued/$letterId/acknowledge/', {
        'status': status,
        if (note.trim().isNotEmpty) 'note': note.trim(),
        if (evidence.isNotEmpty) 'evidence': evidence,
      });

  Future<Map<String, dynamic>> bgvPolicy() =>
      _getMap('/employees/hrms/bgv/policy/');

  Future<Map<String, dynamic>> updateBgvPolicy({
    required bool mandatoryBeforeReady,
    List<String>? requiredChecks,
  }) =>
      _patchMap('/employees/hrms/bgv/policy/', {
        'mandatory_before_ready': mandatoryBeforeReady,
        if (requiredChecks != null) 'required_checks': requiredChecks,
      });

  Future<List<Map<String, dynamic>>> bgvCases({int? employeeId, int? applicationId}) async {
    final query = <String>[];
    if (employeeId != null) query.add('employee_id=$employeeId');
    if (applicationId != null) query.add('application_id=$applicationId');
    final suffix = query.isEmpty ? '' : '?${query.join('&')}';
    return _rows(await _getMap('/employees/hrms/bgv/cases/$suffix'), 'cases');
  }

  Future<Map<String, dynamic>> createBgvCase({int? employeeId, int? applicationId}) =>
      _postMap('/employees/hrms/bgv/cases/', {
        if (employeeId != null) 'employee_id': employeeId,
        if (applicationId != null) 'application_id': applicationId,
      }, successCodes: const {200, 201});

  Future<Map<String, dynamic>> upsertBgvCheck(
    int caseId,
    Map<String, dynamic> payload,
  ) =>
      _postMap('/employees/hrms/bgv/cases/$caseId/checks/', payload, successCodes: const {200, 201});

  Future<Map<String, dynamic>> decideBgv(
    int caseId,
    String decision, {
    required String reason,
  }) =>
      _postMap('/employees/hrms/bgv/cases/$caseId/decision/', {
        'decision': decision,
        'reason': reason.trim(),
      });

  Future<Map<String, dynamic>> uploadEmployeeDocument(
    int employeeId, {
    required String documentType,
    required PlatformFile file,
    String documentNumber = '',
    String expiryDate = '',
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/documents/',
      ),
    );
    final headers = await ApiService.authHeaders();
    headers.remove('Content-Type');
    request.headers.addAll(headers);
    request.fields['document_type'] = documentType;
    if (documentNumber.trim().isNotEmpty) {
      request.fields['document_number'] = documentNumber.trim();
    }
    if (expiryDate.trim().isNotEmpty) {
      request.fields['expiry_date'] = expiryDate.trim();
    }
    if (file.bytes != null) {
      request.files.add(
        http.MultipartFile.fromBytes('file', file.bytes!, filename: file.name),
      );
    } else if (file.path != null) {
      request.files.add(await http.MultipartFile.fromPath('file', file.path!));
    } else {
      throw Exception('Selected document file is unavailable.');
    }
    final streamed = await request.send().timeout(const Duration(seconds: 45));
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> reviewEmployeeDocument(
    int employeeId, {
    required int documentId,
    required String action,
    required String reason,
  }) async {
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/documents/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'document_id': documentId,
            'action': action,
            'reason': reason,
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> createEmployee(
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/employees/manage/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode != 201) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> updateProfile(
    int employeeId,
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/profile/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> updateLifecycle(
    int employeeId,
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .patch(
          Uri.parse('${ApiService.baseUrl}/employees/hrms/employees/$employeeId/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> lifecycleAction(
    int employeeId,
    String action, {
    String note = '',
    Map<String, dynamic> extra = const {},
  }) async {
    final response = await http
        .post(
          Uri.parse(
            '${ApiService.baseUrl}/employees/hrms/employees/$employeeId/action/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({'action': action, 'note': note, ...extra}),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> _getMap(String path) async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> _postMap(
    String path,
    Map<String, dynamic> payload, {
    Set<int> successCodes = const {200},
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 25));
    if (!successCodes.contains(response.statusCode)) {
      throw Exception(_message(response));
    }
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> _patchMap(
    String path,
    Map<String, dynamic> payload,
  ) async {
    final response = await http
        .patch(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  List<Map<String, dynamic>> _rows(Map<String, dynamic> data, String key) =>
      (data[key] as List<dynamic>? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['message'] ??
              data['detail'] ??
              'Corporate HRMS request failed.')
          .toString();
    } catch (_) {
      return 'Corporate HRMS request failed (HTTP ${response.statusCode}).';
    }
  }
}
