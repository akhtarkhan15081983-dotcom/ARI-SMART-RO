import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class AndyReply {
  final int conversationId;
  final int messageId;
  final String answer;
  const AndyReply({required this.conversationId, required this.messageId, required this.answer});
}

class AndyTranscription {
  final String text;
  final String? language;
  final double languageProbability;
  const AndyTranscription({required this.text, this.language, required this.languageProbability});
}

class AndyService {
  Future<AndyReply> chat(String message, {int? conversationId}) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/andy/chat/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'message': message, if (conversationId != null) 'conversation_id': conversationId}),
    );
    final data = response.body.isEmpty ? <String, dynamic>{} : Map<String, dynamic>.from(jsonDecode(response.body));
    if (response.statusCode != 200) throw Exception(data['message']?.toString() ?? 'ANDY is unavailable');
    return AndyReply(conversationId: data['conversation_id'] as int, messageId: data['message_id'] as int, answer: data['answer']?.toString() ?? '');
  }

  Future<AndyTranscription> transcribe(String audioPath) async {
    final headers = await ApiService.authHeaders();
    final request = http.MultipartRequest('POST', Uri.parse('${ApiService.baseUrl}/andy/transcribe/'));
    final authorization = headers['Authorization'];
    if (authorization != null) request.headers['Authorization'] = authorization;
    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    final data = response.body.isEmpty ? <String, dynamic>{} : Map<String, dynamic>.from(jsonDecode(response.body));
    if (response.statusCode != 200) throw Exception(data['message']?.toString() ?? 'Voice recognition failed');
    return AndyTranscription(
      text: data['text']?.toString() ?? '',
      language: data['language']?.toString(),
      languageProbability: (data['language_probability'] as num?)?.toDouble() ?? 0,
    );
  }

  Future<Uint8List> speak(String text) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/andy/speak/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'text': text}),
    );
    if (response.statusCode != 200) {
      String message = 'ANDY voice is unavailable';
      try {
        final data = Map<String, dynamic>.from(jsonDecode(response.body));
        message = data['message']?.toString() ?? message;
      } catch (_) {}
      throw Exception(message);
    }
    return response.bodyBytes;
  }

  Future<void> feedback(int messageId, int rating, {String correction = ''}) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/andy/feedback/$messageId/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({'rating': rating, 'correction': correction}),
    );
    if (response.statusCode != 200) throw Exception('Unable to save ANDY feedback');
  }
}
