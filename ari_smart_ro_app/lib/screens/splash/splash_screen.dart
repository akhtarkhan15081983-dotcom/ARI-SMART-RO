import 'dart:async';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../../services/api_service.dart';
import '../../services/referral_link_service.dart';
import '../../services/tenant_brand_service.dart';
import '../dashboard/dashboard_screen.dart';
import '../login/customer_onboarding_screen.dart';
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
  late final AnimationController _animationController;
  late final Animation<double> _fade;
  late final Animation<double> _scale;

  Timer? _fallbackTimer;
  bool _videoReady = false;
  bool _navigated = false;
  TenantBrand? _tenantBrand;
  String? _tenantError;

  static const _navy = Color(0xFF061F38);
  static const _blue = Color(0xFF0B6FD3);
  static const _cyan = Color(0xFF32C7E8);
  static const _splashDuration = Duration(milliseconds: 2400);

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 850),
    );
    _fade = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeOutCubic,
    );
    _scale = Tween<double>(begin: .94, end: 1).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeOutBack,
      ),
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
        await _animationController.forward();
        await Future.delayed(const Duration(milliseconds: 1300));
        await _goToNext();
      } catch (error) {
        if (mounted) {
          setState(
            () => _tenantError =
                error.toString().replaceFirst('Exception: ', ''),
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
      setState(() => _videoReady = true);
      await _animationController.forward();
      final duration = _videoController.value.duration;
      if (duration > const Duration(seconds: 5)) {
        await _videoController.seekTo(const Duration(seconds: 5));
      }
      await _videoController.play();
    } catch (error) {
      debugPrint('SPLASH VIDEO ERROR: $error');
      if (mounted) await _animationController.forward();
    }
  }

  void _videoListener() {
    if (!_videoController.value.isInitialized) return;
    if (_videoController.value.position >= const Duration(seconds: 7)) {
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
    } catch (_) {}

    final hasSession = await ApiService.restoreSession();
    if (!mounted) return;
    final referralCode = ReferralLinkService.takePendingCode();

    Navigator.pushReplacement(
      context,
      PageRouteBuilder<void>(
        transitionDuration: const Duration(milliseconds: 420),
        pageBuilder: (_, animation, _) {
          if (hasSession) return const DashboardScreen();
          if (_tenantBrand case final brand?) {
            return TenantWelcomeScreen(brand: brand);
          }
          if (referralCode != null) {
            return CustomerOnboardingScreen(referralCode: referralCode);
          }
          return const ShopScreen(guestMode: true);
        },
        transitionsBuilder: (_, animation, _, child) => FadeTransition(
          opacity: CurvedAnimation(parent: animation, curve: Curves.easeOut),
          child: child,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _fallbackTimer?.cancel();
    _videoController.removeListener(_videoListener);
    _videoController.dispose();
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (TenantBrandService.isDedicatedBuild) return _buildTenantSplash();

    return Scaffold(
      backgroundColor: _navy,
      body: Stack(
        fit: StackFit.expand,
        children: [
          if (_videoReady)
            FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width: _videoController.value.size.width,
                height: _videoController.value.size.height,
                child: VideoPlayer(_videoController),
              ),
            )
          else
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [_navy, Color(0xFF0A4779), _blue],
                ),
              ),
            ),
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                stops: [0, .42, 1],
                colors: [
                  Color(0x66031527),
                  Color(0x33031527),
                  Color(0xF2051B31),
                ],
              ),
            ),
          ),
          Positioned(
            top: -90,
            right: -70,
            child: Container(
              width: 230,
              height: 230,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _cyan.withValues(alpha: .12),
              ),
            ),
          ),
          SafeArea(
            child: FadeTransition(
              opacity: _fade,
              child: ScaleTransition(
                scale: _scale,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 26),
                  child: Column(
                    children: [
                      const Spacer(),
                      Container(
                        width: 82,
                        height: 82,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Colors.white, Color(0xFFE6FAFF)],
                          ),
                          borderRadius: BorderRadius.circular(26),
                          boxShadow: const [
                            BoxShadow(
                              color: Color(0x4432C7E8),
                              blurRadius: 35,
                              offset: Offset(0, 12),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.water_drop_rounded,
                          size: 42,
                          color: _blue,
                        ),
                      ),
                      const SizedBox(height: 22),
                      const Text(
                        'ARI SMART RO',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 31,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 2.2,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Pure Water. Smarter Living.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xFFE5F8FF),
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          letterSpacing: .5,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Purifiers • Service • AMC • Smart Care',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Color(0xBFFFFFFF),
                          fontSize: 11.5,
                          letterSpacing: .5,
                        ),
                      ),
                      const SizedBox(height: 36),
                      SizedBox(
                        width: 150,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(50),
                          child: const LinearProgressIndicator(
                            minHeight: 3,
                            backgroundColor: Color(0x33FFFFFF),
                            color: _cyan,
                          ),
                        ),
                      ),
                      const SizedBox(height: 13),
                      const Text(
                        'Preparing your water experience',
                        style: TextStyle(
                          color: Color(0x99FFFFFF),
                          fontSize: 10.5,
                        ),
                      ),
                      const SizedBox(height: 44),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTenantSplash() {
    final brand = _tenantBrand;
    final primary = brand?.primaryColor ?? _navy;
    final secondary = brand?.secondaryColor ?? _blue;
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
                  : FadeTransition(
                      opacity: _fade,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 108,
                            height: 108,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(30),
                              boxShadow: const [
                                BoxShadow(
                                  color: Color(0x33000000),
                                  blurRadius: 26,
                                  offset: Offset(0, 12),
                                ),
                              ],
                            ),
                            child: brand == null || brand.logoUrl.isEmpty
                                ? Icon(
                                    Icons.business_rounded,
                                    size: 58,
                                    color: primary,
                                  )
                                : Image.network(brand.logoUrl, fit: BoxFit.contain),
                          ),
                          const SizedBox(height: 24),
                          Text(
                            brand?.displayName ?? 'Loading workspace',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          if (brand?.tagline.isNotEmpty == true) ...[
                            const SizedBox(height: 8),
                            Text(
                              brand!.tagline,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: Colors.white70),
                            ),
                          ],
                          const SizedBox(height: 28),
                          const CircularProgressIndicator(color: Colors.white),
                        ],
                      ),
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
