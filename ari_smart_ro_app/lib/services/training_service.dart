import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class TrainingService {
  const TrainingService();

  Future<Map<String, dynamic>> listAssignments() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/training/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> detail(int assignmentId) async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/employees/hrms/training/$assignmentId/'),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<void> completeLesson(
    int assignmentId,
    int lessonId, {
    required bool videoWatched,
  }) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/training/$assignmentId/lessons/$lessonId/complete/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'video_watched': videoWatched}),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
  }

  Future<Map<String, dynamic>> submitQuiz(
    int assignmentId,
    Map<int, String> answers,
  ) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/training/$assignmentId/quiz/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'answers': answers.map((key, value) => MapEntry(key.toString(), value)),
      }),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }


  Future<void> saveTrainerReview(
    int assignmentId,
    int lessonId, {
    required int behaviourScore,
    required int communicationScore,
    required int knowledgeScore,
    required String strengths,
    required String gaps,
    required String coachingAction,
    String notes = '',
  }) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/training/$assignmentId/lessons/$lessonId/trainer-review/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'behaviour_score': behaviourScore,
        'communication_score': communicationScore,
        'knowledge_score': knowledgeScore,
        'strengths': strengths.trim(),
        'gaps': gaps.trim(),
        'coaching_action': coachingAction.trim(),
        'notes': notes.trim(),
      }),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
  }


  Future<Map<String, dynamic>> issueCertificate(int assignmentId) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/training/$assignmentId/certificate/issue/',
      ),
      headers: await ApiService.authHeaders(),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<Map<String, dynamic>> revokeCertificate(
    int assignmentId, {
    String reason = '',
  }) async {
    final response = await http.post(
      Uri.parse(
        '${ApiService.baseUrl}/employees/hrms/training/$assignmentId/certificate/revoke/',
      ),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'reason': reason.trim()}),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  String _message(http.Response response) {
    try {
      final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
      return (data['detail'] ?? 'Training request failed.').toString();
    } catch (_) {
      return 'Training request failed (HTTP ${response.statusCode}).';
    }
  }
}
