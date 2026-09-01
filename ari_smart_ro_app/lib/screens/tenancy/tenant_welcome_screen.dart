import 'package:flutter/material.dart';

import '../../services/tenant_brand_service.dart';
import '../login/login_screen.dart';
import '../shop/shop_screen.dart';

class TenantWelcomeScreen extends StatelessWidget {
  const TenantWelcomeScreen({super.key, required this.brand});

  final TenantBrand brand;

  void _open(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [brand.primaryColor, brand.secondaryColor],
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              Center(
                child: Container(
                  width: 112,
                  height: 112,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(28),
                    boxShadow: const [
                      BoxShadow(
                        color: Colors.black26,
                        blurRadius: 26,
                        offset: Offset(0, 12),
                      ),
                    ],
                  ),
                  child: brand.logoUrl.isEmpty
                      ? Icon(
                          Icons.water_drop_rounded,
                          size: 62,
                          color: brand.primaryColor,
                        )
                      : Image.network(
                          brand.logoUrl,
                          fit: BoxFit.contain,
                          errorBuilder: (_, _, _) => Icon(
                            Icons.business_rounded,
                            size: 58,
                            color: brand.primaryColor,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 28),
              Center(
                child: Text(
                  brand.displayName,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 30,
                    height: 1.15,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              if (brand.tagline.isNotEmpty) ...[
                const SizedBox(height: 9),
                Center(
                  child: Text(
                    brand.tagline,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white70, fontSize: 16),
                  ),
                ),
              ],
              const SizedBox(height: 30),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white24),
                ),
                child: Text(
                  brand.welcomeMessage.isEmpty
                      ? 'Sign in to securely manage your services and business operations.'
                      : brand.welcomeMessage,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, height: 1.5),
                ),
              ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: brand.primaryColor,
                  ),
                  onPressed: () => _open(context, const LoginScreen()),
                  icon: const Icon(Icons.login_rounded),
                  label: const Text('SIGN IN'),
                ),
              ),
              if (brand.showPublicShop) ...[
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white54),
                    ),
                    onPressed: () =>
                        _open(context, const ShopScreen(guestMode: true)),
                    icon: const Icon(Icons.storefront_rounded),
                    label: const Text('EXPLORE SHOP'),
                  ),
                ),
              ],
              const SizedBox(height: 15),
              Center(
                child: Text(
                  [
                    brand.supportPhone,
                    brand.supportEmail,
                  ].where((value) => value.isNotEmpty).join(' • '),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white60, fontSize: 11),
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}
