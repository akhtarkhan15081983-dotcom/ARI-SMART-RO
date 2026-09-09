import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/shop_product_model.dart';
import 'api_service.dart';

class ShopService {
  const ShopService({
    this.client,
    this.initialTimeout = const Duration(seconds: 20),
    this.retryTimeout = const Duration(seconds: 70),
    this.retryDelay = const Duration(seconds: 2),
  });

  final http.Client? client;
  final Duration initialTimeout;
  final Duration retryTimeout;
  final Duration retryDelay;

  static const _retryableStatusCodes = <int>{408, 425, 429, 500, 502, 503, 504};

  Future<List<ShopProduct>> fetchCatalog({String query = ''}) async {
    final httpClient = client ?? http.Client();
    final uri = Uri.parse('${ApiService.baseUrl}/products/shop/catalog/')
        .replace(
          queryParameters: query.trim().isEmpty ? null : {'q': query.trim()},
        );
    final headers = await ApiService.authHeaders();

    try {
      for (var attempt = 0; attempt < 2; attempt++) {
        try {
          final response = await httpClient
              .get(uri, headers: headers)
              .timeout(attempt == 0 ? initialTimeout : retryTimeout);

          if (response.statusCode == 200) {
            final decoded = jsonDecode(response.body) as Map<String, dynamic>;
            final products = decoded['products'] as List<dynamic>? ?? const [];
            return products
                .map(
                  (item) => ShopProduct.fromJson(item as Map<String, dynamic>),
                )
                .toList();
          }

          if (!_retryableStatusCodes.contains(response.statusCode) ||
              attempt == 1) {
            throw Exception(
              'Unable to load shop catalog (HTTP ${response.statusCode})',
            );
          }
        } on TimeoutException {
          if (attempt == 1) rethrow;
        } on http.ClientException {
          if (attempt == 1) rethrow;
        }

        await Future<void>.delayed(retryDelay);
      }

      throw Exception('Unable to load shop catalog');
    } finally {
      if (client == null) httpClient.close();
    }
  }
}
