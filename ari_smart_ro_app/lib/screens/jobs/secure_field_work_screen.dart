import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../models/job_model.dart';
import '../../services/field_work_security_service.dart';
import '../../services/job_service.dart';
import 'field_work_part_scanner_screen.dart';
import 'signature_screen.dart';

class SecureFieldWorkScreen extends StatefulWidget {
  const SecureFieldWorkScreen({super.key, required this.jobId});

  final int jobId;

  @override
  State<SecureFieldWorkScreen> createState() => _SecureFieldWorkScreenState();
}

class _SecureFieldWorkScreenState extends State<SecureFieldWorkScreen> {
  final JobService _jobs = JobService();
  final FieldWorkSecurityService _security = FieldWorkSecurityService();
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _otp = TextEditingController();

  late Future<JobModel> _future;
  bool _busy = false;
  bool _otpSent = false;

  @override
  void initState() {
    super.initState();
    _future = _jobs.getJobDetail(widget.jobId);
  }

  @override
  void dispose() {
    _otp.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() => _future = _jobs.getJobDetail(widget.jobId));
    await _future;
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _run(Future<bool> Function() action, String success) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final ok = await action();
      if (!ok) {
        _message('Action blocked. Complete the required proof step first.');
        return;
      }
      _message(success);
      await _refresh();
    } catch (_) {
      _message('Unable to complete this action. Please try again.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _changeStatus(String status, String message) {
    return _run(() => _jobs.changeJobStatus(widget.jobId, status), message);
  }

  Future<void> _uploadPhoto(bool before) async {
    final image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 75,
    );
    if (image == null) return;
    await _run(
      () => _jobs.uploadPhoto(
        widget.jobId,
        image.path,
        before ? 'Before Photo' : 'After Photo',
      ),
      before ? 'Before photo saved.' : 'After photo saved.',
    );
  }

  Future<void> _scanParts() async {
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => FieldWorkPartScannerScreen(jobId: widget.jobId),
      ),
    );
    if (result == true) {
      _message('Used parts recorded against this job.');
      await _refresh();
    }
  }

  Future<void> _declareNoParts() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm no part used'),
        content: const Text(
          'Confirm only if no replacement part was installed at this customer. '
          'This declaration is saved in the audit trail.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Confirm No Part Used'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await _run(
      () => _security.declareNoParts(widget.jobId),
      'No-parts declaration saved in audit trail.',
    );
  }

  Future<void> _sendOtp() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final ok = await _jobs.generateOTP(widget.jobId);
      if (!ok) {
        _message('Unable to send customer OTP.');
        return;
      }
      if (mounted) setState(() => _otpSent = true);
      _message('OTP sent to customer.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verifyOtp() async {
    final value = _otp.text.trim();
    if (value.length != 6) {
      _message('Enter the 6-digit customer OTP.');
      return;
    }
    await _run(
      () => _jobs.verifyOTP(widget.jobId, value),
      'Customer OTP verified.',
    );
  }

  Future<String?> _askCustomerName() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Customer confirmation'),
        content: TextField(
          controller: controller,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Customer / signatory name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Continue'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<void> _captureAndUploadSignature() async {
    final Uint8List? bytes = await Navigator.of(context).push<Uint8List>(
      MaterialPageRoute<Uint8List>(builder: (_) => const SignatureScreen()),
    );
    if (bytes == null || !mounted) return;
    final customerName = await _askCustomerName();
    if (customerName == null || customerName.isEmpty) return;
    await _run(
      () => _jobs.uploadSignature(widget.jobId, bytes, customerName),
      'Customer signature saved.',
    );
  }

  Widget _button(String label, IconData icon, VoidCallback? onPressed) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: _busy ? null : onPressed,
          icon: _busy
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Icon(icon),
          label: Text(label),
        ),
      ),
    );
  }

  Widget _proofStatus(JobModel job) {
    final rows = <String, bool>{
      'Before photo': job.beforePhotoUploaded,
      'Parts decision': job.partsDecision != 'PENDING',
      'After photo': job.afterPhotoUploaded,
      'Customer OTP': job.otpVerified,
      'Customer signature': job.signatureUploaded,
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Fraud-proof completion evidence', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 10),
            ...rows.entries.map(
              (row) => ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                leading: Icon(
                  row.value ? Icons.verified : Icons.radio_button_unchecked,
                  color: row.value ? Colors.green : null,
                ),
                title: Text(row.key),
              ),
            ),
            if (job.partsDecision == 'NO_PARTS')
              const Text('Parts: No replacement part declared (audited).'),
            if (job.partsDecision == 'USED')
              const Text('Parts: Used parts scanned and linked to inventory.'),
          ],
        ),
      ),
    );
  }

  Widget _actions(JobModel job) {
    final status = job.status.toUpperCase();
    if (status == 'ASSIGNED') {
      return _button('Accept Job', Icons.assignment_turned_in, () {
        _changeStatus('ACCEPTED', 'Job accepted.');
      });
    }
    if (status == 'ACCEPTED') {
      return _button('Start Journey', Icons.directions_car, () {
        _changeStatus('ON_THE_WAY', 'Journey started.');
      });
    }
    if (status == 'ON_THE_WAY') {
      return _button('Mark Arrived', Icons.location_on, () {
        _changeStatus('ARRIVED', 'Arrival recorded.');
      });
    }
    if (status == 'ARRIVED') {
      if (!job.beforePhotoUploaded) {
        return _button('Capture Before Photo', Icons.camera_alt, () {
          _uploadPhoto(true);
        });
      }
      return _button('Start Work', Icons.build, () {
        _changeStatus('IN_PROGRESS', 'Work started.');
      });
    }
    if (status == 'IN_PROGRESS') {
      if (job.partsDecision == 'PENDING') {
        return Column(
          children: [
            _button('Scan Used Parts', Icons.qr_code_scanner, _scanParts),
            _button('No Part Used', Icons.inventory_2_outlined, _declareNoParts),
          ],
        );
      }
      if (!job.afterPhotoUploaded) {
        return _button('Capture After Photo', Icons.camera_alt, () {
          _uploadPhoto(false);
        });
      }
      if (!job.otpVerified) {
        if (!_otpSent) {
          return _button('Send Customer OTP', Icons.password, _sendOtp);
        }
        return Column(
          children: [
            TextField(
              controller: _otp,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: '6-digit customer OTP',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            _button('Verify Customer OTP', Icons.verified_user, _verifyOtp),
          ],
        );
      }
      if (!job.signatureUploaded) {
        return _button('Customer Signature', Icons.draw, _captureAndUploadSignature);
      }
      return _button('Complete Secure Job', Icons.check_circle, () {
        _changeStatus('COMPLETED', 'Job completed with verified evidence.');
      });
    }
    if (status == 'COMPLETED') {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(18),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.verified, color: Colors.green),
              SizedBox(width: 8),
              Text('Secure workflow completed'),
            ],
          ),
        ),
      );
    }
    return Text('Status: ${job.status}');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Secure Field Work')),
      body: FutureBuilder<JobModel>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: FilledButton(
                onPressed: _refresh,
                child: const Text('Retry'),
              ),
            );
          }
          final job = snapshot.data!;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(job.customerName, style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 6),
                        Text('${job.jobType} • ${job.jobId}'),
                        Text('Status: ${job.status}'),
                        Text('Asset: ${job.assetId}'),
                        if (job.remarks.isNotEmpty) Text('Work: ${job.remarks}'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                _proofStatus(job),
                const SizedBox(height: 12),
                _actions(job),
              ],
            ),
          );
        },
      ),
    );
  }
}
