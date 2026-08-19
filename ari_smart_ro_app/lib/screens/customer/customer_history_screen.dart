import 'package:flutter/material.dart';

import '../complaint/complaint_list_screen.dart';
import '../rent/rent_payment_screen.dart';
import '../service/service_list_screen.dart';

class CustomerHistoryScreen extends StatelessWidget {
  const CustomerHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My History'),
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'View your ARI SMART RO activity',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Rent, service and complaint records are available from one place.',
          ),
          const SizedBox(height: 20),
          _HistoryTile(
            icon: Icons.payments_outlined,
            title: 'Rent & Payment History',
            subtitle: 'Current rent, dues and previous rent records',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const RentPaymentScreen(),
              ),
            ),
          ),
          const SizedBox(height: 12),
          _HistoryTile(
            icon: Icons.build_circle_outlined,
            title: 'Service History',
            subtitle: 'Review service requests and service activity',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const ServiceListScreen(),
              ),
            ),
          ),
          const SizedBox(height: 12),
          _HistoryTile(
            icon: Icons.report_problem_outlined,
            title: 'Complaint History',
            subtitle: 'Track complaints and their current status',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const ComplaintListScreen(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 10,
        ),
        leading: CircleAvatar(
          child: Icon(icon),
        ),
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text(subtitle),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
