import 'package:flutter/material.dart';

import '../../core/app_colors.dart';
import '../login/customer_onboarding_screen.dart';
import '../login/login_screen.dart';

class GuestAccountScreen extends StatelessWidget {
  const GuestAccountScreen({super.key});

  void _open(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Your ARI Account')),
    body: ListView(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 32),
      children: [
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.primaryDark, AppColors.secondary],
            ),
            borderRadius: BorderRadius.circular(24),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.account_circle_rounded, color: Colors.white, size: 48),
              SizedBox(height: 16),
              Text(
                'Everything about your RO, in one secure place',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  height: 1.2,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 9),
              Text(
                'Track service, rent, payments, referrals and your complete digital service history.',
                style: TextStyle(color: Colors.white70, height: 1.45),
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        Text('Account benefits', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 12),
        const _Benefit(
          icon: Icons.water_drop_outlined,
          title: 'My RO & service history',
          text:
              'See purifier details, service records and upcoming maintenance.',
        ),
        const _Benefit(
          icon: Icons.receipt_long_outlined,
          title: 'Payments & rent',
          text: 'Review transparent payment history and current rental status.',
        ),
        const _Benefit(
          icon: Icons.support_agent_rounded,
          title: 'Priority support',
          text:
              'Raise and track service requests without repeated phone calls.',
        ),
        const _Benefit(
          icon: Icons.card_giftcard_rounded,
          title: 'Referral rewards',
          text: 'Share your referral and monitor eligible rewards securely.',
        ),
        const SizedBox(height: 18),
        FilledButton.icon(
          onPressed: () => _open(context, const LoginScreen()),
          icon: const Icon(Icons.lock_open_rounded),
          label: const Text('SIGN IN SECURELY'),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () => _open(context, const CustomerOnboardingScreen()),
          icon: const Icon(Icons.person_add_alt_1_rounded),
          label: const Text('CREATE / ACTIVATE ACCOUNT'),
        ),
        const SizedBox(height: 14),
        const Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.shield_outlined, size: 17, color: AppColors.success),
            SizedBox(width: 7),
            Flexible(
              child: Text(
                'Secure login • Verified phone • Role-protected access',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

class _Benefit extends StatelessWidget {
  const _Benefit({required this.icon, required this.title, required this.text});

  final IconData icon;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 10),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(
              color: AppColors.surfaceMuted,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: AppColors.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 5),
                Text(text),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
