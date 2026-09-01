import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../jobs/signature_screen.dart';
import '../../services/bag_service.dart';
import '../../services/job_service.dart';

class QRScanScreen extends StatefulWidget {
  final int jobId;

  const QRScanScreen({super.key, required this.jobId});

  @override
  State<QRScanScreen> createState() => _QRScanScreenState();
}

class _QRScanScreenState extends State<QRScanScreen> {
  final MobileScannerController controller = MobileScannerController();
  final BagService bagService = BagService();
  final JobService jobService = JobService();

  final List<Map<String, dynamic>> scannedParts = [];

  final TextEditingController inputTdsController = TextEditingController();
  final TextEditingController outputTdsController = TextEditingController();
  final TextEditingController referralController = TextEditingController();
  final TextEditingController remarksController = TextEditingController();
  final TextEditingController customerNameController = TextEditingController();
  final ImagePicker _picker = ImagePicker();
  final TextEditingController otpController = TextEditingController();

  String? _generatedOtp;
  bool _otpVerified = false;

  bool _isProcessingScan = false;
  bool _isCameraPaused = false;
  bool _isSavingInstallation = false;
  _InstallationStep _step = _InstallationStep.scanning;

  File? _customerPhoto;
  Uint8List? _signatureBytes;
  bool _photoUploaded = false;

  int get totalParts => scannedParts.length;

  @override
  void dispose() {
    controller.dispose();
    inputTdsController.dispose();
    outputTdsController.dispose();
    referralController.dispose();
    remarksController.dispose();
    customerNameController.dispose();
    otpController.dispose();
    super.dispose();
  }

  Future<void> _pauseCamera() async {
    if (_isCameraPaused) return;

    try {
      await controller.stop();
    } catch (_) {
      // Camera may already be stopped by the scanner lifecycle.
    }

    if (!mounted) return;

    setState(() {
      _isCameraPaused = true;
    });
  }

  Future<void> _scanNextPart() async {
    if (_isProcessingScan) return;

    setState(() {
      _isCameraPaused = false;
      _isProcessingScan = false;
    });

    try {
      await controller.start();
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _isCameraPaused = true;
      });

