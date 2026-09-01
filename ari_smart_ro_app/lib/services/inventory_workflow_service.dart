import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import 'api_service.dart';

class InventoryWorkflowService {
  static const _downloads = MethodChannel('com.arismartro.app/downloads');

  Future<List<Map<String, dynamic>>> requests() async =>
      _rows(await _get('/inventory/workflow/requests/'), 'requests');
  Future<List<Map<String, dynamic>>> receivingQueue() async =>
      _rows(await _get('/inventory/workflow/receiving/'), 'items');
  Future<Map<String, dynamic>> summary() async => Map<String, dynamic>.from(
    (await _get('/inventory/workflow/summary/'))['summary'] as Map? ?? const {},
  );
  Future<List<Map<String, dynamic>>> suppliers() async =>
      _rawList(await _getRaw('/suppliers/'));
  Future<List<Map<String, dynamic>>> parts() async =>
      _rawList(await _getRaw('/inventory/parts/'));

  Future<void> review(int requestId, String action, String remarks) => _post(
    '/inventory/workflow/requests/$requestId/review/',
    {'action': action, 'remarks': remarks},
    expected: const {200},
  );
  Future<void> receive(int purchaseItemId, String code) => _post(
    '/inventory/workflow/receive/',
    {'purchase_item_id': purchaseItemId, 'code': code},
    expected: const {200, 201},
  );
  Future<void> fulfil(int requestId, List<String> codes) => _post(
    '/inventory/workflow/requests/$requestId/fulfil/',
    {'codes': codes},
    expected: const {200},
  );
  Future<void> createSupplier(Map<String, dynamic> payload) =>
      _post('/suppliers/', payload, expected: const {201});
  Future<void> createPurchase(Map<String, dynamic> payload) =>
      _post('/purchases/', payload, expected: const {201});

  Future<Map<String, dynamic>> analyzeInvoice(
    String imagePath,
    String ocrText,
  ) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiService.baseUrl}/purchases/invoice-scan/analyze/'),
    );
    request.headers.addAll(await ApiService.authHeaders());
    request.fields['ocr_text'] = ocrText;
    request.files.add(
      await http.MultipartFile.fromPath('invoice_image', imagePath),
    );
    final response = await http.Response.fromStream(
      await request.send().timeout(const Duration(seconds: 45)),
    );
    if (response.statusCode != 200) throw Exception(_message(response));
    final data = Map<String, dynamic>.from(jsonDecode(response.body) as Map);
    return Map<String, dynamic>.from(data['draft'] as Map);
  }

  Future<void> confirmScannedInvoice({
    required String imagePath,
    required String ocrText,
    required Map<String, dynamic> payload,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('${ApiService.baseUrl}/purchases/invoice-scan/confirm/'),
    );
    request.headers.addAll(await ApiService.authHeaders());
    request.fields['ocr_text'] = ocrText;
    request.fields['payload'] = jsonEncode(payload);
    request.files.add(
      await http.MultipartFile.fromPath('invoice_image', imagePath),
    );
    final response = await http.Response.fromStream(
      await request.send().timeout(const Duration(seconds: 60)),
    );
    if (response.statusCode != 201) throw Exception(_message(response));
  }

  Future<int> generateCodes(int purchaseItemId) async {
    final data = await _postData(
      '/inventory/workflow/generate-codes/',
      {'purchase_item_id': purchaseItemId},
      expected: const {200},
    );
    return (data['generated'] as num?)?.toInt() ?? 0;
  }

  Future<String> downloadQrLabels({int? purchaseItemId}) {
    final query = purchaseItemId == null
        ? ''
        : '?purchase_item_id=$purchaseItemId';
    return _download(
      '/inventory/workflow/qr-labels.pdf$query',
      'ARI_Inventory_QR_Labels.pdf',
      'application/pdf',
    );
  }

  Future<String> downloadInventoryReport() => _download(
    '/inventory/workflow/reports/inventory.xlsx',
    'ARI_Professional_Inventory_Report.xlsx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  );

  Future<dynamic> _getRaw(String path) async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 25));
    if (response.statusCode != 200) throw Exception(_message(response));
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> _get(String path) async =>
      Map<String, dynamic>.from(await _getRaw(path) as Map);

  Future<void> _post(
    String path,
    Map<String, dynamic> payload, {
    required Set<int> expected,
  }) async {
    await _postData(path, payload, expected: expected);
  }

  Future<Map<String, dynamic>> _postData(
    String path,
    Map<String, dynamic> payload, {
    required Set<int> expected,
  }) async {
    final response = await http
        .post(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 30));
    if (!expected.contains(response.statusCode)) {
      throw Exception(_message(response));
    }
    if (response.body.isEmpty) return const {};
    return Map<String, dynamic>.from(jsonDecode(response.body) as Map);
  }

  Future<String> _download(
    String path,
    String filename,
    String mimeType,
  ) async {
    final response = await http
        .get(
          Uri.parse('${ApiService.baseUrl}$path'),
          headers: await ApiService.authHeaders(),
        )
        .timeout(const Duration(seconds: 60));
    if (response.statusCode != 200) throw Exception(_message(response));
    if (Platform.isAndroid) {
      final saved = await _downloads.invokeMethod<String>('saveFile', {
        'filename': filename,
        'mimeType': mimeType,
        'bytes': response.bodyBytes,
      });
      if (saved == null || saved.isEmpty) {
        throw Exception('Download location not returned.');
      }
      return saved;
    }
    final directory = await getApplicationDocumentsDirectory();
    final file = File('${directory.path}/$filename');
    await file.writeAsBytes(response.bodyBytes, flush: true);
    return file.path;
  }

  List<Map<String, dynamic>> _rawList(dynamic data) {
    final rows = data is List
        ? data
        : (data is Map ? data['results'] ?? const [] : const []);
    return (rows as List)
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
  }

  List<Map<String, dynamic>> _rows(Map<String, dynamic> data, String key) =>
      (data[key] as List<dynamic>? ?? const [])
          .map((row) => Map<String, dynamic>.from(row as Map))
          .toList();

  String _message(http.Response response) {
    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['message'] ??
              data['detail'] ??
              data['error'] ??
              'Inventory request failed.')
          .toString();
    } catch (_) {
      return 'Inventory request failed (HTTP ${response.statusCode}).';
    }
  }
}
