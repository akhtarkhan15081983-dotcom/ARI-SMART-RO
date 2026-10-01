import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../../services/admin_ro_passport_service.dart';

class AdminROPassportSetupScreen extends StatefulWidget {
  final Map<String, dynamic> customer;
  final Map<String, dynamic>? asset;

  const AdminROPassportSetupScreen({
    super.key,
    required this.customer,
    this.asset,
  });

  @override
  State<AdminROPassportSetupScreen> createState() =>
      _AdminROPassportSetupScreenState();
}

class _AdminROPassportSetupScreenState
    extends State<AdminROPassportSetupScreen> {
  final _service = const AdminROPassportService();
  final _picker = ImagePicker();
  final _serial = TextEditingController();
  final _tdsThreshold = TextEditingController();
  bool _loading = true;
  bool _saving = false;
  String? _error;
  List<Map<String, dynamic>> _models = const [];
  List<Map<String, dynamic>> _parts = const [];
  final Set<String> _selectedParts = {};
  final List<XFile> _photos = [];
  int? _modelId;
  String _ownership = 'RENTAL';
  DateTime? _date;
  DateTime? _nextFilterDate;
  bool _alarmMonitoring = true;

  bool get _allowed =>
      widget.asset == null || widget.asset?['manual_setup_allowed'] != false;

  int? _int(dynamic v) =>
      v is num ? v.toInt() : int.tryParse((v ?? '').toString());

  @override
  void initState() {
    super.initState();
    final asset = widget.asset;
    _modelId = _int(asset?['ro_model_id']);
    _serial.text = (asset?['serial_number'] ?? '').toString().trim();
    _ownership =
        (widget.customer['ownership_type'] ?? '').toString().toUpperCase() ==
                'PURCHASE'
            ? 'PURCHASE'
            : 'RENTAL';
    final rawDate =
        (asset?['purchase_date'] ?? widget.customer['installation_date'] ?? '')
            .toString();
    _date = DateTime.tryParse(rawDate);
    _nextFilterDate = DateTime.tryParse(
      (asset?['next_filter_change_date'] ?? '').toString(),
    );
    _tdsThreshold.text =
        (asset?['output_tds_attention_level'] ?? '').toString().trim();
    _alarmMonitoring = asset?['alarm_monitoring_enabled'] != false;
    for (final raw in (asset?['parts'] as List<dynamic>? ?? const [])) {
      if (raw is Map) {
        final key = (raw['part_key'] ?? '').toString();
        if (key.isNotEmpty) _selectedParts.add(key);
      }
    }
    _load();
  }

  @override
  void dispose() {
    _serial.dispose();
    _tdsThreshold.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await _service.fetchSetupOptions();
      if (!mounted) return;
      setState(() {
        _models = (data['models'] as List<dynamic>? ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
        _parts = (data['parts'] as List<dynamic>? ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
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

  Future<void> _pickDate() async {
    final result = await showDatePicker(
      context: context,
      initialDate: _date ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
    );
    if (result != null && mounted) setState(() => _date = result);
  }

  Future<void> _pickFilterDate() async {
    final result = await showDatePicker(
      context: context,
      initialDate: _nextFilterDate ?? DateTime.now().add(const Duration(days: 180)),
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 3650)),
    );
    if (result != null && mounted) {
      setState(() => _nextFilterDate = result);
    }
  }

  Future<void> _addPhoto() async {
    if (_photos.length >= 4) return;
    final file = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 82,
      maxWidth: 1800,
    );
    if (file != null && mounted) setState(() => _photos.add(file));
  }

  void _snack(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _save() async {
    if (_saving || !_allowed) return;
    final customerId = _int(widget.customer['customer_id']);
    if (customerId == null ||
        _modelId == null ||
        _serial.text.trim().isEmpty ||
        _selectedParts.isEmpty) {
      _snack('RO model, serial number and at least one current part are required.');
      return;
    }
    final tdsThreshold = _tdsThreshold.text.trim().isEmpty
        ? null
        : int.tryParse(_tdsThreshold.text.trim());
    if (_tdsThreshold.text.trim().isNotEmpty && tdsThreshold == null) {
      _snack('Enter a valid TDS attention level.');
      return;
    }
    setState(() => _saving = true);
    try {
      await _service.saveInitialBaseline(
        customerId: customerId,
        assetId: _int(widget.asset?['asset_id']),
        roModelId: _modelId!,
        serialNumber: _serial.text,
        ownershipType: _ownership,
        saleInstallationDate:
            _date == null ? null : DateFormat('yyyy-MM-dd').format(_date!),
        nextFilterChangeDate: _nextFilterDate == null
            ? null
            : DateFormat('yyyy-MM-dd').format(_nextFilterDate!),
        outputTdsAttentionLevel: tdsThreshold,
        alarmMonitoringEnabled: _alarmMonitoring,
        partKeys: _selectedParts.toList(),
        photoPaths: _photos.map((e) => e.path).toList(),
      );
      if (!mounted) return;
      _snack('Digital RO saved. Customer history and configured RO alarms will continue automatically.');
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) _snack(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Map<String, dynamic>? get _selectedModel {
    for (final model in _models) {
      if (_int(model['id']) == _modelId) return model;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final lockText = (widget.asset?['manual_setup_message'] ??
            'Automatic history has started, so this baseline is locked.')
        .toString();

    return Scaffold(
      appBar: AppBar(title: const Text('Digital RO Initial Setup')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const CircleAvatar(child: Icon(Icons.person)),
                      title: Text(
                        (widget.customer['name'] ?? 'Customer').toString(),
                        style: const TextStyle(fontWeight: FontWeight.w900),
                      ),
                      subtitle: Text(
                        '${widget.customer['customer_number'] ?? ''} • '
                        '${widget.customer['phone'] ?? ''}',
                      ),
                    ),
                    if (!_allowed)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Row(
                            children: [
                              const Icon(Icons.lock_outline),
                              const SizedBox(width: 10),
                              Expanded(child: Text(lockText)),
                            ],
                          ),
                        ),
                      ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      value: _modelId,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'RO Model',
                        border: OutlineInputBorder(),
                      ),
                      items: _models
                          .map(
                            (m) => DropdownMenuItem<int>(
                              value: _int(m['id']),
                              child: Text(
                                '${m['model_name']} • ${m['capacity'] ?? ''}',
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                      onChanged:
                          _allowed ? (v) => setState(() => _modelId = v) : null,
                    ),
                    if ((_selectedModel?['image_url'] ?? '').toString().isNotEmpty) ...[
                      const SizedBox(height: 10),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: SizedBox(
                          height: 170,
                          width: double.infinity,
                          child: Image.network(
                            (_selectedModel?['image_url'] ?? '').toString(),
                            fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) => const ColoredBox(
                              color: Color(0xFFE2E8F0),
                              child: Center(
                                child: Icon(Icons.broken_image_outlined),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 12),
                    TextField(
                      controller: _serial,
                      enabled: _allowed,
                      decoration: const InputDecoration(
                        labelText: 'RO Serial Number',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _ownership,
                      decoration: const InputDecoration(
                        labelText: 'RO Type',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'PURCHASE',
                          child: Text('Sale / Purchased RO'),
                        ),
                        DropdownMenuItem(
                          value: 'RENTAL',
                          child: Text('Rental RO'),
                        ),
                      ],
                      onChanged: _allowed
                          ? (v) => setState(() => _ownership = v ?? 'RENTAL')
                          : null,
                    ),
                    const SizedBox(height: 12),
                    OutlinedButton.icon(
                      onPressed: _allowed ? _pickDate : null,
                      icon: const Icon(Icons.calendar_month),
                      label: Text(
                        _date == null
                            ? 'Set sale / installation date'
                            : 'Sale / installation: ${DateFormat('dd MMM yyyy').format(_date!)}',
                      ),
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'Automatic RO monitoring',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                    ),
                    const SizedBox(height: 6),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Alarm monitoring enabled'),
                      subtitle: const Text(
                        'Use this Digital RO record to generate due-filter and TDS attention alerts.',
                      ),
                      value: _alarmMonitoring,
                      onChanged: _allowed
                          ? (value) => setState(() => _alarmMonitoring = value)
                          : null,
                    ),
                    OutlinedButton.icon(
                      onPressed: _allowed ? _pickFilterDate : null,
                      icon: const Icon(Icons.filter_alt_outlined),
                      label: Text(
                        _nextFilterDate == null
                            ? 'Set next filter-change date'
                            : 'Next filter change: ${DateFormat('dd MMM yyyy').format(_nextFilterDate!)}',
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _tdsThreshold,
                      enabled: _allowed,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Output TDS attention level (optional)',
                        helperText:
                            'Maintenance alert threshold only; not a water-safety declaration.',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'Current fitted parts',
                      style:
                          TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
                    ),
                    const Text(
                      'Select what is physically fitted now. Unknown old replacement dates are not invented.',
                    ),
                    Card(
                      child: Column(
                        children: _parts
                            .map(
                              (p) => CheckboxListTile(
                                value: _selectedParts
                                    .contains((p['part_key'] ?? '').toString()),
                                title: Text((p['part_name'] ?? '').toString()),
                                onChanged: !_allowed
                                    ? null
                                    : (v) {
                                        final key =
                                            (p['part_key'] ?? '').toString();
                                        setState(() {
                                          if (v == true) {
                                            _selectedParts.add(key);
                                          } else {
                                            _selectedParts.remove(key);
                                          }
                                        });
                                      },
                              ),
                            )
                            .toList(),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'RO Photos',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        Text('${_photos.length}/4 new'),
                      ],
                    ),
                    const Text(
                      'Add up to 4 clear photos. Existing baseline photos remain if no new photo is added.',
                    ),
                    OutlinedButton.icon(
                      onPressed: _allowed && _photos.length < 4 ? _addPhoto : null,
                      icon: const Icon(Icons.add_a_photo_outlined),
                      label: const Text('ADD PHOTO'),
                    ),
                    ..._photos.asMap().entries.map(
                          (entry) => ListTile(
                            leading: const Icon(Icons.image_outlined),
                            title: Text(entry.value.name),
                            trailing: IconButton(
                              onPressed: () =>
                                  setState(() => _photos.removeAt(entry.key)),
                              icon: const Icon(Icons.close),
                            ),
                          ),
                        ),
                    const SizedBox(height: 12),
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(14),
                        child: Text(
                          'This is only the initial baseline. Once verified engineer/service/inventory history starts, the baseline locks and future changes are added automatically instead of overwriting history.',
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: _allowed && !_saving ? _save : null,
                      icon: const Icon(Icons.verified_outlined),
                      label:
                          Text(_saving ? 'SAVING...' : 'SAVE DIGITAL RO BASELINE'),
                    ),
                  ],
                ),
    );
  }
}
