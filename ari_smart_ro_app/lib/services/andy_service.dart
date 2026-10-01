import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class AndyReply {
  final int conversationId;
  final int messageId;
  final String answer;
  final String? source;
  final String? intent;
  final String? avatarState;
  final bool requiresConfirmation;
  final int? pendingActionId;
  final String? actionSummary;

  const AndyReply({
    required this.conversationId,
    required this.messageId,
    required this.answer,
    this.source,
    this.intent,
    this.avatarState,
    this.requiresConfirmation = false,
    this.pendingActionId,
    this.actionSummary,
  });
}

class AndyActionResult {
  final bool success;
  final String answer;
  final String? status;
  final String? avatarState;

  const AndyActionResult({
    required this.success,
    required this.answer,
    this.status,
    this.avatarState,
  });
}

class AndyTranscription {
  final String text;
  final String? language;
  final double languageProbability;
  final String? avatarState;

  const AndyTranscription({
    required this.text,
    this.language,
    required this.languageProbability,
    this.avatarState,
  });
}

class AndyService {
  static const _requestTimeout = Duration(seconds: 45);
  static const _voicePollTimeout = Duration(minutes: 3);

  Exception _unavailable([String feature = 'ANDY']) => Exception(
        '$feature is temporarily unavailable. ARI SMART RO ke normal features aap use kar sakte hain; thodi der baad retry karein.',
      );

  Map<String, dynamic> _decode(http.Response response) {
    if (response.body.isEmpty) return <String, dynamic>{};
    return Map<String, dynamic>.from(jsonDecode(response.body));
  }

  Future<AndyReply> chat(String message, {int? conversationId}) async {
    late http.Response response;
    try {
      response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/andy/chat/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode({
              'message': message,
              'conversation_id': ?conversationId,
            }),
          )
          .timeout(_requestTimeout);
    } on TimeoutException {
      throw _unavailable();
    } on http.ClientException {
      throw _unavailable();
    }
    final data = _decode(response);
    if (response.statusCode != 200) {
      throw Exception(data['message']?.toString() ?? 'ANDY is unavailable');
    }
    return AndyReply(
      conversationId: data['conversation_id'] as int,
      messageId: data['message_id'] as int,
      answer: data['answer']?.toString() ?? '',
      source: data['source']?.toString(),
      intent: data['intent']?.toString(),
      avatarState: data['avatar_state']?.toString(),
      requiresConfirmation: data['requires_confirmation'] == true,
      pendingActionId: (data['pending_action_id'] as num?)?.toInt(),
      actionSummary: data['action_summary']?.toString(),
    );
  }

  Future<AndyActionResult> confirmAction(int actionId, bool confirm) async {
    late http.Response response;
    try {
      response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/andy/actions/$actionId/confirm/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode({'confirm': confirm}),
          )
          .timeout(_requestTimeout);
    } on TimeoutException {
      throw _unavailable('ANDY action service');
    } on http.ClientException {
      throw _unavailable('ANDY action service');
    }
    final data = _decode(response);
    if (response.statusCode != 200) {
      throw Exception(
        data['message']?.toString() ?? 'Unable to complete ANDY action',
      );
    }
    return AndyActionResult(
      success: data['success'] == true,
      answer: data['answer']?.toString() ?? '',
      status: data['status']?.toString(),
      avatarState: data['avatar_state']?.toString(),
    );
  }

  Future<AndyTranscription> transcribe(String audioPath) async {
    final headers = await ApiService.authHeaders();
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiService.baseUrl}/andy/transcribe/'),
    );
    final authorization = headers['Authorization'];
    if (authorization != null) request.headers['Authorization'] = authorization;
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));
    late http.StreamedResponse streamed;
    late http.Response response;
    try {
      streamed = await request.send().timeout(_requestTimeout);
      response = await http.Response.fromStream(streamed).timeout(_requestTimeout);
    } on TimeoutException {
      throw _unavailable('ANDY voice recognition');
    } on http.ClientException {
      throw _unavailable('ANDY voice recognition');
    }
    final data = _decode(response);
    if (response.statusCode != 200) {
      throw Exception(
        data['message']?.toString() ?? 'Voice recognition failed',
      );
    }
    return AndyTranscription(
      text: data['text']?.toString() ?? '',
      language: data['language']?.toString(),
      languageProbability:
          (data['language_probability'] as num?)?.toDouble() ?? 0,
      avatarState: data['avatar_state']?.toString(),
    );
  }

  Future<Uint8List> speak(String text) async {
    late http.Response response;
    try {
      response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/andy/speak/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode({'text': text}),
          )
          .timeout(_requestTimeout);
    } on TimeoutException {
      throw _unavailable('ANDY voice');
    } on http.ClientException {
      throw _unavailable('ANDY voice');
    }
    if (response.statusCode != 202) {
      String message = 'ANDY voice is unavailable';
      try {
        final data = _decode(response);
        message = data['message']?.toString() ?? message;
      } catch (_) {}
      throw Exception(message);
    }
    final queued = _decode(response);
    final jobId = queued['job_id']?.toString();
    if (jobId == null || jobId.isEmpty) {
      throw Exception('ANDY voice job could not be started');
    }

    // Production inference is external to Django. Keep polling bounded so an
    // unavailable AI service never traps the mobile/Windows client indefinitely.
    final deadline = DateTime.now().add(_voicePollTimeout);
    while (DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(const Duration(seconds: 1));
      late http.Response poll;
      try {
        poll = await http
            .get(
              Uri.parse('${ApiService.baseUrl}/andy/speak/$jobId/'),
              headers: await ApiService.authHeaders(),
            )
            .timeout(_requestTimeout);
      } on TimeoutException {
        throw _unavailable('ANDY voice');
      } on http.ClientException {
        throw _unavailable('ANDY voice');
      }
      if (poll.statusCode == 200 &&
          poll.headers['content-type']?.startsWith('audio/wav') == true) {
        return poll.bodyBytes;
      }
      if (poll.statusCode == 200) continue;

      String message = 'ANDY voice is unavailable';
      try {
        message = _decode(poll)['message']?.toString() ?? message;
      } catch (_) {}
      throw Exception(message);
    }
    throw _unavailable('ANDY voice');
  }

  Future<void> feedback(
    int messageId,
    int rating, {
    String correction = '',
  }) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/andy/feedback/$messageId/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'rating': rating, 'correction': correction}),
    );
    if (response.statusCode != 200) {
      throw Exception('Unable to save ANDY feedback');
    }
  }
}
