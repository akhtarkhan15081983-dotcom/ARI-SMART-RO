import 'package:flutter/material.dart';

import '../../services/digital_ro_service.dart';
import '../../services/job_service.dart';

class MyROScreen extends StatefulWidget {
  const MyROScreen({super.key});

  @override
  State<MyROScreen> createState() => _MyROScreenState();
}

class _MyROScreenState extends State<MyROScreen> {
  final _digitalRo = const DigitalRoService();
  final _jobService = JobService();

  late Future<Map<String, dynamic>> _passportFuture;
  late Future<Map<String, dynamic>> _profileFuture;
  late Future<Map<String, dynamic>> _otpFuture;
  late Future<Map<String, dynamic>> _engineerFuture;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _passportFuture = _digitalRo.getMyRoPassport();
    _profileFuture = _digitalRo.getCustomerProfile();
    _otpFuture = _jobService.getCustomerActiveOTP();
    _engineerFuture = _jobService.getCustomerAssignedEngineer();
  }

  Future<void> _refresh() async {
    setState(_reload);
    await Future.wait([_passportFuture, _profileFuture]);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('My RO • Digital Passport'),
          centerTitle: true,
          actions: [
            IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh_rounded)),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _refresh,
          child: FutureBuilder<List<Map<String, dynamic>>>(
            future: Future.wait([_profileFuture, _passportFuture]),
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const ListView(
                  physics: AlwaysScrollableScrollPhysics(),
                  children: [SizedBox(height: 260), Center(child: CircularProgressIndicator())],
                );
              }
              if (snapshot.hasError) {
                return ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(24),
                  children: [
                    const SizedBox(height: 100),
                    const Icon(Icons.error_outline_rounded, size: 64),
                    const SizedBox(height: 16),
                    const Text('Unable to load Digital RO Passport.', textAlign: TextAlign.center, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                    const SizedBox(height: 8),
                    Text(snapshot.error.toString().replaceFirst('Exception: ', ''), textAlign: TextAlign.center),
                  ],
                );
              }

              final profile = snapshot.data![0];
              final passport = snapshot.data![1];
              final ros = (passport['ros'] as List<dynamic>? ?? const [])
                  .map((e) => Map<String, dynamic>.from(e as Map))
                  .toList();
              return ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 36),
                children: [
                  _hero(profile, ros),
                  const SizedBox(height: 14),
                  _serviceSecurityCards(),
                  const SizedBox(height: 18),
                  if (ros.isEmpty)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Column(
                          children: [
                            Icon(Icons.water_drop_outlined, size: 48),
                            SizedBox(height: 10),
                            Text('No physical RO asset is assigned yet.', textAlign: TextAlign.center),
                          ],
                        ),
                      ),
                    )
                  else
                    ...ros.map(_roPassport),
                ],
              );
            },
          ),
        ),
      );

  Widget _hero(Map<String, dynamic> profile, List<Map<String, dynamic>> ros) {
    final name = (profile['name'] ?? 'Customer').toString();
    final card = (profile['card_number'] ?? '').toString();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0C3B5D), Color(0xFF0891B2)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        children: [
          const Icon(Icons.water_drop_rounded, size: 62, color: Colors.white),
          const SizedBox(height: 8),
          const Text('ARI DIGITAL RO PASSPORT', style: TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900, letterSpacing: .4)),
          const SizedBox(height: 6),
          Text(name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
          if (card.isNotEmpty) Text('Card $card', style: const TextStyle(color: Color(0xFFD5E6F0))),
          const SizedBox(height: 8),
          Text('${ros.length} physical RO ${ros.length == 1 ? 'unit' : 'units'} linked', style: const TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }

  Widget _serviceSecurityCards() => Column(
        children: [
          FutureBuilder<Map<String, dynamic>>(
            future: _engineerFuture,
            builder: (context, snapshot) {
              final data = snapshot.data;
              if (data == null || data['available'] != true) return const SizedBox.shrink();
              final engineer = Map<String, dynamic>.from(data['engineer'] as Map? ?? const {});
              final verified = engineer['identity_verified'] == true && engineer['active'] == true;
              return Card(
                child: ListTile(
                  leading: CircleAvatar(child: Icon(verified ? Icons.verified_user_rounded : Icons.engineering_outlined)),
                  title: Text((engineer['name'] ?? 'ARI Engineer').toString(), style: const TextStyle(fontWeight: FontWeight.w900)),
                  subtitle: Text('${engineer['employee_id'] ?? ''} • ${data['job_status'] ?? ''}'),
                  trailing: Icon(verified ? Icons.verified_rounded : Icons.warning_amber_rounded),
                ),
              );
            },
          ),
          FutureBuilder<Map<String, dynamic>>(
            future: _otpFuture,
            builder: (context, snapshot) {
              final data = snapshot.data;
              if (data == null || data['available'] != true) return const SizedBox.shrink();
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.password_rounded, size: 32),
                      const SizedBox(width: 12),
                      Expanded(child: Text('Service OTP • Job ${data['job_number'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800))),
                      Text((data['otp'] ?? '').toString(), style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: 4)),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      );

  Widget _roPassport(Map<String, dynamic> ro) {
    final components = (ro['components'] as List<dynamic>? ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final active = components.where((e) => e['status'] == 'ACTIVE').toList();
    final history = components.where((e) => e['status'] != 'ACTIVE').toList();
    final summary = Map<String, dynamic>.from(ro['component_summary'] as Map? ?? const {});

    return Card(
      margin: const EdgeInsets.only(bottom: 18),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const CircleAvatar(radius: 25, child: Icon(Icons.water_drop_outlined)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text((ro['ro_model_name'] ?? 'ARI RO').toString(), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                      Text('${ro['asset_id'] ?? ''} • Serial ${ro['serial_number'] ?? ''}'),
                      Text('${ro['deployment_type'] ?? ''} • ${ro['status'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 28),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _chip('Active ${summary['active_parts'] ?? summary['active_records'] ?? active.length}', Icons.settings_outlined),
                _chip('Scan pending ${summary['scan_pending'] ?? 0}', Icons.qr_code_scanner_rounded),
                _chip('Verified ${summary['scan_verified'] ?? 0}', Icons.verified_outlined),
                _chip('Non-scan ${summary['non_scan'] ?? 0}', Icons.format_list_numbered_rounded),
              ],
            ),
            const SizedBox(height: 18),
            const Text('CURRENT COMPONENTS', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, letterSpacing: .5)),
            const SizedBox(height: 8),
            if (active.isEmpty)
              const Text('Component passport is being prepared.')
            else
              ...active.map(_componentTile),
            if (history.isNotEmpty) ...[
              const SizedBox(height: 16),
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text('Replacement / removal history (${history.length})', style: const TextStyle(fontWeight: FontWeight.w900)),
                children: history.map(_componentTile).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _componentTile(Map<String, dynamic> part) {
    final serialized = part['is_serialized'] == true;
    final scan = (part['scan_status'] ?? '').toString();
    final warranty = (part['warranty_status'] ?? '').toString();
    final replacement = (part['replacement_status'] ?? '').toString();
    final serial = (part['serial_number'] ?? part['inventory_serial'] ?? '').toString();
    final quantity = part['quantity'] ?? 1;
    final warning = scan == 'PENDING' || replacement == 'OVERDUE';
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        child: Icon(serialized ? Icons.qr_code_2_rounded : Icons.tune_rounded),
      ),
      title: Text((part['part_name'] ?? 'RO Part').toString(), style: const TextStyle(fontWeight: FontWeight.w800)),
      subtitle: Text([
        (part['part_code'] ?? '').toString(),
        serialized ? (serial.isEmpty ? 'Serial pending' : 'Serial $serial') : 'Qty $quantity • no scan required',
        if (warranty == 'IN_WARRANTY') 'Warranty till ${part['warranty_end_date']}',
        if (warranty == 'EXPIRED') 'Warranty expired',
        if (replacement == 'DUE_SOON') 'Replacement due ${part['replacement_due_date']}',
        if (replacement == 'OVERDUE') 'Replacement overdue',
      ].where((e) => e.isNotEmpty).join('\n')),
      trailing: Icon(
        warning ? Icons.warning_amber_rounded : Icons.check_circle_outline_rounded,
        color: warning ? Colors.orange : Colors.green,
      ),
    );
  }

  Widget _chip(String label, IconData icon) => Chip(
        avatar: Icon(icon, size: 17),
        label: Text(label),
      );
}
