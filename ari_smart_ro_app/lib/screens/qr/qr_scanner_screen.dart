import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../services/bag_service.dart';
import '../../services/job_service.dart';


class QRScanScreen extends StatefulWidget {
  final int jobId;

  const QRScanScreen({
    super.key,
    required this.jobId,
  });

  @override
  State<QRScanScreen> createState() => _QRScanScreenState();
}

class _QRScanScreenState extends State<QRScanScreen> {
  final MobileScannerController controller = MobileScannerController();
  final BagService bagService = BagService();
  final JobService jobService = JobService();

  bool _isScanned = false;

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_isScanned) return;

    final Barcode? barcode = capture.barcodes.firstOrNull;

    if (barcode == null) return;

    final String? value = barcode.rawValue;

    if (value == null || value.isEmpty) return;

    _isScanned = true;

    final result = await bagService.verifyQRCode(value);

    if (!mounted) return;

    if (result["verified"] == true) {

      final bool saved = await jobService.addPartToJob(
        widget.jobId,
        result["inventory_item"],
      );

      if (!mounted) return;

      if (saved) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Part verified & added successfully."),
            backgroundColor: Colors.green,
          ),
        );

        Navigator.pop(context, true);

      } else {

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Part verified but could not be added."),
            backgroundColor: Colors.orange,
          ),
        );

        setState(() {
          _isScanned = false;
        });
      }

    } else {

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result["message"]),
          backgroundColor: Colors.red,
        ),
      );

      setState(() {
        _isScanned = false;
      });

    }
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Scan QR Code"),
        centerTitle: true,
      ),
      body: MobileScanner(
        controller: controller,
        onDetect: _onDetect,
      ),
    );
  }
}