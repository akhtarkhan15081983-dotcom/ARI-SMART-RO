import 'package:flutter/material.dart';

import '../../services/api_service.dart';
import '../../services/ro_alarm_service.dart';
import '../admin/admin_ro_passport_screen.dart';

class ROAlarmScreen extends StatefulWidget {
  const ROAlarmScreen({super.key});

  @override
  State<ROAlarmScreen> createState() => _ROAlarmScreenState();
}

class _ROAlarmScreenState extends State<ROAlarmScreen> {
  final ROAlarmService _service = const ROAlarmService();
  List<Map<String, dynamic>> _alarms = const [];
  List<Map<String, dynamic>> _assets = const [];
  String _role = 'CUSTOMER';
  String _statusFilter = '';
  bool _loading = true;
  bool _working = false;
  String? _error;

  bool get _isCustomer => _role == 'CUSTOMER';
  bool get _canManage =>
      const {'ADMIN', 'MANAGER', 'OFFICE', 'ENGINEER'}.contains(_role);
  bool get _canConfigure =>
      const {'ADMIN', 'MANAGER', 'OFFICE'}.contains(_role);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final role = (await ApiService.getRole() ?? 'CUSTOMER')
          .trim()
          .toUpperCase()
          .replaceAll('ROLE_', '');
      final results = await Future.wait([
        _service.fetchAlarms(status: _statusFilter),
        _service.fetchAssets(),
      ]);
      if (!mounted) return;
      setState(() {
        _role = role;
        _alarms = results[0];
        _assets = results[1];
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _clean(e);
        _loading = false;
      });
    }
  }

  Future<void> _refreshAutomatic() async {
    if (_working || _isCustomer) return;
    setState(() => _working = true);
    try {
      final result = await _service.refreshSystemAlarms();
      if (!mounted) return;
      final created = (result['created'] as num?)?.toInt() ?? 0;
      final resolved = (result['auto_resolved'] as num?)?.toInt() ?? 0;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$created new alarm(s), $resolved auto-resolved.')),
      );
      await _load();
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _changeStatus(int id, String action) async {
    if (_working) return;
    setState(() => _working = true);
    try {
      await _service.updateAlarmStatus(id, action);
      await _load();
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _report() async {
    if (_assets.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No assigned RO is available.')),
      );
      return;
    }

    int selectedAsset = (_assets.first['id'] as num).toInt();
    String alarmType = 'LEAKAGE';
    final note = TextEditingController();
    final tds = TextEditingController();

    final ok = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocalState) => AlertDialog(
          title: const Text('Report RO Alarm'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<int>(
                  initialValue: selectedAsset,
                  decoration: const InputDecoration(
                    labelText: 'RO',
                    border: OutlineInputBorder(),
                  ),
                  items: _assets
                      .map(
                        (row) => DropdownMenuItem<int>(
                          value: (row['id'] as num).toInt(),
                          child: Text('${row['asset_id']} • ${row['ro_model_name']}'),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) setLocalState(() => selectedAsset = value);
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: alarmType,
                  decoration: const InputDecoration(
                    labelText: 'Problem',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'LEAKAGE', child: Text('Leakage')),
                    DropdownMenuItem(value: 'NOISE', child: Text('Unusual noise')),
                    DropdownMenuItem(value: 'TASTE', child: Text('Taste change')),
                    DropdownMenuItem(value: 'TDS', child: Text('TDS attention')),
                    DropdownMenuItem(value: 'LOW_FLOW', child: Text('Low water flow')),
                    DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                  ],
                  onChanged: (value) => setLocalState(
                    () => alarmType = value ?? 'OTHER',
                  ),
                ),
                if (alarmType == 'TDS') ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: tds,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Observed TDS (optional)',
                      helperText: 'Maintenance reading only, not a water-safety verdict.',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                TextField(
                  controller: note,
                  minLines: 2,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'What did you notice?',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Report'),
            ),
          ],
        ),
      ),
    );

    if (ok != true) {
      note.dispose();
      tds.dispose();
      return;
    }

    final observed = tds.text.trim().isEmpty ? null : int.tryParse(tds.text.trim());
    if (alarmType == 'TDS' && tds.text.trim().isNotEmpty && observed == null) {
      note.dispose();
      tds.dispose();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid TDS reading.')),
      );
      return;
    }

    setState(() => _working = true);
    try {
      await _service.reportAlarm(
        assetId: selectedAsset,
        alarmType: alarmType,
        message: note.text.trim(),
        observedValue: observed,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('RO alarm reported.')),
        );
      }
      await _load();
    } catch (e) {
      _showError(e);
    } finally {
      note.dispose();
      tds.dispose();
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _configure() async {
    if (!_canConfigure || _assets.isEmpty) return;
    final asset = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: _assets
              .map(
                (row) => ListTile(
                  leading: const Icon(Icons.water_drop_outlined),
                  title: Text('${row['asset_id']}'),
                  subtitle: Text('${row['customer_name'] ?? ''} • ${row['ro_model_name'] ?? ''}'),
                  trailing: const Icon(Icons.tune),
                  onTap: () => Navigator.pop(context, row),
                ),
              )
              .toList(),
        ),
      ),
    );
    if (asset == null || !mounted) return;

    var enabled = asset['alarm_monitoring_enabled'] != false;
    DateTime? filterDate = DateTime.tryParse(
      (asset['next_filter_change_date'] ?? '').toString(),
    );
    final threshold = TextEditingController(
      text: asset['output_tds_attention_level']?.toString() ?? '',
    );

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setLocalState) => AlertDialog(
          title: Text('Alarm Settings • ${asset['asset_id']}'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Automatic monitoring'),
                  value: enabled,
                  onChanged: (value) => setLocalState(() => enabled = value),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Next filter change'),
                  subtitle: Text(filterDate == null ? 'Not configured' : _date(filterDate!)),
                  trailing: const Icon(Icons.calendar_month),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: dialogContext,
                      firstDate: DateTime.now().subtract(const Duration(days: 365)),
                      lastDate: DateTime.now().add(const Duration(days: 3650)),
                      initialDate: filterDate ?? DateTime.now(),
                    );
                    if (picked != null) setLocalState(() => filterDate = picked);
                  },
                ),
                TextField(
                  controller: threshold,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Output TDS attention level',
                    helperText: 'Maintenance threshold only; not a safe/unsafe declaration.',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );

    if (save != true) {
      threshold.dispose();
      return;
    }
    final thresholdValue = threshold.text.trim().isEmpty
        ? null
        : int.tryParse(threshold.text.trim());
    if (threshold.text.trim().isNotEmpty && thresholdValue == null) {
      threshold.dispose();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid TDS attention level.')),
      );
      return;
    }

    setState(() => _working = true);
    try {
      await _service.updateAssetSettings(
        assetId: (asset['id'] as num).toInt(),
        monitoringEnabled: enabled,
        nextFilterChangeDate: filterDate == null ? null : _isoDate(filterDate!),
        outputTdsAttentionLevel: thresholdValue,
      );
      await _service.refreshSystemAlarms();
      await _load();
    } catch (e) {
      _showError(e);
    } finally {
      threshold.dispose();
      if (mounted) setState(() => _working = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_role == 'ADMIN' && !_loading) {
      return DefaultTabController(
        length: 2,
        child: Scaffold(
          appBar: AppBar(
            title: const Text('RO Control Center'),
            bottom: const TabBar(
              tabs: [
                Tab(
                  icon: Icon(Icons.badge_outlined),
                  text: 'Digital RO',
                ),
                Tab(
                  icon: Icon(Icons.notifications_active_outlined),
                  text: 'Alarms',
                ),
              ],
            ),
          ),
          body: TabBarView(
            children: [
              const AdminROPassportScreen(embedded: true),
              _alarmBody(showOwnAppBar: false),
            ],
          ),
        ),
      );
    }
    return _alarmBody(showOwnAppBar: true);
  }

  Widget _alarmBody({required bool showOwnAppBar}) {
    return Scaffold(
      appBar: showOwnAppBar
          ? AppBar(
              title: const Text('RO Alarm Center'),
        actions: [
          if (_canConfigure)
            IconButton(
              tooltip: 'Alarm settings',
              onPressed: _working ? null : _configure,
              icon: const Icon(Icons.tune),
            ),
          if (!_isCustomer)
            IconButton(
              tooltip: 'Refresh automatic alarms',
              onPressed: _working ? null : _refreshAutomatic,
              icon: const Icon(Icons.sync),
            ),
          IconButton(
            tooltip: 'Reload',
            onPressed: _working ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
              ],
            )
          : null,
      floatingActionButton: _assets.isEmpty
          ? null
          : FloatingActionButton.extended(
              onPressed: _working ? null : _report,
              icon: const Icon(Icons.add_alert),
              label: const Text('Report'),
            ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  '${_alarms.where((a) => a['status'] != 'RESOLVED').length} active alarm(s) • ${_assets.length} RO(s)',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                _filter('', 'All'),
                _filter('OPEN', 'Open'),
                _filter('ACKNOWLEDGED', 'Acknowledged'),
                _filter('RESOLVED', 'Resolved'),
              ],
            ),
            if (_working) ...[
              const SizedBox(height: 10),
              const LinearProgressIndicator(),
            ],
            const SizedBox(height: 12),
            if (_loading)
              const Padding(
                padding: EdgeInsets.only(top: 50),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    children: [
                      Text(_error!, textAlign: TextAlign.center),
                      const SizedBox(height: 8),
                      OutlinedButton(onPressed: _load, child: const Text('Retry')),
                    ],
                  ),
                ),
              )
            else if (_alarms.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text('No RO alarms in this view.')),
                ),
              )
            else
              ..._alarms.map(_alarmCard),
          ],
        ),
      ),
    );
  }

  ChoiceChip _filter(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _statusFilter == value,
        onSelected: (_) {
          setState(() => _statusFilter = value);
          _load();
        },
      );

  Widget _alarmCard(Map<String, dynamic> row) {
    final status = (row['status'] ?? 'OPEN').toString();
    final id = (row['id'] as num?)?.toInt();
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.notifications_active_outlined),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    (row['title'] ?? 'RO Alarm').toString(),
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Chip(label: Text(status.replaceAll('_', ' '))),
              ],
            ),
            Text('${row['asset_id'] ?? ''} • ${row['ro_model_name'] ?? ''}'),
            if ((row['customer_name'] ?? '').toString().isNotEmpty)
              Text('Customer: ${row['customer_name']}'),
            if ((row['message'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(row['message'].toString()),
            ],
            if (row['observed_value'] != null)
              Text('Observed TDS: ${row['observed_value']}'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              children: [
                Chip(label: Text((row['alarm_type_label'] ?? row['alarm_type']).toString())),
                Chip(label: Text('Priority: ${row['severity'] ?? 'NORMAL'}')),
              ],
            ),
            if (_canManage && id != null && status != 'RESOLVED') ...[
              const Divider(),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (status == 'OPEN')
                    TextButton(
                      onPressed: _working ? null : () => _changeStatus(id, 'ACKNOWLEDGE'),
                      child: const Text('Acknowledge'),
                    ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _working ? null : () => _changeStatus(id, 'RESOLVE'),
                    child: const Text('Resolve'),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showError(Object e) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(_clean(e))),
    );
  }

  String _clean(Object e) => e.toString().replaceFirst('Exception: ', '').trim();

  static String _isoDate(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  static String _date(DateTime value) =>
      '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}';
}
