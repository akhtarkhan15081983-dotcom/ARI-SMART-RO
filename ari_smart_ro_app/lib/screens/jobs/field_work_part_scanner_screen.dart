import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../services/bag_service.dart';
import '../../services/job_service.dart';

class FieldWorkPartScannerScreen extends StatefulWidget {
  const FieldWorkPartScannerScreen({super.key, required this.jobId});

  final int jobId;

  @override
  State<FieldWorkPartScannerScreen> createState() =>
      _FieldWorkPartScannerScreenState();
}

class _FieldWorkPartScannerScreenState
    extends State<FieldWorkPartScannerScreen> {
  final MobileScannerController _controller = MobileScannerController();
  final BagService _bagService = BagService();
  final JobService _jobService = JobService();
  final List<String> _scannedCodes = <String>[];
  bool _processing = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_processing || capture.barcodes.isEmpty) return;
    final code = capture.barcodes.first.rawValue?.trim();
    if (code == null || code.isEmpty || _scannedCodes.contains(code)) return;

    setState(() => _processing = true);
    try {
      final result = await _bagService.verifyQRCode(code);
      if (result['verified'] != true) {
        _message(result['message']?.toString() ?? 'Part verification failed.');
        return;
      }
      final inventoryItem = result['inventory_item'];
      if (inventoryItem is! int) {
        _message('Invalid inventory item.');
        return;
      }
      final saved = await _jobService.addPartToJob(widget.jobId, inventoryItem);
      if (!saved) {
        _message('This part could not be added to the job.');
        return;
      }
      if (!mounted) return;
      setState(() => _scannedCodes.add(code));
      _message('Part added. Total scanned: ${_scannedCodes.length}');
    } catch (_) {
      _message('Unable to scan this part. Please try again.');
    } finally {
      if (mounted) setState(() => _processing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Used Parts')),
      body: Column(
        children: [
          Expanded(
            child: MobileScanner(
              controller: _controller,
              onDetect: _onDetect,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Scanned parts: ${_scannedCodes.length}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: _scannedCodes.isEmpty
                      ? null
                      : () => Navigator.of(context).pop(true),
                  icon: const Icon(Icons.check_circle),
                  label: const Text('Finish Parts Scan'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
