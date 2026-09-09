import 'package:flutter/material.dart';

import 'public_request_screen.dart';

class GuestReferralPlanScreen extends StatelessWidget {
  const GuestReferralPlanScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Referral & Rewards Plan')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF5B21B6), Color(0xFF0B6FD3)],
            ),
            borderRadius: BorderRadius.circular(24),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.card_giftcard_rounded, color: Colors.white, size: 42),
              SizedBox(height: 14),
              Text(
                'Invite, earn and save',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 25,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'The full ARI referral plan is public. Login is needed later only to securely hold and redeem your personal rewards.',
                style: TextStyle(color: Colors.white70, height: 1.45),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        const _Rule(
          icon: Icons.person_add_alt_1,
          title: 'App referral',
          text:
              'When a friend applies your code, you receive 100 points worth ₹10, subject to security checks.',
        ),
        const _Rule(
          icon: Icons.water_drop_outlined,
          title: 'Successful installation benefit',
          text:
              'Eligible rental referrals can unlock ₹50 monthly rent benefit for up to 12 months after successful installation.',
        ),
        const _Rule(
          icon: Icons.account_balance_wallet_outlined,
          title: 'Wallet usage',
          text:
              'Rewards can be used for eligible purchase, parts and service bills. Up to 30% of an eligible cash bill may be paid from the wallet.',
        ),
        const _Rule(
          icon: Icons.verified_user_outlined,
          title: 'Transparent verification',
          text:
              'Duplicate, self or suspicious referrals are reviewed. Final eligibility is confirmed in the customer account.',
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => const PublicRequestScreen(
                requestType: 'REFERRAL',
                title: 'Referral enquiry',
                planName: 'ARI Referral & Rewards',
              ),
            ),
          ),
          icon: const Icon(Icons.support_agent_rounded),
          label: const Text('ASK ABOUT REFERRAL — NO LOGIN'),
        ),
      ],
    ),
  );
}

class _Rule extends StatelessWidget {
  const _Rule({required this.icon, required this.title, required this.text});
  final IconData icon;
  final String title;
  final String text;
  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: const Color(0xFFEAF3FF),
            child: Icon(icon, color: const Color(0xFF0B6FD3)),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 5),
                Text(text, style: const TextStyle(height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
