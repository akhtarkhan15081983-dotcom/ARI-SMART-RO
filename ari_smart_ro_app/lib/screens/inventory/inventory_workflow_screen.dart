import 'package:flutter/material.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../services/api_service.dart';
import '../../services/inventory_workflow_service.dart';

class InventoryWorkflowScreen extends StatefulWidget {
  const InventoryWorkflowScreen({super.key});
  @override
  State<InventoryWorkflowScreen> createState() =>
      _InventoryWorkflowScreenState();
}

class _InventoryWorkflowScreenState extends State<InventoryWorkflowScreen> {
  final _service = InventoryWorkflowService();
  List<Map<String, dynamic>> _requests = const [], _receiving = const [];
  List<Map<String, dynamic>> _suppliers = const [], _parts = const [];
  Map<String, dynamic> _summary = const {};
  String _role = '';
  String? _error;
  bool _loading = true, _busy = false;
  bool get _canReview => {'ADMIN', 'MANAGER'}.contains(_role);

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
      final values = await Future.wait([
        _service.requests(),
        _service.receivingQueue(),
        _service.suppliers(),
        _service.parts(),
        _service.summary(),
      ]);
      final role = (await ApiService.getRole() ?? '').toUpperCase();
      if (!mounted) return;
      setState(() {
        _requests = values[0] as List<Map<String, dynamic>>;
        _receiving = values[1] as List<Map<String, dynamic>>;
        _suppliers = values[2] as List<Map<String, dynamic>>;
        _parts = values[3] as List<Map<String, dynamic>>;
        _summary = values[4] as Map<String, dynamic>;
        _role = role;
      });
    } catch (e) {
      if (mounted) setState(() => _error = _clean(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _clean(Object e) => e.toString().replaceFirst('Exception: ', '');
  void _show(String text) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
    }
  }

  Future<void> _act(Future<void> Function() action, String success) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
      _show(success);
      await _load();
    } catch (e) {
      _show(_clean(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _scan(String title) => Navigator.push<String>(
    context,
    MaterialPageRoute(builder: (_) => _InventoryCodeScanner(title: title)),
  );

  Future<void> _addSupplier() async {
    final name = TextEditingController(), contact = TextEditingController();
    final phone = TextEditingController(),
        gst = TextEditingController(),
        address = TextEditingController();
    final ok =
        await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Add verified supplier'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: name,
                    decoration: const InputDecoration(
                      labelText: 'Supplier name *',
                    ),
                  ),
                  TextField(
                    controller: contact,
                    decoration: const InputDecoration(
                      labelText: 'Contact person',
                    ),
                  ),
                  TextField(
                    controller: phone,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: 'Phone'),
                  ),
                  TextField(
                    controller: gst,
                    decoration: const InputDecoration(labelText: 'GST number'),
                  ),
                  TextField(
                    controller: address,
                    maxLines: 2,
                    decoration: const InputDecoration(labelText: 'Address'),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('CANCEL'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('SAVE SUPPLIER'),
              ),
            ],
          ),
        ) ??
        false;
    if (ok && name.text.trim().isNotEmpty) {
      await _act(
        () => _service.createSupplier({
          'name': name.text.trim(),
          'contact_person': contact.text.trim(),
          'phone': phone.text.trim(),
          'gst_number': gst.text.trim(),
          'address': address.text.trim(),
          'is_active': true,
        }),
        'Supplier added successfully.',
      );
    }
    for (final c in [name, contact, phone, gst, address]) {
      c.dispose();
    }
  }

  Future<void> _scanInvoice() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: [
            const ListTile(
              title: Text(
                'AI Invoice Scanner',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
              subtitle: Text(
                'Use a clear, flat photo showing the complete invoice.',
              ),
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt_outlined),
              title: const Text('Take invoice photo'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from gallery'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (source == null) return;
    final image = await ImagePicker().pickImage(
      source: source,
      imageQuality: 92,
      maxWidth: 2400,
    );
    if (image == null) return;
    setState(() => _busy = true);
    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    try {
      final result = await recognizer.processImage(
        InputImage.fromFilePath(image.path),
      );
      if (result.text.trim().length < 10) {
        throw Exception(
          'Invoice could not be read. Retake a clear photo in good light.',
        );
      }
      final draft = await _service.analyzeInvoice(image.path, result.text);
      if (!mounted) return;
      if (draft['duplicate'] == true) {
        await showDialog<void>(
          context: context,
          builder: (_) => const AlertDialog(
            icon: Icon(Icons.content_copy_rounded, color: Colors.red),
            title: Text('Duplicate invoice blocked'),
            content: Text(
              'This supplier invoice already exists. Stock was not changed.',
            ),
          ),
        );
        return;
      }
      setState(() => _busy = false);
      await _newPurchase(
        draft: draft,
        imagePath: image.path,
        ocrText: result.text,
      );
    } catch (e) {
      _show(_clean(e));
    } finally {
      await recognizer.close();
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _newPurchase({
    Map<String, dynamic>? draft,
    String? imagePath,
    String? ocrText,
  }) async {
    if (_suppliers.isEmpty || _parts.isEmpty) {
      _show('Add a supplier and part catalog first.');
      return;
    }
    int? supplierId =
        (draft?['supplier'] as num?)?.toInt() ??
        (_suppliers.first['id'] as num).toInt();
    final invoice = TextEditingController(
      text: draft?['invoice_number']?.toString() ?? '',
    );
    final remarks = TextEditingController(
      text: draft == null ? '' : 'Verified from invoice photo',
    );
    var invoiceDate = draft?['invoice_date']?.toString() ?? '';
    final draftItems = draft?['items'] as List<dynamic>? ?? const [];
    final lines = draftItems.isEmpty
        ? <_PurchaseLine>[_PurchaseLine((_parts.first['id'] as num).toInt())]
        : draftItems.map((raw) {
            final item = Map<String, dynamic>.from(raw as Map);
            return _PurchaseLine(
              (item['part'] as num).toInt(),
              quantity: item['quantity']?.toString(),
              price: item['purchase_price']?.toString(),
            );
          }).toList();
    final ok =
        await showDialog<bool>(
          context: context,
          builder: (dialogContext) => StatefulBuilder(
            builder: (_, setDialog) => AlertDialog(
              title: Text(
                draft == null
                    ? 'Create purchase receipt'
                    : 'Verify scanned invoice',
              ),
              content: SizedBox(
                width: 520,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (draft != null) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.blue.shade50,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.document_scanner_outlined),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'OCR confidence: ${draft['confidence']}%\nReview every field before posting.',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        if ((draft['warnings'] as List<dynamic>? ?? const [])
                            .isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              (draft['warnings'] as List<dynamic>).join('\n'),
                              style: TextStyle(color: Colors.orange.shade900),
                            ),
                          ),
                        const SizedBox(height: 8),
                      ],
                      DropdownButtonFormField<int>(
                        initialValue: supplierId,
                        decoration: const InputDecoration(
                          labelText: 'Supplier *',
                        ),
                        items: _suppliers
                            .map(
                              (s) => DropdownMenuItem(
                                value: (s['id'] as num).toInt(),
                                child: Text(s['name'].toString()),
                              ),
                            )
                            .toList(),
                        onChanged: (v) => supplierId = v,
                      ),
                      TextField(
                        controller: invoice,
                        decoration: const InputDecoration(
                          labelText: 'Invoice number *',
                        ),
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.calendar_month_outlined),
                        title: const Text('Invoice date'),
                        subtitle: Text(
                          invoiceDate.isEmpty ? 'Select date' : invoiceDate,
                        ),
                        trailing: const Icon(Icons.edit_calendar_outlined),
                        onTap: () async {
                          final picked = await showDatePicker(
                            context: dialogContext,
                            initialDate:
                                DateTime.tryParse(invoiceDate) ??
                                DateTime.now(),
                            firstDate: DateTime(2020),
                            lastDate: DateTime.now().add(
                              const Duration(days: 1),
                            ),
                          );
                          if (picked != null) {
                            setDialog(
                              () => invoiceDate =
                                  '${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}',
                            );
                          }
                        },
                      ),
                      TextField(
                        controller: remarks,
                        decoration: const InputDecoration(labelText: 'Remarks'),
                      ),
                      const SizedBox(height: 14),
                      ...lines.asMap().entries.map((entry) {
                        final line = entry.value;
                        return Card(
                          child: Padding(
                            padding: const EdgeInsets.all(10),
                            child: Column(
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: DropdownButtonFormField<int>(
                                        initialValue: line.partId,
                                        isExpanded: true,
                                        decoration: InputDecoration(
                                          labelText: 'Part ${entry.key + 1}',
                                        ),
                                        items: _parts
                                            .map(
                                              (p) => DropdownMenuItem(
                                                value: (p['id'] as num).toInt(),
                                                child: Text(
                                                  '${p['code']} • ${p['name']}',
                                                ),
                                              ),
                                            )
                                            .toList(),
                                        onChanged: (v) => line.partId = v,
                                      ),
                                    ),
                                    if (lines.length > 1)
                                      IconButton(
                                        onPressed: () => setDialog(() {
                                          lines.removeAt(entry.key);
                                          line.dispose();
                                        }),
                                        icon: const Icon(Icons.delete_outline),
                                      ),
                                  ],
                                ),
                                Row(
                                  children: [
                                    Expanded(
                                      child: TextField(
                                        controller: line.qty,
                                        keyboardType: TextInputType.number,
                                        decoration: const InputDecoration(
                                          labelText: 'Quantity',
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: TextField(
                                        controller: line.price,
                                        keyboardType:
                                            const TextInputType.numberWithOptions(
                                              decimal: true,
                                            ),
                                        decoration: const InputDecoration(
                                          labelText: 'Unit price',
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        );
                      }),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          onPressed: () => setDialog(
                            () => lines.add(
                              _PurchaseLine(
                                (_parts.first['id'] as num).toInt(),
                              ),
                            ),
                          ),
                          icon: const Icon(Icons.add),
                          label: const Text('ADD ANOTHER PART'),
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
                FilledButton(
                  onPressed: () => Navigator.pop(dialogContext, true),
                  child: Text(
                    draft == null ? 'CREATE PURCHASE' : 'VERIFY & CREATE',
                  ),
                ),
              ],
            ),
          ),
        ) ??
        false;
    if (ok && invoice.text.trim().isNotEmpty && supplierId != null) {
      final valid = lines.every(
        (l) =>
            l.partId != null &&
            (int.tryParse(l.qty.text) ?? 0) > 0 &&
            (double.tryParse(l.price.text) ?? -1) >= 0,
      );
      if (!valid) {
        _show('Enter valid quantity and unit price for every part.');
      } else {
        final now = DateTime.now();
        final date = invoiceDate.isNotEmpty
            ? invoiceDate
            : '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
        final payload = <String, dynamic>{
          'supplier': supplierId,
          'invoice_number': invoice.text.trim(),
          'invoice_date': date,
          'remarks': remarks.text.trim(),
          'ocr_confidence': draft?['confidence'] ?? 0,
          'items': lines
              .map(
                (l) => {
                  'part': l.partId,
                  'quantity': int.parse(l.qty.text),
                  'purchase_price': double.parse(l.price.text),
                },
              )
              .toList(),
        };
        await _act(
          () => draft == null
              ? _service.createPurchase(payload)
              : _service.confirmScannedInvoice(
                  imagePath: imagePath!,
                  ocrText: ocrText!,
                  payload: payload,
                ),
          'Purchase created. Stock is ready for QR generation and receiving.',
        );
      }
    }
    invoice.dispose();
    remarks.dispose();
    for (final l in lines) {
      l.dispose();
    }
  }

  Future<void> _review(Map<String, dynamic> request, String action) async {
    final note = TextEditingController();
    final ok =
        await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            title: Text(
              '${action == 'APPROVE' ? 'Approve' : 'Reject'} part request',
            ),
            content: TextField(
              controller: note,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: action == 'REJECT'
                    ? 'Rejection reason *'
                    : 'Approval note',
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('CANCEL'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(action),
              ),
            ],
          ),
        ) ??
        false;
    if (ok) {
      await _act(
        () => _service.review(
          (request['id'] as num).toInt(),
          action,
          note.text.trim(),
        ),
        'Request ${action.toLowerCase()}d.',
      );
    }
    note.dispose();
  }

  Future<void> _receive(Map<String, dynamic> item) async {
    final code = await _scan('Receive ${item['part_name']}');
    if (code != null) {
      await _act(
        () => _service.receive((item['purchase_item_id'] as num).toInt(), code),
        'Unit verified and added to stock.',
      );
    }
  }

  Future<void> _fulfil(Map<String, dynamic> request) async {
    final qty = (request['quantity'] as num).toInt(), codes = <String>[];
    for (var i = 0; i < qty; i++) {
      final code = await _scan('Scan part ${i + 1} of $qty');
      if (code == null) return;
      if (codes.contains(code)) {
        _show('This QR was already scanned.');
        i--;
      } else {
        codes.add(code);
      }
    }
    await _act(
      () => _service.fulfil((request['id'] as num).toInt(), codes),
      'Parts issued and engineer bag updated.',
    );
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 4,
    child: Scaffold(
      appBar: AppBar(
        title: const Text('Inventory Control'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
        bottom: const TabBar(
          isScrollable: true,
          tabs: [
            Tab(icon: Icon(Icons.shopping_cart_checkout), text: 'PROCUREMENT'),
            Tab(icon: Icon(Icons.approval_outlined), text: 'REQUESTS'),
            Tab(icon: Icon(Icons.qr_code_scanner), text: 'RECEIVING'),
            Tab(icon: Icon(Icons.analytics_outlined), text: 'REPORTS'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? _errorView()
          : TabBarView(
              children: [
                _procurement(),
                _requestList(),
                _receivingList(),
                _reports(),
              ],
            ),
    ),
  );

  Widget _errorView() => Center(
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
  );
  Widget _intro(String title, String text) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
      ),
      const SizedBox(height: 3),
      Text(text, style: TextStyle(color: Colors.blueGrey.shade700)),
      const SizedBox(height: 14),
    ],
  );

  Widget _procurement() => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      _intro(
        'Procurement desk',
        'Register suppliers and convert every invoice into traceable unit-level inventory.',
      ),
      Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _busy ? null : _addSupplier,
              icon: const Icon(Icons.person_add_alt_1),
              label: const Text('ADD SUPPLIER'),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: FilledButton.icon(
              onPressed: _busy ? null : () => _newPurchase(),
              icon: const Icon(Icons.add_shopping_cart),
              label: const Text('NEW PURCHASE'),
            ),
          ),
        ],
      ),
      const SizedBox(height: 10),
      SizedBox(
        width: double.infinity,
        child: FilledButton.tonalIcon(
          onPressed: _busy ? null : _scanInvoice,
          icon: const Icon(Icons.document_scanner_outlined),
          label: const Text('SCAN INVOICE & AUTO-FILL'),
        ),
      ),
      const SizedBox(height: 18),
      Text(
        '${_suppliers.length} registered suppliers',
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
      const SizedBox(height: 8),
      ..._suppliers
          .take(12)
          .map(
            (s) => Card(
              child: ListTile(
                leading: const CircleAvatar(
                  child: Icon(Icons.local_shipping_outlined),
                ),
                title: Text(s['name'].toString()),
                subtitle: Text(
                  [s['contact_person'], s['phone'], s['gst_number']]
                      .where((v) => v != null && v.toString().isNotEmpty)
                      .join(' • '),
                ),
              ),
            ),
          ),
    ],
  );

  Widget _requestList() => RefreshIndicator(
    onRefresh: _load,
    child: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _intro(
          'Approval & issue workflow',
          'Review demand and scan approved physical units into the engineer bag.',
        ),
        if (_requests.isEmpty) _empty('No part requests.'),
        ..._requests.map(
          (r) => Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const CircleAvatar(
                        child: Icon(Icons.build_circle_outlined),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${r['part_code']} • ${r['part_name']}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            Text('${r['engineer_name']} (${r['employee_id']})'),
                          ],
                        ),
                      ),
                      Chip(label: Text(r['status'].toString())),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('Quantity: ${r['quantity']}\n${r['remarks'] ?? ''}'),
                  if (_canReview && r['status'] == 'PENDING')
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => _review(r, 'REJECT'),
                            child: const Text('REJECT'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: FilledButton(
                            onPressed: () => _review(r, 'APPROVE'),
                            child: const Text('APPROVE'),
                          ),
                        ),
                      ],
                    ),
                  if (r['status'] == 'APPROVED')
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: () => _fulfil(r),
                        icon: const Icon(Icons.qr_code_scanner),
                        label: const Text('SCAN & ISSUE PARTS'),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ],
    ),
  );

  Widget _receivingList() => RefreshIndicator(
    onRefresh: _load,
    child: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _intro(
          'Goods receiving',
          'Generate labels, print them, attach each label and scan the physical unit into live stock.',
        ),
        if (_receiving.isEmpty) _empty('No pending inventory receipts.'),
        ..._receiving.map(
          (item) => Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(
                      child: Icon(Icons.inventory_2_outlined),
                    ),
                    title: Text(
                      '${item['part_code']} • ${item['part_name']}',
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    subtitle: Text(
                      '${item['supplier']} • Invoice ${item['invoice_number']}\nPending ${item['pending_count']} of ${item['quantity']}',
                    ),
                  ),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      OutlinedButton.icon(
                        onPressed: _busy
                            ? null
                            : () => _act(() async {
                                final n = await _service.generateCodes(
                                  (item['purchase_item_id'] as num).toInt(),
                                );
                                _show('$n secure QR codes generated.');
                              }, 'QR generation completed.'),
                        icon: const Icon(Icons.qr_code_2),
                        label: const Text('GENERATE QR'),
                      ),
                      OutlinedButton.icon(
                        onPressed: _busy
                            ? null
                            : () async {
                                try {
                                  final path = await _service.downloadQrLabels(
                                    purchaseItemId:
                                        (item['purchase_item_id'] as num)
                                            .toInt(),
                                  );
                                  _show('QR label PDF saved: $path');
                                } catch (e) {
                                  _show(_clean(e));
                                }
                              },
                        icon: const Icon(Icons.print_outlined),
                        label: const Text('PRINT LABELS'),
                      ),
                      FilledButton.icon(
                        onPressed: _busy ? null : () => _receive(item),
                        icon: const Icon(Icons.qr_code_scanner),
                        label: const Text('SCAN RECEIPT'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    ),
  );

  Widget _reports() {
    final cards = [
      ('Total units', 'total_units', Icons.inventory_2),
      ('Pending receipt', 'pending_receipt', Icons.hourglass_top),
      ('In stock', 'in_stock', Icons.warehouse),
      ('Issued', 'issued', Icons.engineering),
      ('Installed', 'installed', Icons.home_repair_service),
      ('Pending requests', 'pending_requests', Icons.pending_actions),
    ];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _intro(
          'Inventory intelligence',
          'Audit-ready stock, procurement, employee issue and movement reports.',
        ),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 2.15,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          children: cards
              .map(
                (c) => Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Icon(c.$3, color: Colors.blue.shade700),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${_summary[c.$2] ?? 0}',
                                style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              Text(c.$1, maxLines: 1),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: () async {
            try {
              final path = await _service.downloadInventoryReport();
              _show('Professional Excel report saved: $path');
            } catch (e) {
              _show(_clean(e));
            }
          },
          icon: const Icon(Icons.table_view_outlined),
          label: const Text('DOWNLOAD COMPLETE EXCEL REPORT'),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () async {
            try {
              final path = await _service.downloadQrLabels();
              _show('All QR labels saved: $path');
            } catch (e) {
              _show(_clean(e));
            }
          },
          icon: const Icon(Icons.picture_as_pdf_outlined),
          label: const Text('DOWNLOAD ALL QR LABELS PDF'),
        ),
        const SizedBox(height: 14),
        const Card(
          child: Padding(
            padding: EdgeInsets.all(14),
            child: Text(
              'Excel contains Executive Summary, Stock Ledger, Purchases, Part Requests and a tamper-evident Audit Trail. Files are saved on this device.',
            ),
          ),
        ),
      ],
    );
  }

  Widget _empty(String text) => Card(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Center(child: Text(text)),
    ),
  );
}

