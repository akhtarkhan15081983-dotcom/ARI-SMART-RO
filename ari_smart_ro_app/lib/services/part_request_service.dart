import 'dart:convert';
import 'package:http/http.dart' as http;
import 'api_service.dart';

class PartOption {
  const PartOption({required this.id, required this.name, required this.code, required this.unit});
  final int id;
  final String name;
  final String code;
  final String unit;
  factory PartOption.fromJson(Map<String, dynamic> json) => PartOption(
    id: (json['id'] as num).toInt(),
    name: json['name']?.toString() ?? '',
    code: json['code']?.toString() ?? '',
    unit: json['unit']?.toString() ?? '',
  );
}

class EngineerPartRequest {
  const EngineerPartRequest({required this.id, required this.partName, required this.partCode, required this.quantity, required this.status, required this.remarks});
  final int id;
  final String partName;
  final String partCode;
  final int quantity;
  final String status;
  final String remarks;
  factory EngineerPartRequest.fromJson(Map<String, dynamic> json) => EngineerPartRequest(
    id: (json['id'] as num).toInt(),
    partName: json['part_name']?.toString() ?? '',
    partCode: json['part_code']?.toString() ?? '',
    quantity: (json['quantity'] as num).toInt(),
    status: json['status']?.toString() ?? 'PENDING',
    remarks: json['remarks']?.toString() ?? '',
  );
}

class PartRequestService {
  const PartRequestService({this.client});
  final http.Client? client;

  Future<List<PartOption>> fetchParts() async {
    final c = client ?? http.Client();
    final response = await c.get(Uri.parse('${ApiService.baseUrl}/inventory/parts/'), headers: await ApiService.authHeaders());
    if (response.statusCode != 200) throw Exception('Unable to load parts');
    return (jsonDecode(response.body) as List).map((e) => PartOption.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<EngineerPartRequest>> fetchRequests() async {
    final c = client ?? http.Client();
    final response = await c.get(Uri.parse('${ApiService.baseUrl}/inventory/part-requests/'), headers: await ApiService.authHeaders());
    if (response.statusCode != 200) throw Exception('Unable to load part requests');
    return (jsonDecode(response.body) as List).map((e) => EngineerPartRequest.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<void> createRequest({required int partId, required int quantity, String remarks = ''}) async {
    final c = client ?? http.Client();
    final response = await c.post(
      Uri.parse('${ApiService.baseUrl}/inventory/part-requests/'),
      headers: {...await ApiService.authHeaders(), 'Content-Type': 'application/json'},
      body: jsonEncode({'part': partId, 'quantity': quantity, 'remarks': remarks}),
    );
    if (response.statusCode != 201) throw Exception('Unable to create part request');
  }
}
