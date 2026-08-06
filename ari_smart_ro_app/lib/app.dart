import 'package:flutter/material.dart';

import 'core/app_theme.dart';
import 'screens/splash/splash_screen.dart';

class AriSmartROApp extends StatelessWidget {
  const AriSmartROApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'ARI SMART RO',
      theme: AppTheme.lightTheme,
      home: const SplashScreen(),
    );
  }
}