class _PurchaseLine {
  _PurchaseLine(this.partId, {String? quantity, String? price}) {
    qty.text = quantity ?? '1';
    this.price.text = price ?? '0';
  }
  int? partId;
  final qty = TextEditingController();
  final price = TextEditingController();
  void dispose() {
    qty.dispose();
    price.dispose();
  }
}

class _InventoryCodeScanner extends StatefulWidget {
  const _InventoryCodeScanner({required this.title});
  final String title;
  @override
  State<_InventoryCodeScanner> createState() => _InventoryCodeScannerState();
}

class _InventoryCodeScannerState extends State<_InventoryCodeScanner> {
  final _controller = MobileScannerController();
  bool _handled = false;
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(widget.title)),
    body: Stack(
      children: [
        MobileScanner(
          controller: _controller,
          onDetect: (capture) {
            if (_handled) return;
            final value = capture.barcodes.firstOrNull?.rawValue?.trim();
            if (value == null || value.isEmpty) return;
            _handled = true;
            Navigator.pop(context, value);
          },
        ),
        Center(
          child: Container(
            width: 250,
            height: 250,
            decoration: BoxDecoration(
              border: Border.all(color: Colors.white, width: 3),
              borderRadius: BorderRadius.circular(20),
            ),
          ),
        ),
        const Positioned(
          left: 24,
          right: 24,
          bottom: 42,
          child: Card(
            child: Padding(
              padding: EdgeInsets.all(14),
              child: Text(
                'Align one QR/barcode inside the frame. Duplicate and wrong-part scans are rejected automatically.',
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      ],
    ),
  );
}
