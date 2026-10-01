import 'package:flutter/material.dart';

import '../../services/admin_ro_passport_service.dart';
import 'admin_ro_passport_setup_screen.dart';

class AdminROPassportScreen extends StatefulWidget {
  const AdminROPassportScreen({
    super.key,
    this.embedded = false,
  });

  final bool embedded;

  @override
  State<AdminROPassportScreen> createState() => _AdminROPassportScreenState();
}

class _AdminROPassportScreenState extends State<AdminROPassportScreen> {
  final _service = const AdminROPassportService();
  final _search = TextEditingController();
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

  Future<void> _setup(
    Map<String, dynamic> customer, [
    Map<String, dynamic>? asset,
  ]) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => AdminROPassportSetupScreen(
          customer: customer,
          asset: asset,
        ),
      ),
    );
    if (changed == true) await _load();
  }

  String _text(dynamic value, [String fallback = 'Not recorded']) {
    final text = (value ?? '').toString().trim();
    return text.isEmpty ? fallback : text;
  }

  List<Map<String, dynamic>> get _customers =>
      (_data['customers'] as List<dynamic>? ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();

  @override
  Widget build(BuildContext context) {
    final alarms = (_data['active_alarm_count'] as num?)?.toInt() ?? 0;
    final content = RefreshIndicator(
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
                hintText: 'Search customer, phone, card, model, serial...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  onPressed: _load,
                  icon: const Icon(Icons.arrow_forward),
                ),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    Expanded(
                      child: _metric(
                        'Customers',
                        '${_data['customer_count'] ?? 0}',
                        Icons.people_alt_outlined,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _metric(
                        'Active alarms',
                        '$alarms',
                        Icons.notifications_active_outlined,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 10),
                      FilledButton.icon(
                        onPressed: _load,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              )
            else if (_customers.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(28),
                  child: Center(child: Text('No matching customer found.')),
                ),
              )
            else
              ..._customers.map(_customerCard),
          ],
        ),
      );

    if (widget.embedded) return content;
    return Scaffold(
      appBar: AppBar(title: const Text('Admin Digital RO Registry')),
      body: content,
    );
  }

  Widget _metric(String label, String value, IconData icon) => Row(
        children: [
          Icon(icon),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(label),
              ],
            ),
          ),
        ],
      );

  Widget _customerCard(Map<String, dynamic> customer) {
    final assets = (customer['assets'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final alarmCount =
        (customer['active_alarm_count'] as num?)?.toInt() ?? 0;
    return Card(
      margin: const EdgeInsets.only(top: 10),
      child: ExpansionTile(
        leading: const CircleAvatar(child: Icon(Icons.person_outline)),
        title: Text(
          _text(customer['name']),
          style: const TextStyle(fontWeight: FontWeight.w900),
        ),
        subtitle: Text(
          '${_text(customer['customer_number'])} • '
          '${_text(customer['phone'])}\n'
          '${_text(customer['card_number'])} • '
          '${_text(customer['city'])} • ${assets.length} RO',
        ),
        trailing: alarmCount > 0
            ? Badge(
                label: Text('$alarmCount'),
                child: const Icon(Icons.notifications_active_outlined),
              )
            : null,
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        children: [
          _info('Master RO model', customer['master_ro_model']),
          _info('Ownership', customer['ownership_type']),
          _info('Sale / installation', customer['installation_date']),
          _info(
            'Address',
            [
              customer['address'],
              customer['area'],
              customer['city'],
            ].where((e) => (e ?? '').toString().trim().isNotEmpty).join(', '),
          ),
          if (assets.isEmpty) ...[
            const ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.water_drop_outlined),
              title: Text('Digital RO baseline not created'),
              subtitle: Text(
                'Admin can fill model, current parts, sale date and photos now.',
              ),
            ),
            SizedBox(
              width: double.infinity,
              child: FilledButton.tonalIcon(
                onPressed: () => _setup(customer),
                icon: const Icon(Icons.add_circle_outline),
                label: const Text('CREATE DIGITAL RO BASELINE'),
              ),
            ),
          ] else
            ...assets.map((asset) => _assetCard(customer, asset)),
        ],
      ),
    );
  }

  Widget _assetCard(
    Map<String, dynamic> customer,
    Map<String, dynamic> asset,
  ) {
    final parts = (asset['parts'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final history = (asset['replacement_history'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final photos = (asset['photos'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final alarms = (asset['active_alarms'] as List<dynamic>? ?? const [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final editable = asset['manual_setup_allowed'] == true;

    return Card(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      child: ExpansionTile(
        leading: const Icon(Icons.water_drop_outlined),
        title: Text(
          '${_text(asset['asset_number'])} • ${_text(asset['ro_model'])}',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          'Serial: ${_text(asset['serial_number'])} • '
          '${parts.length} current part(s)',
        ),
        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        children: [
          if ((asset['ro_model_image_url'] ?? '').toString().isNotEmpty) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                width: double.infinity,
                height: 150,
                child: Image.network(
                  asset['ro_model_image_url'].toString(),
                  fit: BoxFit.contain,
                  errorBuilder: (_, __, ___) => const ColoredBox(
                    color: Color(0xFFE2E8F0),
                    child: Center(child: Icon(Icons.broken_image_outlined)),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
          ],
          _info('Sale date', asset['purchase_date']),
          _info('Next filter change', asset['next_filter_change_date']),
          _info(
            'TDS attention level',
            asset['output_tds_attention_level'],
          ),
          _info(
            'Alarm monitoring',
            asset['alarm_monitoring_enabled'] == false ? 'OFF' : 'ON',
          ),
          _info('Last verified check', asset['last_visual_check']),
          SizedBox(
            width: double.infinity,
            child: editable
                ? FilledButton.tonalIcon(
                    onPressed: () => _setup(customer, asset),
                    icon: const Icon(Icons.edit_note),
                    label: const Text('EDIT INITIAL BASELINE'),
                  )
                : Card(
                    margin: EdgeInsets.zero,
                    child: Padding(
                      padding: const EdgeInsets.all(10),
                      child: Row(
                        children: [
                          const Icon(Icons.lock_outline, size: 19),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _text(
                                asset['manual_setup_message'],
                                'Automatic history active; baseline locked.',
                              ),
                              style: const TextStyle(fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
          ),
          if (alarms.isNotEmpty) ...[
            _heading('Active alarms', Icons.warning_amber_rounded),
            ...alarms.map(
              (a) => ListTile(
                dense: true,
                title: Text(_text(a['title'])),
                subtitle: Text(
                  '${_text(a['severity'])} • ${_text(a['status'])}',
                ),
              ),
            ),
          ],
          _heading('Current fitted parts', Icons.settings_outlined),
          if (parts.isEmpty)
            const ListTile(
              dense: true,
              title: Text('No verified current parts yet.'),
            )
          else
            ...parts.map(
              (p) => ListTile(
                dense: true,
                leading: const Icon(Icons.verified_outlined),
                title: Text(_text(p['part_name'])),
                subtitle: Text(_text(p['date_label'])),
              ),
            ),
          if (history.isNotEmpty) ...[
            _heading('Replacement history', Icons.history),
            ...history.map(
              (p) => ListTile(
                dense: true,
                title: Text(_text(p['part_name'])),
                subtitle: Text(
                  '${_text(p['date_label'])}'
                  '${_text(p['engineer'], '').isEmpty ? '' : ' • ${_text(p['engineer'])}'}',
                ),
              ),
            ),
          ],
          if (photos.isNotEmpty) ...[
            _heading('Latest photos', Icons.photo_library_outlined),
            SizedBox(
              height: 110,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: photos.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, index) {
                  final url = _text(photos[index]['url'], '');
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: SizedBox(
                      width: 145,
                      child: url.isEmpty
                          ? const ColoredBox(
                              color: Color(0xFFE2E8F0),
                              child: Icon(Icons.image_not_supported),
                            )
                          : Image.network(
                              url,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) =>
                                  const ColoredBox(
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
        padding: const EdgeInsets.only(top: 10, bottom: 4),
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
        subtitle: Text(
          _text(value),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      );
}
