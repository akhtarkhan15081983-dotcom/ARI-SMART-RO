import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_service.dart';

class AdminROPassportService {
  const AdminROPassportService();

  Future<Map<String, dynamic>> fetchRegistry({String query = ''}) async {
    const pageSize = 250;
    var page = 1;
    final allCustomers = <dynamic>[];
    var activeAlarmCount = 0;
    Map<String, dynamic>? merged;

    while (true) {
      final params = <String, String>{
        'page': '$page',
        'page_size': '$pageSize',
        if (query.trim().isNotEmpty) 'q': query.trim(),
      };
      final uri = Uri.parse(
        '${ApiService.baseUrl}/jobs/admin/ro-parts-passports/',
      ).replace(queryParameters: params);
      final response = await http
          .get(uri, headers: await ApiService.authHeaders())
          .timeout(const Duration(seconds: 25));
      final body = _decode(response.body);
      if (response.statusCode != 200) {
        throw Exception(
          body['detail']?.toString() ?? 'Unable to load Digital RO registry.',
        );
      }

      merged ??= Map<String, dynamic>.from(body);
      final pageCustomers = body['customers'] as List<dynamic>? ?? const [];
      allCustomers.addAll(pageCustomers);
      activeAlarmCount += (body['active_alarm_count'] as num?)?.toInt() ?? 0;

      if (body['has_more'] != true || pageCustomers.isEmpty) {
        break;
      }
      page = (body['next_page'] as num?)?.toInt() ?? (page + 1);
    }

    final result = merged ?? <String, dynamic>{};
    result['customers'] = allCustomers;
    result['customer_count'] =
        (result['customer_count'] as num?)?.toInt() ?? allCustomers.length;
    result['returned_customer_count'] = allCustomers.length;
    result['active_alarm_count'] = activeAlarmCount;
    result['has_more'] = false;
    result['next_page'] = null;
    return result;
  }

  Future<Map<String, dynamic>> updateRentDueDay({
    required int customerId,
    required int rentDueDay,
  }) async {
    final response = await http
        .patch(
          Uri.parse(
            '${ApiService.baseUrl}/jobs/admin/ro-parts-passports/',
          ),
          headers: await ApiService.authHeaders(),
          body: jsonEncode({
            'customer_id': customerId,
            'rent_due_day': rentDueDay,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(
        body['detail']?.toString() ?? 'Unable to update RO rent due date.',
      );
    }
    return body;
  }

  Future<Map<String, dynamic>> fetchSetupOptions() async {
    final response = await http
        .get(
          Uri.parse(
            '${ApiService.baseUrl}/jobs/admin/ro-parts-passports/setup/',
          ),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 25));
    final body = _decode(response.body);
    if (response.statusCode != 200) {
      throw Exception(
        body['detail']?.toString() ?? 'Unable to load Digital RO setup options.',
      );
    }
    return body;
  }

  Future<Map<String, dynamic>> saveInitialBaseline({
    required int customerId,
    int? assetId,
    required int roModelId,
    required String serialNumber,
    required String ownershipType,
    String? saleInstallationDate,
    String? nextFilterChangeDate,
    int? outputTdsAttentionLevel,
    bool alarmMonitoringEnabled = true,
    required List<String> partKeys,
    List<String> photoPaths = const [],
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse(
        '${ApiService.baseUrl}/jobs/admin/ro-parts-passports/setup/',
      ),
    );
    final headers = await ApiService.authHeaders();
    headers.remove('Content-Type');
    request.headers.addAll(headers);
    request.fields['customer_id'] = '$customerId';
    if (assetId != null) request.fields['asset_id'] = '$assetId';
    request.fields['ro_model_id'] = '$roModelId';
    request.fields['serial_number'] = serialNumber.trim();
    request.fields['ownership_type'] = ownershipType.trim().toUpperCase();
    if (saleInstallationDate != null &&
        saleInstallationDate.trim().isNotEmpty) {
      request.fields['sale_installation_date'] =
          saleInstallationDate.trim();
    }
    if (nextFilterChangeDate != null &&
        nextFilterChangeDate.trim().isNotEmpty) {
      request.fields['next_filter_change_date'] =
          nextFilterChangeDate.trim();
    }
    if (outputTdsAttentionLevel != null) {
      request.fields['output_tds_attention_level'] =
          '$outputTdsAttentionLevel';
    }
    request.fields['alarm_monitoring_enabled'] =
        alarmMonitoringEnabled ? 'true' : 'false';
    request.fields['parts'] = jsonEncode(
      partKeys.map((key) => {'part_key': key}).toList(),
    );

    for (final path in photoPaths.take(4)) {
      request.files.add(await http.MultipartFile.fromPath('photos', path));
    }

    final streamed = await request.send().timeout(const Duration(seconds: 90));
    final response = await http.Response.fromStream(streamed);
    final body = _decode(response.body);
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception(
        body['detail']?.toString() ?? 'Unable to save Digital RO baseline.',
      );
    }
    return body;
  }

  Map<String, dynamic> _decode(String value) {
    if (value.trim().isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(value);
    return decoded is Map
        ? Map<String, dynamic>.from(decoded)
        : <String, dynamic>{};
  }
}
