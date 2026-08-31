import 'package:flutter/material.dart';

import '../login/login_screen.dart';

class GuestServicesScreen extends StatelessWidget {
  const GuestServicesScreen({super.key});

  void _login(BuildContext context) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LoginScreen()));

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFFF5F7FB),
    appBar: AppBar(title: const Text('ARI Services')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF07315E), Color(0xFF078AD8)]),
            borderRadius: BorderRadius.circular(22),
          ),
          child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.home_repair_service_rounded, color: Colors.white, size: 38),
            SizedBox(height: 14),
            Text('Water care made simple', style: TextStyle(color: Colors.white, fontSize: 23, fontWeight: FontWeight.w900)),
            SizedBox(height: 7),
            Text('Book, track and manage your RO service from one place.', style: TextStyle(color: Colors.white70, height: 1.4)),
          ]),
        ),
        const SizedBox(height: 18),
        _ServiceCard(icon: Icons.build_circle_outlined, title: 'RO Service & Repair', text: 'Request routine maintenance or help with a purifier issue.', onTap: () => _login(context)),
        _ServiceCard(icon: Icons.verified_outlined, title: 'AMC Plans', text: 'Manage planned maintenance and service coverage.', onTap: () => _login(context)),
        _ServiceCard(icon: Icons.currency_rupee_rounded, title: 'RO on Rent', text: 'Explore and manage rental water-purifier service.', onTap: () => _login(context)),
        _ServiceCard(icon: Icons.report_problem_outlined, title: 'Register a Complaint', text: 'Create and track a service complaint digitally.', onTap: () => _login(context)),
        const SizedBox(height: 10),
        FilledButton.icon(onPressed: () => _login(context), icon: const Icon(Icons.login), label: const Text('LOGIN TO BOOK SERVICE')),
      ],
    ),
  );
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard({required this.icon, required this.title, required this.text, required this.onTap});
  final IconData icon;
  final String title;
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: ListTile(
      contentPadding: const EdgeInsets.all(14),
      leading: CircleAvatar(backgroundColor: const Color(0xFFE9F5FF), child: Icon(icon, color: const Color(0xFF0868D7))),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
      subtitle: Padding(padding: const EdgeInsets.only(top: 5), child: Text(text)),
      trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
      onTap: onTap,
    ),
  );
}
