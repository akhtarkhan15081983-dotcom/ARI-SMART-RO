import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../services/customer_service.dart';

class CustomerBulkImportScreen extends StatefulWidget {
  const CustomerBulkImportScreen({super.key});

  @override
  State<CustomerBulkImportScreen> createState() => _CustomerBulkImportScreenState();
}

class _CustomerBulkImportScreenState extends State<CustomerBulkImportScreen> {
  final CustomerService service = CustomerService();
  PlatformFile? selectedFile;
  Map<String, dynamic>? preview;
  bool busy = false;

  Future<void> _pickFile() async {
    if (Platform.isWindows) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Windows Safe Build: Excel file picker is temporarily disabled. '
            'Use Android for bulk import while the signed Windows installer is prepared.',
          ),
        ),
      );
      return;
    }
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['xlsx', 'csv'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    setState(() {
      selectedFile = result.files.single;
      preview = null;
    });
  }

  Future<void> _upload({required bool previewOnly}) async {
    final file = selectedFile;
    if (file == null || file.bytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select an Excel or CSV file first.')),
      );
      return;
    }
    setState(() => busy = true);
    try {
      final result = await service.bulkImportCustomers(
        filename: file.name,
        bytes: file.bytes!,
        previewOnly: previewOnly,
      );
      if (!mounted) return;
      setState(() => preview = result);
      final summary = (result['summary'] as Map?)?.cast<String, dynamic>() ?? {};
      final ready = summary['ready_or_created'] ?? 0;
      final duplicates = summary['duplicates'] ?? 0;
      final errors = summary['errors'] ?? 0;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: errors == 0 ? Colors.green : Colors.orange,
          content: Text(
            previewOnly
                ? 'Preview: $ready ready, $duplicates duplicate, $errors error'
                : 'Imported: $ready, duplicate: $duplicates, errors: $errors',
          ),
        ),
      );
      if (!previewOnly && ready is num && ready > 0) {
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(backgroundColor: Colors.red, content: Text(e.toString())),
      );
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final summary = (preview?['summary'] as Map?)?.cast<String, dynamic>();
    return Scaffold(
      appBar: AppBar(title: const Text('Bulk Customer Import')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Upload XLSX or CSV. Required columns: Name and Phone. '
            'Duplicate phone numbers will be skipped automatically.',
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: busy ? null : _pickFile,
            icon: const Icon(Icons.upload_file),
            label: Text(selectedFile?.name ?? 'Select Excel / CSV File'),
          ),
          if (selectedFile != null) ...[
            const SizedBox(height: 8),
            Text(
              '${selectedFile!.name} • ${(selectedFile!.size / 1024).toStringAsFixed(1)} KB',
              textAlign: TextAlign.center,
            ),
          ],
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: busy ? null : () => _upload(previewOnly: true),
                  child: const Text('Preview'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton(
                  onPressed: busy ? null : () => _upload(previewOnly: false),
                  child: busy
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Import Customers'),
                ),
              ),
            ],
          ),
          if (summary != null) ...[
            const SizedBox(height: 24),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    _row('Rows', summary['total_rows']),
                    _row('Ready / Created', summary['ready_or_created']),
                    _row('Duplicates', summary['duplicates']),
                    _row('Errors', summary['errors']),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          const Text(
            'Each successfully imported customer automatically receives a '
            'stable ARI SMART RO customer QR.',
          ),
        ],
      ),
    );
  }

  Widget _row(String label, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Expanded(child: Text(label)),
          Text('${value ?? 0}', style: const TextStyle(fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}