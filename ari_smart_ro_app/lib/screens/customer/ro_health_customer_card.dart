import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../services/ro_health_service.dart';
import '../../services/ro_parts_passport_service.dart';
import '../complaint/complaint_assistant_screen.dart';

class ROHealthCustomerCard extends StatefulWidget {
  const ROHealthCustomerCard({super.key});

  @override
  State<ROHealthCustomerCard> createState() => _ROHealthCustomerCardState();
}

class _ROHealthCustomerCardState extends State<ROHealthCustomerCard> {
  final ROPartsPassportService _passportService = const ROPartsPassportService();
  final ROHealthService _healthService = const ROHealthService();
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final passport = await _passportService.customerPassport();
    final assets = passport['assets'] as List<dynamic>? ?? const [];
    final results = <Map<String, dynamic>>[];
    for (final raw in assets.whereType<Map>()) {
      final asset = Map<String, dynamic>.from(raw);
      final assetId = (asset['asset_number'] ?? '').toString().trim();
      if (assetId.isEmpty) continue;
      results.add(await _healthService.getHealth(assetId));
    }
    return results;
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() => _future = _load());
    await _future;
  }

  Future<void> _openCareAssistant() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const ComplaintAssistantScreen()),
    );
    if (created == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Complaint submitted to ARI Care.')),
      );
    }
  }

  String _label(dynamic raw) {
    final value = (raw ?? '').toString().trim();
    if (value.isEmpty) return 'ACTION REQUIRED';
    return value.replaceAll('_', ' ').toUpperCase();
  }

  String _date(dynamic raw) {
    final value = (raw ?? '').toString().trim();
    if (value.isEmpty) return 'Not available';
    try {
      return DateFormat('dd MMM yyyy').format(DateTime.parse(value).toLocal());
    } catch (_) {
      return value;
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'HEALTHY':
        return Colors.green;
      case 'SERVICE DUE SOON':
        return Colors.orange;
      case 'SERVICE OVERDUE':
        return Colors.red;
      case 'NOT CONFIGURED':
        return Colors.blueGrey;
      default:
        return Colors.deepOrange;
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'HEALTHY':
        return Icons.health_and_safety_outlined;
      case 'SERVICE DUE SOON':
        return Icons.schedule_outlined;
      case 'SERVICE OVERDUE':
        return Icons.warning_amber_rounded;
      case 'NOT CONFIGURED':
        return Icons.tune_outlined;
      default:
        return Icons.build_circle_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }
        if (snapshot.hasError) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Icon(Icons.cloud_off_outlined, size: 34),
                  const SizedBox(height: 8),
                  const Text(
                    'ARI RO Health could not be loaded.',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                ],
              ),
            ),
          );
        }

        final assets = snapshot.data ?? const <Map<String, dynamic>>[];
        if (assets.isEmpty) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'RO Health will appear after a linked RO asset and verified parts record are available.',
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _openCareAssistant,
                    icon: const Icon(Icons.support_agent),
                    label: const Text('Get Help from ARI Care'),
                  ),
                ],
              ),
            ),
          );
        }

        return Column(
          children: assets.map(_assetCard).toList(),
        );
      },
    );
  }

  Widget _assetCard(Map<String, dynamic> data) {
    final overall = _label(data['overall_status']);
    final color = _statusColor(overall);
    final parts = data['parts'] as List<dynamic>? ?? const [];
    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: color.withValues(alpha: .10),
            child: Row(
              children: [
                CircleAvatar(
                  backgroundColor: color.withValues(alpha: .16),
                  child: Icon(_statusIcon(overall), color: color),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'ARI RO HEALTH & SMART CARE',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900),
                      ),
                      Text(
                        overall,
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          color: color,
                        ),
                      ),
                      Text(
                        '${data['asset_id'] ?? ''} • ${data['ro_model'] ?? ''}',
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh RO Health',
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
          ),
          if (parts.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'No verified installed/replaced parts are available yet. Ask the engineer to update the Digital RO Passport during the next service.',
              ),
            )
          else
            ...parts.whereType<Map>().map((raw) {
              return _partTile(Map<String, dynamic>.from(raw));
            }),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
            child: SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _openCareAssistant,
                icon: const Icon(Icons.support_agent),
                label: const Text('Problem with this RO? Open ARI Care Assistant'),
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Text(
              'Service intervals are ARI-configured for the specific part/model. The app does not assume one universal replacement period for every RO.',
              style: TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _partTile(Map<String, dynamic> part) {
    final status = _label(part['health_status']);
    final color = _statusColor(status);
    final history = part['verified_replacement_history'] as List<dynamic>? ?? const [];
    final interval = part['expected_service_interval_days'];
    final remaining = part['days_remaining'];
    final overdue = part['days_overdue'];
    final due = part['next_due_date'];

    String countdown;
    if (status == 'NOT CONFIGURED') {
      countdown = 'Service interval not configured yet';
    } else if (overdue is num && overdue > 0) {
      countdown = '${overdue.toInt()} day${overdue == 1 ? '' : 's'} overdue';
    } else if (remaining is num) {
      countdown = '${remaining.toInt()} day${remaining == 1 ? '' : 's'} remaining';
    } else {
      countdown = 'Cycle verification required';
    }

    return ExpansionTile(
      leading: CircleAvatar(
        backgroundColor: color.withValues(alpha: .12),
        child: Icon(_statusIcon(status), color: color),
      ),
      title: Text(
        (part['part_name'] ?? 'RO part').toString(),
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
      subtitle: Text('$status • $countdown'),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
      children: [
        _fact('Installed / replaced', _date(part['installed_or_replaced_at'])),
        _fact('Last verified service', _date(part['last_verified_service_date'])),
        _fact(
          'Expected interval',
          interval == null ? 'Not configured' : '$interval days',
        ),
        _fact('Next due', due == null ? 'Not configured' : _date(due)),
        _fact('Current status', status),
        if (history.isNotEmpty) ...[
          const Divider(height: 24),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Verified replacement history',
              style: TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(height: 6),
          ...history.whereType<Map>().take(5).map((raw) {
            final item = Map<String, dynamic>.from(raw);
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  const Icon(Icons.history, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${_date(item['replaced_at'])} • Service ${item['service_id'] ?? ''}',
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ],
    );
  }

  Widget _fact(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 145,
            child: Text(
              label,
              style: const TextStyle(color: Colors.grey),
            ),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}
