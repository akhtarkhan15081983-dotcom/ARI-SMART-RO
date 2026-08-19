import 'package:flutter/material.dart';
import '../../services/part_request_service.dart';

class PartRequestScreen extends StatefulWidget {
  const PartRequestScreen({super.key, this.service = const PartRequestService()});
  final PartRequestService service;

  @override
  State<PartRequestScreen> createState() => _PartRequestScreenState();
}

class _PartRequestScreenState extends State<PartRequestScreen> {
  late Future<List<EngineerPartRequest>> _requests;

  @override
  void initState() {
    super.initState();
    _requests = widget.service.fetchRequests();
  }

  void _reload() => setState(() => _requests = widget.service.fetchRequests());

  Future<void> _newRequest() async {
    final parts = await widget.service.fetchParts();
    if (!mounted) return;
    if (parts.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No active parts available')));
      return;
    }
    PartOption selected = parts.first;
    final qty = TextEditingController(text: '1');
    final remarks = TextEditingController();
    final submit = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Request Part'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButtonFormField<PartOption>(
                initialValue: selected,
                items: parts.map((p) => DropdownMenuItem(value: p, child: Text('${p.code} - ${p.name}'))).toList(),
                onChanged: (p) { if (p != null) setDialogState(() => selected = p); },
                decoration: const InputDecoration(labelText: 'Part'),
              ),
              TextField(controller: qty, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Quantity')),
              TextField(controller: remarks, decoration: const InputDecoration(labelText: 'Remarks')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Submit')),
          ],
        ),
      ),
    );
    if (submit != true) return;
    final quantity = int.tryParse(qty.text) ?? 0;
    if (quantity < 1) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a valid quantity')));
      return;
    }
    try {
      await widget.service.createRequest(partId: selected.id, quantity: quantity, remarks: remarks.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Part request submitted')));
      _reload();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not submit part request')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Part Requests')),
      floatingActionButton: FloatingActionButton.extended(onPressed: _newRequest, icon: const Icon(Icons.add), label: const Text('Request Part')),
      body: FutureBuilder<List<EngineerPartRequest>>(
        future: _requests,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: FilledButton(onPressed: _reload, child: const Text('Retry')));
          final requests = snapshot.data ?? const <EngineerPartRequest>[];
          if (requests.isEmpty) return const Center(child: Text('No part requests yet'));
          return RefreshIndicator(
            onRefresh: () async { _reload(); await _requests; },
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: requests.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final r = requests[i];
                return Card(child: ListTile(
                  leading: const Icon(Icons.build_circle_outlined),
                  title: Text('${r.partCode} - ${r.partName}'),
                  subtitle: Text('Qty: ${r.quantity}${r.remarks.isEmpty ? '' : '\n${r.remarks}'}'),
                  trailing: Chip(label: Text(r.status)),
                ));
              },
            ),
          );
        },
      ),
    );
  }
}
