import 'dart:async';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../../services/api_service.dart';
import '../../services/referral_link_service.dart';
import '../../services/tenant_brand_service.dart';
import '../login/customer_onboarding_screen.dart';
import '../dashboard/dashboard_screen.dart';
import '../shop/shop_screen.dart';
import '../tenancy/tenant_welcome_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final VideoPlayerController _videoController;
  late final AnimationController _fadeController;
  late final Animation<double> _fadeAnimation;

  Timer? _fallbackTimer;
  bool _videoReady = false;
  bool _navigated = false;
  TenantBrand? _tenantBrand;
  String? _tenantError;

  static const Duration _splashDuration = Duration(milliseconds: 2500);

  @override
  void initState() {
    super.initState();

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );

    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeInOut,
    );

    _videoController = VideoPlayerController.asset(
      'assets/videos/ari_water_fill.mp4',
    );

    if (!TenantBrandService.isDedicatedBuild) {
      _fallbackTimer = Timer(_splashDuration, _goToNext);
    }
    _initializeSplash();
  }

  Future<void> _initializeSplash() async {
    if (TenantBrandService.isDedicatedBuild) {
      try {
        final brand = await const TenantBrandService().resolveDedicated();
        if (!mounted) return;
        setState(() => _tenantBrand = brand);
        await Future.delayed(const Duration(milliseconds: 1400));
        await _goToNext();
      } catch (error) {
        if (mounted) {
          setState(
            () =>
                _tenantError = error.toString().replaceFirst('Exception: ', ''),
          );
        }
      }
      return;
    }
    try {
      await _videoController.initialize();

      await _videoController.setLooping(false);
      await _videoController.setVolume(0);

      _videoController.addListener(_videoListener);

      if (!mounted) return;

      setState(() {
        _videoReady = true;
      });

      await _fadeController.forward();

      await _videoController.seekTo(const Duration(seconds: 5));

      await _videoController.play();
    } catch (e) {
      debugPrint('SPLASH VIDEO ERROR: $e');

      await Future.delayed(const Duration(milliseconds: 800));

      _goToNext();
    }
  }

  void _videoListener() {
    if (!_videoController.value.isInitialized) return;

    final position = _videoController.value.position;

    if (position >= const Duration(seconds: 7)) {
      _goToNext();
    }
  }

  Future<void> _goToNext() async {
    if (_navigated || !mounted) return;

    _navigated = true;
    _fallbackTimer?.cancel();

    try {
      if (_videoController.value.isPlaying) {
        await _videoController.pause();
      }

      await _fadeController.reverse();
    } catch (e) {
      debugPrint('SPLASH EXIT ERROR: $e');
    }

    if (!mounted) return;

    final hasSession = await ApiService.restoreSession();
    if (!mounted) return;
    final referralCode = ReferralLinkService.takePendingCode();

    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) {
          if (hasSession) return const DashboardScreen();
          if (_tenantBrand case final brand?) {
            return TenantWelcomeScreen(brand: brand);
          }
          if (referralCode != null) {
            return CustomerOnboardingScreen(referralCode: referralCode);
          }
          return const ShopScreen(guestMode: true);
        },
      ),
    );
  }

  @override
  void dispose() {
    _fallbackTimer?.cancel();
    _videoController.removeListener(_videoListener);
    _videoController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (TenantBrandService.isDedicatedBuild) {
      final brand = _tenantBrand;
      final primary = brand?.primaryColor ?? const Color(0xFF102A43);
      final secondary = brand?.secondaryColor ?? const Color(0xFF075985);
      return Scaffold(
        body: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [primary, secondary],
            ),
          ),
          child: SafeArea(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: _tenantError != null
                    ? Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.cloud_off_rounded,
                            color: Colors.white,
                            size: 58,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            _tenantError!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white),
                          ),
                          const SizedBox(height: 18),
                          FilledButton(
                            onPressed: () {
                              setState(() => _tenantError = null);
                              _initializeSplash();
                            },
                            child: const Text('TRY AGAIN'),
                          ),
                        ],
                      )
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 108,
                            height: 108,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(28),
                            ),
                            child: brand == null || brand.logoUrl.isEmpty
                                ? Icon(
                                    Icons.business_rounded,
                                    size: 58,
                                    color: primary,
                                  )
                                : Image.network(
                                    brand.logoUrl,
                                    fit: BoxFit.contain,
                                  ),
                          ),
                          const SizedBox(height: 22),
                          Text(
                            brand?.displayName ?? 'Loading workspace',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 27,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          if (brand?.tagline.isNotEmpty == true) ...[
                            const SizedBox(height: 7),
                            Text(
                              brand!.tagline,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: Colors.white70),
                            ),
                          ],
                          const SizedBox(height: 26),
                          const CircularProgressIndicator(color: Colors.white),
                        ],
                      ),
              ),
            ),
          ),
        ),
      );
    }
    return Scaffold(
      backgroundColor: const Color(0xFF00132E),
      body: Stack(
        fit: StackFit.expand,
        children: [
          if (_videoReady)
            FadeTransition(
              opacity: _fadeAnimation,
              child: FittedBox(
                fit: BoxFit.cover,
                child: SizedBox(
                  width: _videoController.value.size.width,
                  height: _videoController.value.size.height,
                  child: VideoPlayer(_videoController),
                ),
              ),
            )
          else
            const Center(
              child: CircularProgressIndicator(color: Color(0xFF00A8FF)),
            ),

          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0x22000000),
                  Color(0x00000000),
                  Color(0xCC00132E),
                ],
              ),
            ),
          ),

          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
              child: Column(
                children: [
                  const Spacer(),

                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 12,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.30),
                      borderRadius: BorderRadius.circular(22),
                      border: Border.all(color: const Color(0x5500A8FF)),
                    ),
                    child: const Column(
                      children: [
                        Text(
                          'ARI',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 38,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 5,
                          ),
                        ),
                        SizedBox(height: 3),
                        Text(
                          'SMART RO',
                          style: TextStyle(
                            color: Color(0xFF4DDCFF),
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 4,
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 14),

                  const Text(
                    'PURE • SAFE • HEALTHY',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 2,
                    ),
                  ),

                  const SizedBox(height: 10),

                  const Text(
                    'Smart solution for every drop',
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),

                  const SizedBox(height: 30),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
