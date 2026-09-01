import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class TenantBrand {
  const TenantBrand({
    required this.slug,
    required this.displayName,
    required this.tagline,
    required this.welcomeMessage,
    required this.logoUrl,
    required this.primaryColor,
    required this.secondaryColor,
    required this.supportPhone,
    required this.supportEmail,
    required this.showPublicShop,
    required this.enabledModules,
  });

  final String slug;
  final String displayName;
  final String tagline;
  final String welcomeMessage;
  final String logoUrl;
  final Color primaryColor;
  final Color secondaryColor;
  final String supportPhone;
  final String supportEmail;
  final bool showPublicShop;
  final Set<String> enabledModules;

  factory TenantBrand.fromJson(Map<String, dynamic> json) => TenantBrand(
    slug: json['slug']?.toString() ?? '',
    displayName: json['display_name']?.toString() ?? 'Business App',
    tagline: json['tagline']?.toString() ?? '',
    welcomeMessage: json['welcome_message']?.toString() ?? '',
    logoUrl: json['logo_url']?.toString() ?? '',
    primaryColor: _color(
      json['primary_color']?.toString(),
      const Color(0xFF075985),
    ),
    secondaryColor: _color(
      json['secondary_color']?.toString(),
      const Color(0xFF0891B2),
    ),
    supportPhone: json['support_phone']?.toString() ?? '',
    supportEmail: json['support_email']?.toString() ?? '',
    showPublicShop: json['show_public_shop'] == true,
    enabledModules: (json['enabled_modules'] as List<dynamic>? ?? const [])
        .map((value) => value.toString().toUpperCase())
        .toSet(),
  );

  static Color _color(String? value, Color fallback) {
    final hex = (value ?? '').replaceFirst('#', '');
    if (!RegExp(r'^[0-9A-Fa-f]{6}$').hasMatch(hex)) return fallback;
    return Color(int.parse('FF$hex', radix: 16));
  }
}

class TenantBrandService {
  const TenantBrandService();

  static const dedicatedTenantSlug = String.fromEnvironment(
    'TENANT_SLUG',
    defaultValue: '',
  );

  static bool get isDedicatedBuild => dedicatedTenantSlug.trim().isNotEmpty;

  Future<TenantBrand> fetch(String slug) async {
    final response = await http
        .get(Uri.parse('${ApiService.baseUrl}/saas/brand/${slug.trim()}/'))
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        throw Exception(
          data['message']?.toString() ?? 'Company workspace unavailable.',
        );
      } catch (error) {
        if (error is Exception) rethrow;
        throw Exception('Company workspace unavailable.');
      }
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return TenantBrand.fromJson(
      Map<String, dynamic>.from(data['brand'] as Map),
    );
  }

  Future<TenantBrand?> resolveDedicated() async {
    if (!isDedicatedBuild) return null;
    return fetch(dedicatedTenantSlug);
  }
}
