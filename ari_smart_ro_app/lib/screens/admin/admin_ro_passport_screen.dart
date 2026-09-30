import 'package:flutter/material.dart';

import '../../services/admin_ro_passport_service.dart';

class AdminROPassportScreen extends StatefulWidget {
  const AdminROPassportScreen({super.key});

  @override
  State<AdminROPassportScreen> createState() => _AdminROPassportScreenState();
}

class _AdminROPassportScreenState extends State<AdminROPassportScreen> {
  final AdminROPassportService _service = const AdminROPassportService();
  final TextEditingController _search = TextEditingController();

  bool _loading = true;
  String? _error;
  Map<String, dynamic> _data = const {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.fetchRegistry(query: _search.text);
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  List<Map<String, dynamic>> get _customers =>
      (_data['customers'] as List<dynamic>? ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();

  String _text(dynamic value, [String fallback = 'Not recorded']) {
    final v = (value ?? '').toString().trim();
    return v.isEmpty ? fallback : v;
  }

  Widget _summaryCard() {
    final customers = (_data['customer_count'] as num?)?.toInt() ?? 0;
    final alarms = (_data['active_alarm_count'] as num?)?.toInt() ?? 0;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(child: _metric('Customers', '$customers', Icons.people_alt_outlined)),
            const SizedBox(width: 10),
            Expanded(child: _metric('Active alarms', '$alarms', Icons.notifications_active_outlined)),
          ],
        ),
      ),
    );
  }

  Widget _metric(String label, String value, IconData icon) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(icon),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
                  Text(label),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _customerCard(Map<String, dynamic> customer) {
    final assets = (customer['assets'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final alarmCount = (customer['active_alarm_count'] as num?)?.toInt() ?? 0;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ExpansionTile(
        leading: CircleAvatar(
          child: Text(_text(customer['name'], '?').substring(0, 1).toUpperCase()),
        ),
        title: Text(
          _text(customer['name']),
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        subtitle: Text(
          '${_text(customer['customer_number'])} • ${_text(customer['phone'])}\n'
          '${_text(customer['master_ro_model'])} • ${assets.length} RO',
        ),
        isThreeLine: true,
        trailing: alarmCount > 0
            ? Badge(
                label: Text('$alarmCount'),
                child: const Icon(Icons.notifications_active_outlined),
              )
            : const Icon(Icons.keyboard_arrow_down),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        children: [
          _info('Card', customer['card_number']),
          _info('Ownership', customer['ownership_type']),
          _info('Installation', customer['installation_date']),
          _info('Address', '${_text(customer['address'], '')} ${_text(customer['area'], '')} ${_text(customer['city'], '')}'.trim()),
          const SizedBox(height: 8),
          if (assets.isEmpty)
            const ListTile(
              leading: Icon(Icons.water_drop_outlined),
              title: Text('No active RO asset linked'),
            )
          else
            ...assets.map(_assetCard),
        ],
      ),
    );
  }

  Widget _assetCard(Map<String, dynamic> asset) {
    final parts = (asset['parts'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final history = (asset['replacement_history'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final alarms = (asset['active_alarms'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final photos = (asset['photos'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();

    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      child: ExpansionTile(
        leading: const Icon(Icons.water_drop_outlined),
        title: Text(
          '${_text(asset['asset_number'])} • ${_text(asset['ro_model'])}',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          'Serial: ${_text(asset['serial_number'])} • ${parts.length} current part(s)',
        ),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        children: [
          _info('RO status', asset['status']),
          _info('Last verified visual check', asset['last_visual_check']),
          if (alarms.isNotEmpty) ...[
            const SizedBox(height: 8),
            _heading('Active alarms', Icons.notifications_active_outlined),
            ...alarms.map(
              (alarm) => ListTile(
                dense: true,
                leading: const Icon(Icons.warning_amber_rounded),
                title: Text(_text(alarm['title'])),
                subtitle: Text(
                  '${_text(alarm['severity'])} • ${_text(alarm['status'])}'
                  '${_text(alarm['due_date'], '').isEmpty ? '' : ' • Due ${_text(alarm['due_date'])}'}',
                ),
              ),
            ),
          ],
          const SizedBox(height: 8),
          _heading('Current fitted parts', Icons.settings_outlined),
          if (parts.isEmpty)
            const ListTile(
              dense: true,
              title: Text('No verified part baseline yet.'),
            )
          else
            ...parts.map(
              (part) => ListTile(
                dense: true,
                leading: const Icon(Icons.verified_outlined),
                title: Text(_text(part['part_name'])),
                subtitle: Text(_text(part['date_label'])),
              ),
            ),
          if (history.isNotEmpty) ...[
            _heading('Replacement history', Icons.history),
            ...history.map(
              (part) => ListTile(
                dense: true,
                leading: const Icon(Icons.change_circle_outlined),
                title: Text(_text(part['part_name'])),
                subtitle: Text(
                  '${_text(part['date_label'])}${_text(part['engineer'], '').isEmpty ? '' : ' • ${_text(part['engineer'])}'}',
                ),
              ),
            ),
          ],
          if (photos.isNotEmpty) ...[
            _heading('Latest verified photos', Icons.photo_library_outlined),
            SizedBox(
              height: 120,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: photos.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, index) {
                  final photo = photos[index];
                  final url = _text(photo['url'], '');
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 150,
                      child: url.isEmpty
                          ? const ColoredBox(
                              color: Color(0xFFE2E8F0),
                              child: Icon(Icons.image_not_supported_outlined),
                            )
                          : Image.network(
                              url,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const ColoredBox(
                                color: Color(0xFFE2E8F0),
                                child: Icon(Icons.broken_image_outlined),
                              ),
                            ),
                    ),
                  );
                },
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _heading(String text, IconData icon) => Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 4),
        child: Row(
          children: [
            Icon(icon, size: 19),
            const SizedBox(width: 8),
            Text(text, style: const TextStyle(fontWeight: FontWeight.w900)),
          ],
        ),
      );

  Widget _info(String label, dynamic value) => ListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        title: Text(label, style: const TextStyle(fontSize: 12)),
        subtitle: Text(_text(value), style: const TextStyle(fontWeight: FontWeight.w700)),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Digital RO Registry')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(14),
          children: [
            TextField(
              controller: _search,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _load(),
              decoration: InputDecoration(
                hintText: 'Search customer, phone, card, RO model, serial...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  onPressed: _load,
                  icon: const Icon(Icons.arrow_forward),
                ),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    children: [
                      const Icon(Icons.error_outline, size: 42),
                      const SizedBox(height: 10),
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        onPressed: _load,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              )
            else ...[
              _summaryCard(),
              const SizedBox(height: 8),
              if (_customers.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(28),
                    child: Center(child: Text('No matching customer Digital RO record found.')),
                  ),
                )
              else
                ..._customers.map(_customerCard),
            ],
          ],
        ),
      ),
    );
  }
}
