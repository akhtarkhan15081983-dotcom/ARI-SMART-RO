import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/ro_parts_passport_service.dart';

class ROPartsCaptureScreen extends StatefulWidget {
  const ROPartsCaptureScreen({super.key, required this.jobId});

  final int jobId;

  @override
  State<ROPartsCaptureScreen> createState() => _ROPartsCaptureScreenState();
}

class _ROPartsCaptureScreenState extends State<ROPartsCaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  final ROPartsPassportService _service = const ROPartsPassportService();
  final List<XFile> _photos = <XFile>[];
  final Map<String, Map<String, dynamic>> _selected = {};
  final Set<String> _inventoryVerified = <String>{};

  Map<String, dynamic>? _analysis;
  bool _busy = false;

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _takePhoto() async {
    if (_busy || _photos.length >= 4) return;
    final image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 78,
      maxWidth: 1800,
    );
    if (image == null || !mounted) return;
    setState(() {
      _photos.add(image);
      _analysis = null;
      _selected.clear();
      _inventoryVerified.clear();
    });
  }

  void _removePhoto(int index) {
    if (_busy) return;
    setState(() {
      _photos.removeAt(index);
      _analysis = null;
      _selected.clear();
      _inventoryVerified.clear();
    });
  }

  Future<void> _analyze() async {
    if (_photos.length < 3 || _photos.length > 4 || _busy) return;
    setState(() => _busy = true);
    try {
      final result = await _service.scanJob(
        widget.jobId,
        _photos.map((e) => e.path).toList(),
      );
      final detected = (result['detected_parts'] as List<dynamic>? ?? const []);
      final selected = <String, Map<String, dynamic>>{};
      final inventory = <String>{};
      for (final raw in detected) {
        if (raw is! Map) continue;
        final item = Map<String, dynamic>.from(raw);
        final key = (item['part_key'] ?? '').toString();
        if (key.isEmpty) continue;
        selected[key] = item;
        if (item['inventory_verified'] == true) inventory.add(key);
      }
      if (!mounted) return;
      setState(() {
        _analysis = result;
        _selected
          ..clear()
          ..addAll(selected);
        _inventoryVerified
          ..clear()
          ..addAll(inventory);
      });
      if (selected.isEmpty) {
        _message('AI could not confidently identify a part. Add visible parts manually and confirm.');
      }
    } catch (e) {
      _message(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  List<Map<String, dynamic>> get _catalog {
    final list = _analysis?['catalog'] as List<dynamic>? ?? const [];
    return list
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<void> _addManualPart() async {
    if (_analysis == null) return;
    final available = _catalog
        .where((item) => !_selected.containsKey(item['part_key']?.toString()))
        .toList();
    if (available.isEmpty) {
      _message('All catalog parts are already selected.');
      return;
    }
    final picked = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .72,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
                child: Row(
                  children: [
                    const Icon(Icons.add_circle_outline),
                    const SizedBox(width: 10),
                    Text('Add visible RO part', style: Theme.of(context).textTheme.titleLarge),
                  ],
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView.separated(
                  itemCount: available.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, index) {
                    final item = available[index];
                    return ListTile(
                      leading: const Icon(Icons.settings_outlined),
                      title: Text((item['part_name'] ?? '').toString()),
                      onTap: () => Navigator.pop(context, item),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (picked == null || !mounted) return;
    final key = (picked['part_key'] ?? '').toString();
    if (key.isEmpty) return;
    setState(() {
      _selected[key] = {
        ...picked,
        'confidence': 0.0,
        'evidence': 'Employee added from RO part catalog.',
        'inventory_verified': false,
        'replaced': false,
      };
    });
  }

  void _setReplacement(String key, bool value) {
    if (_inventoryVerified.contains(key)) return;
    setState(() {
      _selected[key] = {...?_selected[key], 'replaced': value};
    });
  }

  Future<void> _confirm() async {
    final analysis = _analysis;
    if (analysis == null || _selected.isEmpty || _busy) return;
    final inspectionId = analysis['inspection_id'];
    if (inspectionId is! int) {
      _message('Invalid inspection. Please scan again.');
      return;
    }
    setState(() => _busy = true);
    try {
      final parts = _selected.entries.map((entry) {
        final item = entry.value;
        return <String, dynamic>{
          'part_key': entry.key,
          'replaced': _inventoryVerified.contains(entry.key) || item['replaced'] == true,
          'evidence': (item['evidence'] ?? '').toString(),
        };
      }).toList();
      await _service.confirmInspection(
        jobId: widget.jobId,
        inspectionId: inspectionId,
        parts: parts,
      );
      if (!mounted) return;
      _message('RO visual parts passport saved.');
      Navigator.of(context).pop(true);
    } catch (e) {
      _message(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _photoGuide() {
    const labels = ['Front', 'Inside left', 'Inside right', 'Full overview'];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Take 3–4 clear photos', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            const Text(
              'Open the RO cover where safe. Keep labels, cartridges, pump, SMPS, valves and housings visible. The system suggests visible parts; you confirm the final record.',
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: List.generate(labels.length, (index) {
                final complete = index < _photos.length;
                return Chip(
                  avatar: Icon(
                    complete ? Icons.check_circle : Icons.camera_alt_outlined,
                    size: 18,
                  ),
                  label: Text(labels[index]),
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _photoStrip() {
    return SizedBox(
      height: 116,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _photos.length + (_photos.length < 4 ? 1 : 0),
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, index) {
          if (index == _photos.length) {
            return SizedBox(
              width: 108,
              child: OutlinedButton(
                onPressed: _busy ? null : _takePhoto,
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.add_a_photo_outlined),
                    SizedBox(height: 6),
                    Text('Take photo', textAlign: TextAlign.center),
                  ],
                ),
              ),
            );
          }
          return Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  File(_photos[index].path),
                  width: 108,
                  height: 116,
                  fit: BoxFit.cover,
                ),
              ),
              Positioned(
                right: 2,
                top: 2,
                child: IconButton.filledTonal(
                  visualDensity: VisualDensity.compact,
                  onPressed: _busy ? null : () => _removePhoto(index),
                  icon: const Icon(Icons.close, size: 18),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _existingParts() {
    final existing = _analysis?['existing_parts'] as List<dynamic>? ?? const [];
    if (existing.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Current saved parts', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ...existing.whereType<Map>().map((raw) {
              final item = Map<String, dynamic>.from(raw);
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.history),
                title: Text((item['part_name'] ?? '').toString()),
                subtitle: Text((item['date_label'] ?? '').toString()),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _identifiedParts() {
    if (_analysis == null) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('Confirm identified parts', style: Theme.of(context).textTheme.titleMedium),
                ),
                TextButton.icon(
                  onPressed: _busy ? null : _addManualPart,
                  icon: const Icon(Icons.add),
                  label: const Text('Add part'),
                ),
              ],
            ),
            if ((_analysis?['ai_summary'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 4),
              Text((_analysis?['ai_summary'] ?? '').toString()),
            ],
            const SizedBox(height: 8),
            if (_selected.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 16),
                child: Text('No confident match. Use “Add part” and select the visible components.'),
              ),
            ..._selected.entries.map((entry) {
              final key = entry.key;
              final item = entry.value;
              final confidence = ((item['confidence'] as num?) ?? 0).toDouble();
              final inventory = _inventoryVerified.contains(key);
              final replaced = inventory || item['replaced'] == true;
              return Container(
                margin: const EdgeInsets.only(top: 10),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  border: Border.all(color: Theme.of(context).dividerColor),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.settings_outlined),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                (item['part_name'] ?? key).toString(),
                                style: const TextStyle(fontWeight: FontWeight.w800),
                              ),
                              if (inventory)
                                const Text('Verified from scanned inventory part', style: TextStyle(color: Colors.green)),
                              if (!inventory && confidence > 0)
                                Text('Visual confidence ${(confidence * 100).round()}%'),
                              if ((item['evidence'] ?? '').toString().isNotEmpty)
                                Text((item['evidence'] ?? '').toString()),
                            ],
                          ),
                        ),
                        IconButton(
                          tooltip: 'Remove from this inspection',
                          onPressed: inventory || _busy
                              ? null
                              : () => setState(() => _selected.remove(key)),
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ],
                    ),
                    SwitchListTile.adaptive(
                      contentPadding: EdgeInsets.zero,
                      value: replaced,
                      onChanged: inventory || _busy ? null : (value) => _setReplacement(key, value),
                      title: Text(inventory ? 'Changed today • inventory verified' : 'Was this part changed today?'),
                      subtitle: Text(
                        inventory
                            ? 'The service inventory record will set the actual change date.'
                            : 'Leave off for an existing part. First-time records use today only as a baseline date.',
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('RO Visual Parts Passport')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _photoGuide(),
          const SizedBox(height: 12),
          _photoStrip(),
          const SizedBox(height: 16),
          if (_analysis == null)
            FilledButton.icon(
              onPressed: _photos.length >= 3 && !_busy ? _analyze : null,
              icon: _busy
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.auto_awesome),
              label: Text(
                _photos.length < 3
                    ? 'Take ${3 - _photos.length} more photo${3 - _photos.length == 1 ? '' : 's'}'
                    : 'Identify RO Parts',
              ),
            )
          else ...[
            _existingParts(),
            const SizedBox(height: 12),
            _identifiedParts(),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _selected.isNotEmpty && !_busy ? _confirm : null,
              icon: _busy
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.verified),
              label: const Text('Confirm & Save RO Passport'),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
