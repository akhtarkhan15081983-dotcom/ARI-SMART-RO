import 'package:flutter/material.dart';

import '../login/login_screen.dart';

enum GuestServiceType { service, amc, rental, complaint }

class GuestServiceDetailScreen extends StatelessWidget {
  const GuestServiceDetailScreen({super.key, required this.type});

  final GuestServiceType type;

  ({
    IconData icon,
    String title,
    String subtitle,
    List<String> included,
    String process,
  })
  get _content => switch (type) {
    GuestServiceType.service => (
      icon: Icons.build_circle_outlined,
      title: 'RO Service & Repair',
      subtitle:
          'Professional diagnosis, maintenance and repair with a complete digital work record.',
      included: [
        'Customer issue and purifier details recorded before assignment',
        'Engineer visit scheduling with job-status tracking',
        'Input/output TDS readings and parts-used record',
        'Completion confirmation and future service reminder',
      ],
      process:
          'Sign in → choose your RO → describe the issue → select a suitable visit → track completion.',
    ),
    GuestServiceType.amc => (
      icon: Icons.verified_outlined,
      title: 'AMC Care Plans',
      subtitle:
          'Preventive maintenance plans designed to protect performance and reduce unexpected downtime.',
      included: [
        'Planned service schedule visible in your account',
        'Maintenance reminders before the due date',
        'Transparent visit, TDS and replacement history',
        'Plan coverage and applicable charges shown before confirmation',
      ],
      process:
          'Sign in → verify your installed RO → review eligible plan → confirm coverage with the ARI team.',
    ),
    GuestServiceType.rental => (
      icon: Icons.currency_rupee_rounded,
      title: 'RO on Rent',
      subtitle:
          'A professionally managed purifier rental experience with installation, service and payment visibility.',
      included: [
        'Eligibility and installation-location verification',
        'Digital rental agreement for approved customers',
        'Monthly rent ledger and payment history',
        'Tracked maintenance, complaint and machine history',
      ],
      process:
          'Create account → submit requirement → office verification → agreement → scheduled installation.',
    ),
    GuestServiceType.complaint => (
      icon: Icons.report_problem_outlined,
      title: 'Complaint Support',
      subtitle:
          'Raise an issue once and follow its ownership, priority and resolution from your account.',
      included: [
        'Complaint number and status timeline',
        'Assigned engineer and scheduled visit',
        'Resolution notes and service evidence',
        'Permanent history linked with your customer profile',
      ],
      process:
          'Sign in → select RO → describe the problem → submit → track engineer and resolution.',
    ),
  };

