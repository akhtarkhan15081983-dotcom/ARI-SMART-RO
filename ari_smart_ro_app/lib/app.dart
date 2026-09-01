import 'package:flutter/material.dart';

import 'core/app_theme.dart';
import 'screens/splash/splash_screen.dart';
import 'screens/login/customer_onboarding_screen.dart';
import 'services/referral_link_service.dart';

class AriSmartROApp extends StatefulWidget {
  const AriSmartROApp({super.key});

  @override
  State<AriSmartROApp> createState() => _AriSmartROAppState();
}

class _AriSmartROAppState extends State<AriSmartROApp> {
  final _navigatorKey = GlobalKey<NavigatorState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ReferralLinkService.initialize((code) async {
        await _navigatorKey.currentState?.push(
          MaterialPageRoute(
            builder: (_) => CustomerOnboardingScreen(referralCode: code),
          ),
        );
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      navigatorKey: _navigatorKey,
      debugShowCheckedModeBanner: false,
      title: 'ARI SMART RO',
      theme: AppTheme.lightTheme,
      themeMode: ThemeMode.light,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: MediaQuery.textScalerOf(
            context,
          ).clamp(minScaleFactor: 0.9, maxScaleFactor: 1.4),
        ),
        child: child ?? const SizedBox.shrink(),
      ),
      home: const SplashScreen(),
    );
  }
}
