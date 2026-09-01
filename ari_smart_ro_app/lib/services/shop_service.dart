import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/shop_product_model.dart';
import 'api_service.dart';

class ShopService {
  const ShopService({this.client});

  final http.Client? client;

  Future<List<ShopProduct>> fetchCatalog({String query = ''}) async {
    final httpClient = client ?? http.Client();
    final uri = Uri.parse('${ApiService.baseUrl}/products/shop/catalog/')
        .replace(
          queryParameters: query.trim().isEmpty ? null : {'q': query.trim()},
        );
    final response = await httpClient
        .get(uri, headers: await ApiService.authHeaders())
        .timeout(const Duration(seconds: 15));

    if (response.statusCode != 200) {
      throw Exception('Unable to load shop catalog');
    }

    final decoded = jsonDecode(response.body) as Map<String, dynamic>;
    final products = decoded['products'] as List<dynamic>? ?? const [];
    return products
        .map((item) => ShopProduct.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
