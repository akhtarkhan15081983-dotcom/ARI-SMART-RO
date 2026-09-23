import 'package:flutter/material.dart';

import '../../services/inventory_workflow_service.dart';
import '../../utils/search_utils.dart';

class RoStockWorkflowScreen extends StatefulWidget {
  const RoStockWorkflowScreen({super.key});

  @override
  State<RoStockWorkflowScreen> createState() => _RoStockWorkflowScreenState();
}

class _RoStockWorkflowScreenState extends State<RoStockWorkflowScreen> {
  final _service = InventoryWorkflowService();
  final _searchController = TextEditingController();
  List<Map<String, dynamic>> _assets = const [];
  List<Map<String, dynamic>> _models = const [];
  List<Map<String, dynamic>> _customers = const [];
  Map<String, dynamic> _summary = const {};
  bool _loading = true;
  bool _busy = false;
  String? _error;
  String _query = '';
  String _status = 'ALL';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final values = await Future.wait([
        _service.roAssets(),
        _service.roModels(),
        _service.customers(),
        _service.roSummary(),
      ]);
      if (!mounted) return;
      setState(() {
        _assets = values[0] as List<Map<String, dynamic>>;
        _models = values[1] as List<Map<String, dynamic>>;
        _customers = values[2] as List<Map<String, dynamic>>;
        _summary = values[3] as Map<String, dynamic>;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> get _visible => _assets.where((row) {
        if (_status != 'ALL' && row['status']?.toString() != _status) {
          return false;
        }
        return matchesAllSearchTerms(_query, [
          row['asset_id']?.toString() ?? '',
          row['serial_number']?.toString() ?? '',
          row['ro_model_name']?.toString() ?? '',
          row['customer_name']?.toString() ?? '',
          row['deployment_type']?.toString() ?? '',
          row['status']?.toString() ?? '',
        ]);
      }).toList();

  void _show(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
      _show(success);
      await _load();
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _receiveStock() async {
    if (_models.isEmpty) {
      _show('Add an RO model first.');
      return;
    }
    int? modelId = (_models.first['id'] as num?)?.toInt();
    final serials = TextEditingController();
    final invoice = TextEditingController();
    final price = TextEditingController(text: '0');
    var purchaseDate = DateTime.now();
    final ok = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => StatefulBuilder(
            builder: (_, setDialog) => AlertDialog(
              title: const Text('Receive complete RO stock'),
              content: SizedBox(
                width: 560,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      DropdownButtonFormField<int>(
                        initialValue: modelId,
                        isExpanded: true,
                        decoration: const InputDecoration(labelText: 'RO model *'),
                        items: _models.map((model) {
                          return DropdownMenuItem<int>(
                            value: (model['id'] as num).toInt(),
                            child: Text(model['model_name']?.toString() ?? 'RO'),
                          );
                        }).toList(),
                        onChanged: (v) => modelId = v,
                      ),
                      TextField(
                        controller: invoice,
                        decoration: const InputDecoration(labelText: 'Purchase invoice'),
                      ),
                      TextField(
                        controller: price,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(labelText: 'Purchase price per RO'),
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.calendar_month_outlined),
                        title: const Text('Purchase date'),
                        subtitle: Text(
                          '${purchaseDate.year}-${purchaseDate.month.toString().padLeft(2, '0')}-${purchaseDate.day.toString().padLeft(2, '0')}',
                        ),
                        onTap: () async {
                          final picked = await showDatePicker(
                            context: dialogContext,
                            firstDate: DateTime(2020),
                            lastDate: DateTime.now(),
                            initialDate: purchaseDate,
                          );
                          if (picked != null) {
                            setDialog(() => purchaseDate = picked);
                          }
                        },
                      ),
                      TextField(
                        controller: serials,
                        minLines: 6,
                        maxLines: 12,
                        decoration: const InputDecoration(
                          labelText: 'RO serial numbers *',
                          hintText: 'One serial per line\nExample:\nARI50-001\nARI50-002',
                          helperText: '50 RO aaye hain to 50 serial numbers ek saath paste kar sakte hain.',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext, false),
                  child: const Text('CANCEL'),
                ),
                FilledButton.icon(
                  onPressed: () => Navigator.pop(dialogContext, true),
                  icon: const Icon(Icons.inventory_2_outlined),
                  label: const Text('RECEIVE STOCK'),
                ),
              ],
            ),
          ),
        ) ??
        false;

    final values = serials.text
        .replaceAll(',', '\n')
        .split('\n')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList();
    final enteredPrice = double.tryParse(price.text.trim());
    if (ok && modelId != null && values.isNotEmpty && enteredPrice != null) {
      final date =
          '${purchaseDate.year}-${purchaseDate.month.toString().padLeft(2, '0')}-${purchaseDate.day.toString().padLeft(2, '0')}';
      await _run(() async {
        final count = await _service.receiveRoStock(
          roModelId: modelId!,
          serialNumbers: values,
          purchaseInvoice: invoice.text.trim(),
          purchaseDate: date,
          purchasePrice: enteredPrice,
        );
        _show('$count RO units received into warehouse.');
      }, 'RO stock updated successfully.');
    }
    serials.dispose();
    invoice.dispose();
    price.dispose();
  }

  Future<void> _allocate(Map<String, dynamic> asset, String type) async {
    if (_customers.isEmpty) {
      _show('No active customer is available. Add/select a customer first.');
      return;
    }
    int? customerId = (_customers.first['id'] as num?)?.toInt();
    final note = TextEditingController();
    final ok = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => StatefulBuilder(
            builder: (_, setDialog) => AlertDialog(
              title: Text(type == 'SALE' ? 'Sell this RO' : 'Give this RO on rent'),
              content: SizedBox(
                width: 520,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(asset['ro_model_name']?.toString() ?? 'RO'),
                      subtitle: Text(
                        '${asset['asset_id']} • Serial ${asset['serial_number']}',
                      ),
                    ),
                    DropdownButtonFormField<int>(
                      initialValue: customerId,
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'Customer *'),
                      items: _customers.map((customer) {
                        final id = (customer['id'] as num).toInt();
                        final name = customer['name']?.toString() ?? 'Customer';
                        final phone = customer['phone']?.toString() ?? '';
                        return DropdownMenuItem<int>(
                          value: id,
                          child: Text('$name${phone.isEmpty ? '' : ' • $phone'}'),
                        );
                      }).toList(),
                      onChanged: (v) => customerId = v,
                    ),
                    TextField(
                      controller: note,
                      maxLines: 2,
                      decoration: const InputDecoration(labelText: 'Remarks'),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext, false),
                  child: const Text('CANCEL'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(dialogContext, true),
                  child: Text(type == 'SALE' ? 'CONFIRM SALE' : 'CONFIRM RENTAL'),
                ),
              ],
            ),
          ),
        ) ??
        false;
    if (ok && customerId != null) {
      await _run(
        () => _service.allocateRo(
          assetId: (asset['id'] as num).toInt(),
          customerId: customerId!,
          deploymentType: type,
          remarks: note.text.trim(),
        ),
        type == 'SALE'
            ? 'RO reserved for customer sale and removed from warehouse stock.'
            : 'RO assigned on rent and removed from warehouse stock.',
      );
    }
    note.dispose();
  }

  Future<void> _returnRental(Map<String, dynamic> asset) async {
    await _run(
      () => _service.returnRentalRo((asset['id'] as num).toInt()),
      'Rental RO marked returned. QC/restock is now pending.',
    );
  }

  Future<void> _restock(Map<String, dynamic> asset) async {
    await _run(
      () => _service.restockRo(
        (asset['id'] as num).toInt(),
        remarks: 'QC passed and returned to warehouse',
      ),
      'RO returned to available warehouse stock.',
    );
  }

  Widget _summaryCard(String title, String key, IconData icon) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Icon(icon),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      '${_summary[key] ?? 0}',
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                    ),
                    Text(title, maxLines: 1),
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('RO Stock • Sale • Rent'),
          actions: [
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: _busy ? null : _receiveStock,
          icon: const Icon(Icons.add_box_outlined),
          label: const Text('RECEIVE RO'),
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
                          Text(_error!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(onPressed: _load, child: const Text('RETRY')),
                        ],
                      ),
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                      children: [
                        const Text(
                          'Complete RO Inventory',
                          style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Every physical RO is tracked by model, serial, customer and Sale/Rent lifecycle.',
                          style: TextStyle(color: Colors.blueGrey.shade700),
                        ),
                        const SizedBox(height: 14),
                        GridView.count(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          crossAxisCount: 2,
                          childAspectRatio: 2.2,
                          mainAxisSpacing: 8,
                          crossAxisSpacing: 8,
                          children: [
                            _summaryCard('Warehouse', 'warehouse', Icons.warehouse_outlined),
                            _summaryCard('Assigned', 'assigned', Icons.assignment_turned_in_outlined),
                            _summaryCard('Installed', 'installed', Icons.home_repair_service_outlined),
                            _summaryCard('Returned', 'returned', Icons.keyboard_return_outlined),
                          ],
                        ),
                        const SizedBox(height: 14),
                        TextField(
                          controller: _searchController,
                          onChanged: (v) => setState(() => _query = v),
                          decoration: InputDecoration(
                            hintText: 'Search model, asset ID, serial or customer...',
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: _query.isEmpty
                                ? null
                                : IconButton(
                                    onPressed: () {
                                      _searchController.clear();
                                      setState(() => _query = '');
                                    },
                                    icon: const Icon(Icons.clear),
                                  ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<String>(
                          initialValue: _status,
                          decoration: const InputDecoration(labelText: 'RO status'),
                          items: const [
                            DropdownMenuItem(value: 'ALL', child: Text('All RO units')),
                            DropdownMenuItem(value: 'WAREHOUSE', child: Text('Warehouse / available')),
                            DropdownMenuItem(value: 'ASSIGNED', child: Text('Assigned for sale/rent')),
                            DropdownMenuItem(value: 'INSTALLED', child: Text('Installed')),
                            DropdownMenuItem(value: 'RETURNED', child: Text('Returned / QC pending')),
                            DropdownMenuItem(value: 'REPAIR', child: Text('Repair')),
                            DropdownMenuItem(value: 'SCRAP', child: Text('Scrap')),
                          ],
                          onChanged: (v) => setState(() => _status = v ?? 'ALL'),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          '${_visible.length} of ${_assets.length} physical RO units',
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 8),
                        if (_visible.isEmpty)
                          const Card(
                            child: Padding(
                              padding: EdgeInsets.all(24),
                              child: Center(child: Text('No RO units match this filter.')),
                            ),
                          ),
                        ..._visible.map((asset) {
                          final status = asset['status']?.toString() ?? '';
                          final deployment = asset['deployment_type']?.toString() ?? '';
                          return Card(
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      const CircleAvatar(child: Icon(Icons.water_drop_outlined)),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              asset['ro_model_name']?.toString() ?? 'RO',
                                              style: const TextStyle(fontWeight: FontWeight.w900),
                                            ),
                                            Text('${asset['asset_id']} • ${asset['serial_number']}'),
                                          ],
                                        ),
                                      ),
                                      Chip(label: Text(status)),
                                    ],
                                  ),
                                  if ((asset['customer_name'] ?? '').toString().isNotEmpty) ...[
                                    const SizedBox(height: 8),
                                    Text(
                                      'Customer: ${asset['customer_name']} • ${deployment.isEmpty ? 'Assigned' : deployment}',
                                      style: const TextStyle(fontWeight: FontWeight.w700),
                                    ),
                                  ],
                                  if ((asset['purchase_invoice'] ?? '').toString().isNotEmpty)
                                    Text('Invoice: ${asset['purchase_invoice']}'),
                                  const SizedBox(height: 10),
                                  if (status == 'WAREHOUSE')
                                    Row(
                                      children: [
                                        Expanded(
                                          child: FilledButton.icon(
                                            onPressed: _busy ? null : () => _allocate(asset, 'SALE'),
                                            icon: const Icon(Icons.shopping_bag_outlined),
                                            label: const Text('SELL'),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: OutlinedButton.icon(
                                            onPressed: _busy ? null : () => _allocate(asset, 'RENT'),
                                            icon: const Icon(Icons.currency_rupee_outlined),
                                            label: const Text('RENT'),
                                          ),
                                        ),
                                      ],
                                    ),
                                  if (deployment == 'RENT' &&
                                      {'ASSIGNED', 'INSTALLED', 'SERVICE', 'REPAIR'}.contains(status))
                                    SizedBox(
                                      width: double.infinity,
                                      child: OutlinedButton.icon(
                                        onPressed: _busy ? null : () => _returnRental(asset),
                                        icon: const Icon(Icons.keyboard_return_outlined),
                                        label: const Text('RECEIVE RENTAL RETURN'),
                                      ),
                                    ),
                                  if (status == 'RETURNED' || status == 'REFURBISHED')
                                    SizedBox(
                                      width: double.infinity,
                                      child: FilledButton.tonalIcon(
                                        onPressed: _busy ? null : () => _restock(asset),
                                        icon: const Icon(Icons.warehouse_outlined),
                                        label: const Text('QC PASSED • RESTOCK'),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          );
                        }),
                      ],
                    ),
                  ),
      );
}
