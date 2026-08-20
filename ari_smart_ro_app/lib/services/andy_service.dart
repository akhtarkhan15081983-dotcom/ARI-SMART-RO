import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class AndyReply {
  final int conversationId;
  final int messageId;
  final String answer;
  const AndyReply({required this.conversationId, required this.messageId, required this.answer});
}

class AndyService {
  Future<AndyReply> chat(String message, {int? conversationId}) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/andy/chat/'),
      headers: await ApiService.authHeaders(),
      body: jsonEncode({
        'message': message,
        if (conversationId != null) 'conversation_id': conversationId,
      }),
    );
    final data = response.body.isEmpty ? <String, dynamic>{} : Map<String, dynamic>.from(jsonDecode(response.body));
    if (response.statusCode != 200) {
      throw Exception(data['message']?.toString() ?? 'ANDY is unavailable');
    }
    return AndyReply(
      conversationId: data['conversation_id'] as int,
      messageId: data['message_id'] as int,
      answer: data['answer']?.toString() ?? '',
    );
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
