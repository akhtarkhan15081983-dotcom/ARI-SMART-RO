import 'package:flutter/material.dart';

const _ariNavy = Color(0xFF07315E);
const _ariBlue = Color(0xFF0868D7);

class AboutAriScreen extends StatelessWidget {
  const AboutAriScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFFF5F7FB),
    appBar: AppBar(title: const Text('About ARI SMART RO')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: const [
        _BrandHero(),
        SizedBox(height: 18),
        _InfoCard(
          icon: Icons.apartment_rounded,
          title: 'Who we are',
          text:
              'ARI SMART RO brings products, rental management, service support and customer history into one connected experience.',
        ),
        _InfoCard(
          icon: Icons.visibility_outlined,
          title: 'Our vision',
          text:
              'To make dependable water-purification products and service easier to discover, access and manage.',
        ),
        _InfoCard(
          icon: Icons.track_changes_rounded,
          title: 'Our mission',
          text:
              'Deliver transparent service workflows, accountable field operations and a simple digital experience for every customer.',
        ),
        _InfoCard(
          icon: Icons.workspace_premium_outlined,
          title: 'The ARI promise',
          text:
              'Clear product information, QR-verifiable parts, tracked service activity and a lasting digital service record.',
        ),
        SizedBox(height: 8),
      ],
    ),
  );
}

class _BrandHero extends StatelessWidget {
  const _BrandHero();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(24),
    decoration: BoxDecoration(
      gradient: const LinearGradient(colors: [_ariNavy, _ariBlue]),
      borderRadius: BorderRadius.circular(24),
    ),
    child: const Column(
      children: [
        CircleAvatar(
          radius: 34,
          backgroundColor: Colors.white,
          child: Icon(Icons.water_drop_rounded, color: _ariBlue, size: 38),
        ),
        SizedBox(height: 14),
        Text(
          'ARI SMART RO',
          style: TextStyle(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
          ),
        ),
        SizedBox(height: 6),
        Text(
          'Pure water. Smart living.',
          style: TextStyle(color: Colors.white70, fontSize: 15),
        ),
      ],
    ),
  );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.icon,
    required this.title,
    required this.text,
  });
  final IconData icon;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.only(bottom: 14),
    child: Padding(
      padding: const EdgeInsets.all(18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(11),
            decoration: BoxDecoration(
              color: const Color(0xFFE9F5FF),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: _ariBlue),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: _ariNavy,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  text,
                  style: const TextStyle(height: 1.45, color: Colors.black87),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
