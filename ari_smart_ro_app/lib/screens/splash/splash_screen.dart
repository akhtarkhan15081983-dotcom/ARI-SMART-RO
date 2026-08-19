import 'package:flutter/material.dart';

import '../login/login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _introController;
  late final AnimationController _waterController;
  late final Animation<double> _scale;
  late final Animation<double> _fade;

  @override
  void initState() {
    super.initState();
    _introController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    _waterController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _scale = CurvedAnimation(parent: _introController, curve: Curves.easeOutBack);
    _fade = CurvedAnimation(parent: _introController, curve: Curves.easeIn);
    _introController.forward();
    _continueToLogin();
  }

  Future<void> _continueToLogin() async {
    await Future.delayed(const Duration(milliseconds: 2800));
    if (!mounted) return;
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const LoginScreen()),
    );
  }

  @override
  void dispose() {
    _introController.dispose();
    _waterController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const navy = Color(0xFF031B46);
    const electricBlue = Color(0xFF079BFF);

    return Scaffold(
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF021331), navy, Color(0xFF0059A8)],
          ),
        ),
        child: SafeArea(
          child: FadeTransition(
            opacity: _fade,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                ScaleTransition(
                  scale: _scale,
                  child: Container(
                    width: 190,
                    height: 190,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(42),
                      gradient: const LinearGradient(
                        colors: [Color(0xFF0A2D62), Color(0xFF001735)],
                      ),
                      border: Border.all(color: electricBlue, width: 2),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x88009BFF),
                          blurRadius: 35,
                          spreadRadius: 3,
                        ),
                      ],
                    ),
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        const Icon(
                          Icons.water_drop_rounded,
                          size: 116,
                          color: Colors.white,
                        ),
                        Positioned(
                          bottom: 31,
                          child: AnimatedBuilder(
                            animation: _waterController,
                            builder: (context, child) => Transform.translate(
                              offset: Offset(0, 5 * _waterController.value),
                              child: child,
                            ),
                            child: const Icon(
                              Icons.water_drop,
                              size: 28,
                              color: electricBlue,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                const Text(
                  'ARI',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 48,
                    height: 1,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 5,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'SMART RO',
                  style: TextStyle(
                    color: Color(0xFF35C7FF),
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 4,
                  ),
                ),
                const SizedBox(height: 18),
                const Text(
                  'PURE • SAFE • HEALTHY',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 44),
                SizedBox(
                  width: 170,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: const LinearProgressIndicator(
                      minHeight: 4,
                      backgroundColor: Color(0x33FFFFFF),
                      color: electricBlue,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                const Text(
                  'Smart solution for every drop',
                  style: TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
