import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import 'api_service.dart';

class ReportService {
  static const MethodChannel _downloadsChannel = MethodChannel(
    'com.arismartro.app/downloads',
  );

  Future<Map<String, dynamic>> getSummary({
    required String period,
    required DateTime date,
  }) async {
    final uri = Uri.parse(
      "${ApiService.baseUrl}/reports/summary/",
    ).replace(queryParameters: {"period": period, "date": _dateValue(date)});

    final response = await http
        .get(uri, headers: await ApiService.authHeaders())
        .timeout(const Duration(seconds: 30));

    if (response.statusCode != 200) {
      throw Exception(_message(response));
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<String> downloadExcel({
    required String period,
    required DateTime date,
  }) async {
    final uri = Uri.parse(
      "${ApiService.baseUrl}/reports/export/",
    ).replace(queryParameters: {"period": period, "date": _dateValue(date)});

    final response = await http
        .get(uri, headers: await ApiService.authHeaders())
        .timeout(const Duration(seconds: 60));

    if (response.statusCode != 200) {
      throw Exception(_message(response));
    }

    final filename = "ari-smart-ro-$period-${_dateValue(date)}.xlsx";

    if (Platform.isAndroid) {
      final savedPath = await _downloadsChannel.invokeMethod<String>('saveFile', {
        'filename': filename,
        'mimeType':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'bytes': response.bodyBytes,
      });
      if (savedPath == null || savedPath.isEmpty) {
        throw Exception('Report download location was not returned.');
      }
      return savedPath;
    }

    final directory = await getApplicationDocumentsDirectory();
    final file = File("${directory.path}/$filename");
    await file.writeAsBytes(response.bodyBytes, flush: true);
    return file.path;
  }

  static String _dateValue(DateTime value) {
    final month = value.month.toString().padLeft(2, "0");
    final day = value.day.toString().padLeft(2, "0");
    return "${value.year}-$month-$day";
  }

  static String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data["message"] ?? "Unable to load reports.").toString();
    } catch (_) {
      return "Unable to load reports (HTTP ${response.statusCode}).";
    }
  }
}
