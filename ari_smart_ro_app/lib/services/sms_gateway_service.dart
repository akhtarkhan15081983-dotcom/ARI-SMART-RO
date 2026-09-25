import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';

import 'api_service.dart';

class SmsGatewayService {
  const SmsGatewayService();

  static const MethodChannel _channel = MethodChannel(
    'com.arismartro.app/sms_gateway',
  );

  Future<Map<String, dynamic>> fetchStatus() async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}/auth/admin/sms-gateway/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> provision({
    required String phoneNumber,
    String name = 'ARI Office SMS Gateway',
  }) async {
    if (!Platform.isAndroid) {
      throw Exception('The SIM SMS gateway can only run on an Android phone.');
    }

    final permission = await Permission.sms.request();
    if (!permission.isGranted) {
      throw Exception(
        'Allow SMS permission on this office phone so ARI can receive verification messages.',
      );
    }

    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}/auth/admin/sms-gateway/'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'phone_number': phoneNumber.trim(),
            'name': name.trim(),
          }),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 201) throw Exception(_message(response));

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final gateway = Map<String, dynamic>.from(data['gateway'] as Map);
    await _channel.invokeMethod<bool>('configure', {
      'gatewayId': gateway['device_id'].toString(),
      'gatewayKey': gateway['api_key'].toString(),
      'baseUrl': ApiService.baseUrl,
    });
    return data;
  }

  Future<void> disable() async {
    final response = await http
        .delete(
          Uri.parse('${ApiService.baseUrl}/auth/admin/sms-gateway/'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 20));
    if (response.statusCode != 200) throw Exception(_message(response));
    if (Platform.isAndroid) {
      await _channel.invokeMethod<bool>('clear');
    }
  }

  Future<bool> isConfiguredOnThisPhone() async {
    if (!Platform.isAndroid) return false;
    return await _channel.invokeMethod<bool>('isConfigured') ?? false;
  }

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['message']?.toString() ?? 'Unable to configure SMS gateway.';
    } catch (_) {
      return 'Unable to configure SMS gateway.';
    }
  }
}
