import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../models/service_model.dart';
import 'api_service.dart';

class ServiceService {
  Future<List<ServiceModel>> getServices() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/service/'),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      return data.map((item) => ServiceModel.fromJson(item)).toList();
    }

    throw Exception('Failed to load services');
  }

  Future<ServiceModel> getServiceDetail(int id) async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/service/$id/'),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      return ServiceModel.fromJson(jsonDecode(response.body));
    }

    throw Exception('Failed to load service detail');
  }

  Future<bool> completeService(int id) async {
    final response = await http.post(
      Uri.parse('${ApiService.baseUrl}/service/$id/complete/'),
      headers: await ApiService.authHeaders(),
    );

    return response.statusCode == 200 || response.statusCode == 201;
  }

  Future<String> exportServicesExcel() async {
    final response = await http.get(
      Uri.parse('${ApiService.baseUrl}/service/export/'),
      headers: await ApiService.authHeaders(),
    );

    if (response.statusCode == 200) {
      final tempDir = await getTemporaryDirectory();
      final file = File(
        '${tempDir.path}/service_report_${DateTime.now().millisecondsSinceEpoch}.xlsx',
      );
      await file.writeAsBytes(response.bodyBytes);
      return file.path;
    }

    throw Exception('Failed to export service report');
  }
}
