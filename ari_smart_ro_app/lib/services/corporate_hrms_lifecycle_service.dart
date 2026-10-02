import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';
import 'corporate_hrms_service.dart';

/// Phase-2 Employee Lifecycle API surface for [CorporateHrmsService].
///
/// Kept as an extension so the Phase-1 service remains stable while lifecycle
/// endpoints can evolve independently. Import this file wherever lifecycle
/// methods are used.
extension CorporateHrmsLifecycleService on CorporateHrmsService {
  Future<Map<String, dynamic>> lifecycleCommandCenter() =>
      _lifecycleGetMap('/employees/hrms/lifecycle/command-center/');

  Future<Map<String, dynamic>> lifecycleProbationQueue() =>
      _lifecycleGetMap('/employees/hrms/lifecycle/probation-queue/');

  Future<Map<String, dynamic>> lifecycleTimeline(int employeeId) =>
      _lifecycleGetMap(
        '/employees/hrms/lifecycle/employees/$employeeId/timeline/',
      );

  Future<List<Map<String, dynamic>>> lifecycleActions({
    int? employeeId,
    String actionType = '',
    String status = '',
  }) async {
    final query = <String>[];
    if (employeeId != null) query.add('employee_id=$employeeId');
    if (actionType.trim().isNotEmpty) {
      query.add(
        'action_type=${Uri.encodeQueryComponent(actionType.trim().toUpperCase())}',
      );
    }
    if (status.trim().isNotEmpty) {
      query.add('status=${Uri.encodeQueryComponent(status.trim().toUpperCase())}');
    }
    final suffix = query.isEmpty ? '' : '?${query.join('&')}';
    return _lifecycleGetList('/employees/hrms/lifecycle/actions/$suffix');
  }

  Future<Map<String, dynamic>> createLifecycleAction(
    Map<String, dynamic> payload,
  ) =>
      _lifecyclePostMap(
        '/employees/hrms/lifecycle/actions/',
        payload,
        successCodes: const {201},
      );

  Future<Map<String, dynamic>> lifecycleWorkflow(
    int actionId,
    String action, {
    String reason = '',
    Map<String, dynamic> assessment = const {},
    Map<String, dynamic> extra = const {},
  }) =>
      _lifecyclePostMap(
        '/employees/hrms/lifecycle/actions/$actionId/workflow/',
        {
          'action': action.trim().toUpperCase(),
          if (reason.trim().isNotEmpty) 'reason': reason.trim(),
          if (assessment.isNotEmpty) 'assessment': assessment,
          ...extra,
        },
      );

  Future<List<Map<String, dynamic>>> exitCases({
    int? employeeId,
    String status = '',
  }) async {
    final query = <String>[];
    if (employeeId != null) query.add('employee_id=$employeeId');
    if (status.trim().isNotEmpty) {
      query.add('status=${Uri.encodeQueryComponent(status.trim().toUpperCase())}');
    }
    final suffix = query.isEmpty ? '' : '?${query.join('&')}';
    return _lifecycleGetList('/employees/hrms/lifecycle/exits/$suffix');
  }

  Future<Map<String, dynamic>> createExitCase(
    Map<String, dynamic> payload,
  ) {
    final canonicalPayload = Map<String, dynamic>.from(payload);
    final separationType =
        (canonicalPayload['separation_type'] ?? '').toString().trim().toUpperCase();
    // Older Flutter lifecycle UI builds used CONTRACT_END while the backend
    // contract and persisted model use CONTRACT_COMPLETION. Normalize at the
    // client API boundary so existing builds remain compatible without ever
    // persisting the legacy value.
    if (separationType == 'CONTRACT_END') {
      canonicalPayload['separation_type'] = 'CONTRACT_COMPLETION';
    }
    return _lifecyclePostMap(
      '/employees/hrms/lifecycle/exits/',
      canonicalPayload,
      successCodes: const {201},
    );
  }

  Future<Map<String, dynamic>> exitCaseAction(
    int caseId,
    String action, {
    String reason = '',
    Map<String, dynamic> extra = const {},
  }) =>
      _lifecyclePostMap(
        '/employees/hrms/lifecycle/exits/$caseId/action/',
        {
          'action': action.trim().toUpperCase(),
          if (reason.trim().isNotEmpty) 'reason': reason.trim(),
          ...extra,
        },
      );

  Future<Map<String, dynamic>> exitClearanceAction(
    int caseId,
    int clearanceId, {
    required String status,
    String note = '',
    String waiverReason = '',
    Map<String, dynamic> evidence = const {},
  }) =>
      _lifecyclePostMap(
        '/employees/hrms/lifecycle/exits/$caseId/clearances/$clearanceId/action/',
        {
          'status': status.trim().toUpperCase(),
          if (note.trim().isNotEmpty) 'note': note.trim(),
          if (waiverReason.trim().isNotEmpty)
            'waiver_reason': waiverReason.trim(),
          if (evidence.isNotEmpty) 'evidence': evidence,
        },
      );

  Future<Map<String, dynamic>> createPostSeparationLetter(
    int caseId,
    String letterType,
  ) =>
      _lifecyclePostMap(
        '/employees/hrms/lifecycle/exits/$caseId/post-separation-letter/',
        {'letter_type': letterType.trim().toUpperCase()},
        successCodes: const {200, 201},
      );
}

Future<Map<String, dynamic>> _lifecycleGetMap(String path) async {
  final response = await http
      .get(
        Uri.parse('${ApiService.baseUrl}$path'),
        headers: await ApiService.authHeaders(),
      )
      .timeout(const Duration(seconds: 25));
  if (response.statusCode != 200) throw Exception(_lifecycleMessage(response));
  final decoded = jsonDecode(response.body);
  if (decoded is! Map) {
    throw Exception('Corporate HRMS lifecycle response is invalid.');
  }
  return Map<String, dynamic>.from(decoded);
}

Future<List<Map<String, dynamic>>> _lifecycleGetList(String path) async {
  final response = await http
      .get(
        Uri.parse('${ApiService.baseUrl}$path'),
        headers: await ApiService.authHeaders(),
      )
      .timeout(const Duration(seconds: 25));
  if (response.statusCode != 200) throw Exception(_lifecycleMessage(response));
  final decoded = jsonDecode(response.body);
  if (decoded is! List) {
    throw Exception('Corporate HRMS lifecycle list response is invalid.');
  }
  return decoded
      .map((row) => Map<String, dynamic>.from(row as Map))
      .toList();
}

Future<Map<String, dynamic>> _lifecyclePostMap(
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
      .timeout(const Duration(seconds: 30));
  if (!successCodes.contains(response.statusCode)) {
    throw Exception(_lifecycleMessage(response));
  }
  final decoded = jsonDecode(response.body);
  if (decoded is! Map) {
    throw Exception('Corporate HRMS lifecycle response is invalid.');
  }
  return Map<String, dynamic>.from(decoded);
}

String _lifecycleMessage(http.Response response) {
  try {
    final decoded = jsonDecode(response.body);
    if (decoded is Map) {
      final data = Map<String, dynamic>.from(decoded);
      return (data['message'] ??
              data['detail'] ??
              'Corporate HRMS lifecycle request failed.')
          .toString();
    }
  } catch (_) {}
  return 'Corporate HRMS lifecycle request failed (HTTP ${response.statusCode}).';
}
