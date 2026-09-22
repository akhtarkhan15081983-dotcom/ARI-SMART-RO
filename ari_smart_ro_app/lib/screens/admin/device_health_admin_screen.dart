import 'package:flutter/material.dart';

import '../../services/device_health_service.dart';

class DeviceHealthAdminScreen extends StatefulWidget {
  const DeviceHealthAdminScreen({super.key});

  @override
  State<DeviceHealthAdminScreen> createState() =>
      _DeviceHealthAdminScreenState();
}

class _DeviceHealthAdminScreenState extends State<DeviceHealthAdminScreen> {
  final _service = const DeviceHealthService();
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _rows = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final rows = await _service.fetchAdminHealth();
      if (!mounted) return;
      setState(() => _rows = rows);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'HEALTHY':
        return Colors.green.shade700;
      case 'STALE':
        return Colors.orange.shade800;
      default:
        return Colors.red.shade700;
    }
  }

  String _ago(dynamic seconds) {
    if (seconds == null) return 'Never';
    final value = int.tryParse(seconds.toString()) ?? 0;
    if (value < 60) return '${value}s ago';
    if (value < 3600) return '${value ~/ 60}m ago';
    return '${value ~/ 3600}h ago';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Device Health Center'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline, size: 48),
                        const SizedBox(height: 12),
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        FilledButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _rows.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 12),
                    itemBuilder: (_, index) {
                      final row = _rows[index];
                      final health = row['health'] is Map
                          ? Map<String, dynamic>.from(row['health'] as Map)
                          : <String, dynamic>{};
                      final status = row['status']?.toString() ?? 'UNKNOWN';
                      final pendingJobs =
                          int.tryParse(health['pending_job_actions']?.toString() ?? '') ?? 0;
                      final pendingLocations =
                          int.tryParse(health['pending_location_points']?.toString() ?? '') ?? 0;
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  CircleAvatar(
                                    child: Text(
                                      (row['name']?.toString().trim().isNotEmpty == true
                                              ? row['name'].toString().trim()[0]
                                              : '?')
                                          .toUpperCase(),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          row['name']?.toString() ?? 'Employee',
                                          style: Theme.of(context)
                                              .textTheme
                                              .titleMedium
                                              ?.copyWith(fontWeight: FontWeight.w800),
                                        ),
                                        Text(
                                          '${row['employee_code'] ?? ''} • ${row['designation'] ?? ''}',
                                        ),
                                      ],
                                    ),
                                  ),
                                  Chip(
                                    label: Text(status.replaceAll('_', ' ')),
                                    labelStyle: TextStyle(
                                      color: _statusColor(status),
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 14),
                              Wrap(
                                spacing: 8,
                                runSpacing: 8,
                                children: [
                                  _Metric(
                                    icon: Icons.schedule,
                                    label: 'Heartbeat',
                                    value: _ago(row['age_seconds']),
                                  ),
                                  _Metric(
                                    icon: Icons.smartphone,
                                    label: 'Device',
                                    value:
                                        '${health['manufacturer'] ?? '-'} ${health['model'] ?? ''}'.trim(),
                                  ),
                                  _Metric(
                                    icon: Icons.android,
                                    label: 'Android',
                                    value:
                                        '${health['os_version'] ?? '-'} • SDK ${health['android_sdk'] ?? '-'}',
                                  ),
                                  _Metric(
                                    icon: Icons.apps,
                                    label: 'App',
                                    value:
                                        'v${health['app_version'] ?? '-'} (${health['app_build'] ?? '-'})',
                                  ),
                                  _Metric(
                                    icon: Icons.location_on_outlined,
                                    label: 'GPS',
                                    value:
                                        '${row['location_status'] ?? '-'} • ${health['location_permission'] ?? '-'}',
                                  ),
                                  _Metric(
                                    icon: Icons.sync,
                                    label: 'Pending Sync',
                                    value: '$pendingJobs jobs • $pendingLocations GPS',
                                  ),
                                  _Metric(
                                    icon: Icons.memory,
                                    label: 'Memory',
                                    value:
                                        '${health['memory_class_mb'] ?? '-'} MB class • ${health['total_memory_mb'] ?? '-'} MB total',
                                  ),
                                ],
                              ),
                              if (health['last_error']?.toString().isNotEmpty == true) ...[
                                const SizedBox(height: 12),
                                Text(
                                  'Last issue: ${health['last_error']}',
                                  style: TextStyle(color: Colors.red.shade700),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 230,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).dividerColor),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.labelSmall),
                const SizedBox(height: 2),
                Text(
                  value,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