  @override
  Widget build(BuildContext context) {
    final content = _content;
    return Scaffold(
      appBar: AppBar(title: Text(content.title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 32),
        children: [
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF07315E), Color(0xFF078AD8)],
              ),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(content.icon, color: Colors.white, size: 44),
                const SizedBox(height: 16),
                Text(
                  content.title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 25,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  content.subtitle,
                  style: const TextStyle(color: Colors.white70, height: 1.45),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          Text(
            'What is included',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                children: content.included
                    .map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 13),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(
                              Icons.check_circle_rounded,
                              color: Color(0xFF15803D),
                              size: 21,
                            ),
                            const SizedBox(width: 11),
                            Expanded(child: Text(item)),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ),
          const SizedBox(height: 18),
          Text('How it works', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.route_rounded, color: Color(0xFF075985)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      content.process,
                      style: const TextStyle(height: 1.5),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 22),
          FilledButton.icon(
            onPressed: () => Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (_) => const LoginScreen())),
            icon: const Icon(Icons.login_rounded),
            label: const Text('LOGIN TO CONTINUE'),
          ),
          const SizedBox(height: 10),
          const Text(
            'Plan availability and final commercial terms are confirmed transparently before booking.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Color(0xFF526D82),
              fontSize: 12,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

class GuestServicesScreen extends StatelessWidget {
  const GuestServicesScreen({super.key});

  void _login(BuildContext context) => Navigator.of(
    context,
  ).push(MaterialPageRoute(builder: (_) => const LoginScreen()));

  void _showService(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String description,
    required List<String> benefits,
  }) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 4, 22, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: const Color(0xFFEAF2F7),
                child: Icon(icon, color: const Color(0xFF075985), size: 28),
              ),
              const SizedBox(height: 16),
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(description),
              const SizedBox(height: 18),
              ...benefits.map(
                (benefit) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.check_circle_rounded,
                        color: Color(0xFF15803D),
                        size: 20,
                      ),
                      const SizedBox(width: 10),
                      Expanded(child: Text(benefit)),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () {
                    Navigator.pop(sheetContext);
                    _login(context);
                  },
                  icon: const Icon(Icons.login_rounded),
                  label: const Text('LOGIN TO BOOK / TRACK'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

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
            gradient: const LinearGradient(
              colors: [Color(0xFF07315E), Color(0xFF078AD8)],
            ),
            borderRadius: BorderRadius.circular(22),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.home_repair_service_rounded,
                color: Colors.white,
                size: 38,
              ),
              SizedBox(height: 14),
              Text(
                'Water care made simple',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 23,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 7),
              Text(
                'Book, track and manage your RO service from one place.',
                style: TextStyle(color: Colors.white70, height: 1.4),
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        _ServiceCard(
          icon: Icons.build_circle_outlined,
          title: 'RO Service & Repair',
          text: 'Request routine maintenance or help with a purifier issue.',
          onTap: () => _showService(
            context,
            icon: Icons.build_circle_outlined,
            title: 'RO Service & Repair',
            description:
                'Professional diagnosis and tracked service for purifier performance issues.',
            benefits: const [
              'Engineer assignment and scheduled visit',
              'Digital service history and parts record',
              'TDS readings and completion confirmation',
            ],
          ),
        ),
        _ServiceCard(
          icon: Icons.verified_outlined,
          title: 'AMC Plans',
          text: 'Manage planned maintenance and service coverage.',
          onTap: () => _showService(
            context,
            icon: Icons.verified_outlined,
            title: 'AMC Plans',
            description:
                'Planned preventive care designed to keep your purifier dependable.',
            benefits: const [
              'Scheduled maintenance reminders',
              'Transparent visit and replacement history',
              'Coverage details available inside your account',
            ],
          ),
        ),
        _ServiceCard(
          icon: Icons.currency_rupee_rounded,
          title: 'RO on Rent',
          text: 'Explore and manage rental water-purifier service.',
          onTap: () => _showService(
            context,
            icon: Icons.currency_rupee_rounded,
            title: 'RO on Rent',
            description:
                'Access clean drinking water with professionally managed rental service.',
            benefits: const [
              'Installation and service workflow tracking',
              'Clear rent and payment history',
              'Digital agreement for eligible rental customers',
            ],
          ),
        ),
        _ServiceCard(
          icon: Icons.report_problem_outlined,
          title: 'Register a Complaint',
          text: 'Create and track a service complaint digitally.',
          onTap: () => _showService(
            context,
            icon: Icons.report_problem_outlined,
            title: 'Register a Complaint',
            description:
                'Report an issue once and follow its complete resolution lifecycle.',
            benefits: const [
              'Priority and status visibility',
              'Assigned engineer information',
              'Resolution notes stored in your history',
            ],
          ),
        ),
        const SizedBox(height: 10),
        FilledButton.icon(
          onPressed: () => _login(context),
          icon: const Icon(Icons.login),
          label: const Text('LOGIN TO BOOK SERVICE'),
        ),
      ],
    ),
  );
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard({
    required this.icon,
    required this.title,
    required this.text,
    required this.onTap,
  });
  final IconData icon;
  final String title;
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 12),
    child: ListTile(
      contentPadding: const EdgeInsets.all(14),
      leading: CircleAvatar(
        backgroundColor: const Color(0xFFE9F5FF),
        child: Icon(icon, color: const Color(0xFF0868D7)),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 5),
        child: Text(text),
      ),
      trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
      onTap: onTap,
    ),
  );
}