      _showMessage('Unable to start camera. Please try again.', Colors.red);
    }
  }

  Future<void> _resumeAfterFailedScan() async {
    if (!mounted) return;

    setState(() {
      _isProcessingScan = false;
      _isCameraPaused = false;
    });

    try {
      await controller.start();
    } catch (_) {
      if (!mounted) return;

      setState(() {
        _isCameraPaused = true;
      });
    }
  }

  void _showMessage(String message, Color color) {
    if (!mounted) return;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: color,
          behavior: SnackBarBehavior.floating,
        ),
      );
  }

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_isProcessingScan || _isCameraPaused) return;

    final Barcode? barcode = capture.barcodes.firstOrNull;
    final String? value = barcode?.rawValue?.trim();

    if (value == null || value.isEmpty) return;

    setState(() {
      _isProcessingScan = true;
    });

    // Stop immediately so the same QR cannot trigger repeatedly.
    await _pauseCamera();

    final alreadyScanned = scannedParts.any((part) => part['qr'] == value);

    if (alreadyScanned) {
      _showMessage(
        'This part is already scanned. Scan another part.',
        Colors.orange,
      );

      await _resumeAfterFailedScan();
      return;
    }

    try {
      final result = await bagService.verifyQRCode(value);

      if (!mounted) return;

      if (result['verified'] != true) {
        _showMessage(
          result['message']?.toString() ?? 'QR code verification failed.',
          Colors.red,
        );

        await _resumeAfterFailedScan();
        return;
      }

      final bool saved = await jobService.addPartToJob(
        widget.jobId,
        result['inventory_item'],
      );

      if (!mounted) return;

      if (!saved) {
        _showMessage(
          'Part verified but could not be added. Please try again.',
          Colors.orange,
        );

        await _resumeAfterFailedScan();
        return;
      }

      setState(() {
        scannedParts.add({
          'inventory_item': result['inventory_item'],
          'qr': value,
        });
        _isProcessingScan = false;
        _isCameraPaused = true;
      });

      _showMessage(
        'Part added successfully.\nTotal parts: $totalParts',
        Colors.green,
      );
    } catch (_) {
      if (!mounted) return;

      _showMessage(
        'Something went wrong while scanning. Please try again.',
        Colors.red,
      );

      await _resumeAfterFailedScan();
    }
  }

  Future<void> _finishScanning() async {
    await _pauseCamera();
    if (!mounted) return;

    setState(() => _step = _InstallationStep.photo);
  }

  Future<void> _captureCustomerPhoto() async {
    final image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 80,
    );
    if (image == null || !mounted) return;

    setState(() => _isSavingInstallation = true);
    try {
      final uploaded = await jobService.uploadPhoto(
        widget.jobId,
        image.path,
        'Customer installation photo',
      );
      if (!mounted) return;
      if (!uploaded) {
        _showMessage('Photo upload failed. Please try again.', Colors.red);
        return;
      }
      setState(() {
        _customerPhoto = File(image.path);
        _photoUploaded = true;
        _step = _InstallationStep.otp;
      });
      _showMessage('Customer photo uploaded.', Colors.green);
    } catch (_) {
      _showMessage('Photo upload failed. Please try again.', Colors.red);
    } finally {
      if (mounted) setState(() => _isSavingInstallation = false);
    }
  }

  Future<void> _generateOtp() async {
    if (_isSavingInstallation) return;

    setState(() {
      _isSavingInstallation = true;
    });

    try {
      final otp = await jobService.generateOTP(widget.jobId);

      if (!mounted) return;

      if (otp == null) {
        _showMessage('Unable to generate OTP. Please try again.', Colors.red);
        return;
      }

      setState(() {
        _generatedOtp = otp.toString();
      });

      _showMessage(
        'OTP generated. Please share it with the customer.',
        Colors.green,
      );
    } catch (_) {
      if (!mounted) return;

      _showMessage('Unable to generate OTP.', Colors.red);
    } finally {
      if (mounted) {
        setState(() {
          _isSavingInstallation = false;
        });
      }
    }
  }

  Future<void> _verifyOtp() async {
    final otp = otpController.text.trim();

    if (otp.isEmpty) {
      _showMessage('Please enter customer OTP.', Colors.red);
      return;
    }

    if (otp.length != 6) {
      _showMessage('OTP must be 6 digits.', Colors.red);
      return;
    }

    if (_isSavingInstallation) return;

    setState(() {
      _isSavingInstallation = true;
    });

    try {
      final success = await jobService.verifyOTP(widget.jobId, otp);

      if (!mounted) return;

      if (!success) {
        _showMessage('Invalid OTP.', Colors.red);
        return;
      }

      setState(() {
        _otpVerified = true;
        _step = _InstallationStep.signature;
      });

      _showMessage('Customer OTP verified successfully.', Colors.green);
    } catch (_) {
      if (!mounted) return;

      _showMessage('Unable to verify OTP.', Colors.red);
    } finally {
      if (mounted) {
        setState(() {
          _isSavingInstallation = false;
        });
      }
    }
  }

  Future<void> _captureSignature() async {
    final result = await Navigator.push<Uint8List>(
      context,
      MaterialPageRoute(builder: (_) => const SignatureScreen()),
    );

    if (result == null || !mounted) return;

    setState(() {
      _signatureBytes = result;
      _step = _InstallationStep.details;
    });

    _showMessage('Customer signature captured.', Colors.green);
  }

  Future<void> _completeInstallation() async {
    if (!_photoUploaded || _signatureBytes == null) {
      _showMessage('Please complete photo and signature first.', Colors.red);
      return;
    }
    if (!_otpVerified) {
      _showMessage('Please verify customer OTP first.', Colors.red);
      return;
    }

    if (inputTdsController.text.trim().isEmpty) {
      _showMessage('Please enter Input TDS.', Colors.red);
      return;
    }

    if (outputTdsController.text.trim().isEmpty) {
      _showMessage('Please enter Output TDS.', Colors.red);
      return;
    }

    final inputTds = int.tryParse(inputTdsController.text.trim());

    final outputTds = int.tryParse(outputTdsController.text.trim());

    if (inputTds == null || inputTds < 0) {
      _showMessage('Please enter a valid Input TDS.', Colors.red);
      return;
    }

    if (outputTds == null || outputTds < 0) {
      _showMessage('Please enter a valid Output TDS.', Colors.red);
      return;
    }
    if (customerNameController.text.trim().isEmpty) {
      _showMessage('Please enter the customer name.', Colors.red);
      return;
    }

    setState(() => _isSavingInstallation = true);
    try {
      final signatureUploaded = await jobService.uploadSignature(
        widget.jobId,
        _signatureBytes!,
        customerNameController.text.trim(),
      );
      if (!signatureUploaded) {
        _showMessage('Signature upload failed. Please try again.', Colors.red);
        return;
      }

      final installationSaved = await jobService.completeInstallation(
        jobId: widget.jobId,
        inputTds: int.tryParse(inputTdsController.text.trim()) ?? 0,
        outputTds: int.tryParse(outputTdsController.text.trim()) ?? 0,
        referral: referralController.text.trim(),
        remarks: remarksController.text.trim(),
      );
      if (!installationSaved) {
        _showMessage('Installation save failed. Please try again.', Colors.red);
        return;
      }

      final completed = await jobService.changeJobStatus(
        widget.jobId,
        'COMPLETED',
      );
      if (!mounted) return;
      if (!completed) {
        _showMessage(
          'Installation saved, but job status could not be completed.',
          Colors.orange,
        );
        return;
      }

      _showMessage('Installation completed successfully.', Colors.green);
      Navigator.pop(context, true);
    } catch (_) {
      _showMessage(
        'Unable to complete installation. Please try again.',
        Colors.red,
      );
    } finally {
      if (mounted) setState(() => _isSavingInstallation = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;

        if (_step == _InstallationStep.details) {
          setState(() {
            _step = _InstallationStep.signature;
          });
          return;
        }

        if (_step == _InstallationStep.signature) {
          setState(() {
            _step = _InstallationStep.otp;
          });
          return;
        }

        if (_step == _InstallationStep.otp) {
          setState(() {
            _step = _InstallationStep.photo;
            _generatedOtp = null;
            otpController.clear();
          });
          return;
        }

        if (_step == _InstallationStep.photo) {
          setState(() {
            _step = _InstallationStep.scanning;
          });
          return;
        }

        Navigator.of(context).pop();
      },
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: false,
          title: Text(_appBarTitle),
          centerTitle: true,
        ),
        body: Column(
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              color: theme.colorScheme.primaryContainer,
              child: Row(
                children: [
                  Icon(
                    Icons.inventory_2_outlined,
                    color: theme.colorScheme.onPrimaryContainer,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Scanned Parts: $totalParts',
                    style: TextStyle(
                      color: theme.colorScheme.onPrimaryContainer,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),

            Expanded(
              child: _step == _InstallationStep.scanning
                  ? _buildScanner()
                  : _buildProofStep(),
            ),

            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: SizedBox(
                  width: double.infinity,
                  child: _buildPrimaryAction(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String get _appBarTitle {
    switch (_step) {
      case _InstallationStep.scanning:
        return 'Scan QR Code';

      case _InstallationStep.photo:
        return 'Customer Photo';

      case _InstallationStep.details:
        return 'Installation Details';

      case _InstallationStep.otp:
        return 'Customer OTP';

      case _InstallationStep.signature:
        return 'Customer Signature';
    }
  }

  Widget _buildScanner() => Column(
    children: [
      Expanded(
        flex: 3,
        child: Stack(
          fit: StackFit.expand,
          children: [
            MobileScanner(controller: controller, onDetect: _onDetect),
            if (_isCameraPaused) _cameraPausedOverlay(),
            if (_isProcessingScan && !_isCameraPaused)
              const Center(
                child: CircularProgressIndicator(color: Colors.white),
              ),
          ],
        ),
      ),
      Expanded(flex: 2, child: _scannedPartsList()),
    ],
  );

  Widget _cameraPausedOverlay() => Container(
    color: Colors.black54,
    alignment: Alignment.center,
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.pause_circle_filled, color: Colors.white, size: 58),
        const SizedBox(height: 12),
        Text(
          _isProcessingScan ? 'Verifying part...' : 'Camera paused',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    ),
  );

  Widget _scannedPartsList() => scannedParts.isEmpty
      ? const Center(
          child: Text(
            'No parts scanned yet.',
            style: TextStyle(color: Colors.grey),
          ),
        )
      : ListView.separated(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: scannedParts.length,
          separatorBuilder: (_, _) => const Divider(height: 1),
          itemBuilder: (context, index) => ListTile(
            leading: const Icon(Icons.check_circle, color: Colors.green),
            title: Text(scannedParts[index]['qr'].toString()),
            subtitle: Text('Part ${index + 1}'),
          ),
        );

  Widget _buildProofStep() {
    Widget child;

    switch (_step) {
      case _InstallationStep.photo:
        child = _proofCard(
          icon: Icons.camera_alt_outlined,
          title: 'Capture customer photo',
          message: 'Take a clear photo as proof of the completed installation.',
          preview: _customerPhoto == null
              ? null
              : Image.file(_customerPhoto!, height: 220),
        );
        break;

      case _InstallationStep.signature:
        child = _proofCard(
          icon: Icons.draw_outlined,
          title: 'Capture customer signature',
          message: 'Ask the customer to sign and confirm the installation.',
        );
        break;
      case _InstallationStep.otp:
        child = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.verified_user, size: 72, color: Colors.green),

            const SizedBox(height: 16),

            const Text(
              'Verify Customer OTP',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 8),

            const Text(
              'Generate the OTP and ask the customer to tell you the OTP.',
              textAlign: TextAlign.center,
            ),

            const SizedBox(height: 24),

            if (_generatedOtp != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [
                      const Text(
                        'Customer OTP',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),

                      const SizedBox(height: 8),

                      Text(
                        _generatedOtp!,
                        style: const TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 6,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 20),

              TextField(
                controller: otpController,
                keyboardType: TextInputType.number,
                maxLength: 6,
                decoration: const InputDecoration(
                  labelText: 'Enter Customer OTP *',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.lock),
                ),
              ),
            ],
          ],
        );
        break;
      case _InstallationStep.details:
        child = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Enter final installation details.',
              style: TextStyle(fontSize: 16),
            ),

            const SizedBox(height: 16),

            TextField(
              controller: customerNameController,
              decoration: const InputDecoration(
                labelText: 'Customer Name *',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 12),

            TextField(
              controller: inputTdsController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Input TDS',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 12),

            TextField(
              controller: outputTdsController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Output TDS',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 12),

            TextField(
              controller: referralController,
              decoration: const InputDecoration(
                labelText: 'Referral Name',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 12),

            TextField(
              controller: remarksController,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Remarks',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        );
        break;

      case _InstallationStep.scanning:
        child = const SizedBox.shrink();
        break;
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: child,
    );
  }

  Widget _proofCard({
    required IconData icon,
    required String title,
    required String message,
    Widget? preview,
  }) => Column(
    children: [
      Icon(icon, size: 72, color: Theme.of(context).colorScheme.primary),
      const SizedBox(height: 16),
      Text(
        title,
        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
        textAlign: TextAlign.center,
      ),
      const SizedBox(height: 8),
      Text(message, textAlign: TextAlign.center),
      if (preview != null) ...[const SizedBox(height: 20), preview],
    ],
  );

  Widget _buildPrimaryAction() {
    if (_step == _InstallationStep.scanning) {
      if (_isCameraPaused && !_isProcessingScan) {
        return OutlinedButton.icon(
          onPressed: _scanNextPart,
          icon: const Icon(Icons.qr_code_scanner),
          label: const Text('Scan Next Part'),
        );
      }
      return ElevatedButton.icon(
        onPressed: totalParts == 0 || _isProcessingScan
            ? null
            : _finishScanning,
        icon: const Icon(Icons.check_circle),
        label: const Text('Finish Scanning'),
      );
    }
    final action = switch (_step) {
      _InstallationStep.photo => _captureCustomerPhoto,

      _InstallationStep.details => _completeInstallation,

      _InstallationStep.otp =>
        _generatedOtp == null ? _generateOtp : _verifyOtp,

      _InstallationStep.signature =>
        _signatureBytes == null ? _captureSignature : _completeInstallation,

      _InstallationStep.scanning => null,
    };
    final label = switch (_step) {
      _InstallationStep.photo => 'Take Customer Photo',

      _InstallationStep.details => 'Complete Installation',

      _InstallationStep.otp =>
        _generatedOtp == null ? 'Generate OTP' : 'Verify OTP',

      _InstallationStep.signature =>
        _signatureBytes == null ? 'Capture Signature' : 'Complete Installation',

      _InstallationStep.scanning => '',
    };
    return ElevatedButton.icon(
      onPressed: _isSavingInstallation ? null : action,
      icon: _isSavingInstallation
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : const Icon(Icons.check_circle),
      label: Text(label),
    );
  }
}

enum _InstallationStep { scanning, photo, details, otp, signature }
