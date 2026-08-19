import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/job_model.dart';
import '../../services/job_service.dart';
import '../qr/qr_scanner_screen.dart';
import 'signature_screen.dart';

/// Engineer-facing job workflow screen.
///
/// The screen deliberately uses the existing [JobService] API only.  It
/// returns `true` to My Jobs after a successful completion so the previous
/// screen can refresh its list.
class JobDetailsScreen extends StatefulWidget {
  const JobDetailsScreen({super.key, required this.jobId});

  final int jobId;

  @override
  State<JobDetailsScreen> createState() => _JobDetailsScreenState();
}

class _JobDetailsScreenState extends State<JobDetailsScreen> {
  final JobService _jobService = JobService();
  final ImagePicker _imagePicker = ImagePicker();

  final TextEditingController _inputTdsController = TextEditingController();
  final TextEditingController _outputTdsController = TextEditingController();
  final TextEditingController _referralController = TextEditingController();
  final TextEditingController _remarksController = TextEditingController();
  final TextEditingController _otpController = TextEditingController();

  late Future<JobModel> _jobFuture;
  bool _isSaving = false;
  bool _beforePhotoUploaded = false;
  bool _partsScanned = false;
  bool _installationSaved = false;
  bool _afterPhotoUploaded = false;
  bool _otpVerified = false;
  Uint8List? _signatureBytes;
  Position? _currentPosition;
  String? _generatedOtp;

  @override
  void initState() {
    super.initState();
    _jobFuture = _jobService.getJobDetail(widget.jobId);
    _updateLocation(silent: true);
  }

  @override
  void dispose() {
    _inputTdsController.dispose();
    _outputTdsController.dispose();
    _referralController.dispose();
    _remarksController.dispose();
    _otpController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() => _jobFuture = _jobService.getJobDetail(widget.jobId));
    try {
      await _jobFuture;
    } catch (_) {
      // FutureBuilder displays the loading error; pull-to-refresh should not throw.
    }
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _runAction(Future<void> Function() action) async {
    if (_isSaving) return;
    setState(() => _isSaving = true);
    try {
      await action();
    } catch (_) {
      _showMessage('Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _updateLocation({bool silent = false}) async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        if (!silent) _showMessage('Please enable GPS.');
        return;
      }

      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        if (!silent) _showMessage('Location permission is required.');
        return;
      }

      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );
      await _jobService.uploadGPS(
        widget.jobId,
        position.latitude,
        position.longitude,
      );
      if (mounted) setState(() => _currentPosition = position);
    } catch (_) {
      if (!silent) _showMessage('Unable to update GPS location.');
    }
  }

  Future<void> _changeStatus(String status, String successMessage) async {
    await _runAction(() async {
      final success = await _jobService.changeJobStatus(widget.jobId, status);
      if (!success) {
        _showMessage('Unable to update the job status.');
        return;
      }
      _showMessage(successMessage);
      await _refresh();
    });
  }

  Future<void> _uploadPhoto({required bool before}) async {
    final image = await _imagePicker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );
    if (image == null) return;

    await _runAction(() async {
      final success = await _jobService.uploadPhoto(
        widget.jobId,
        image.path,
        before ? 'Before Photo' : 'After Photo',
      );
      if (!success) {
        _showMessage('Photo upload failed.');
        return;
      }
      if (!mounted) return;
      setState(() {
        if (before) {
          _beforePhotoUploaded = true;
        } else {
          _afterPhotoUploaded = true;
        }
      });
      _showMessage(before ? 'Before photo uploaded.' : 'After photo uploaded.');
    });
  }

  Future<void> _scanParts() async {
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => QRScanScreen(
          jobId: widget.jobId,
        ),
      ),
    );

    if (!mounted) return;

    if (result == true) {
      setState(() {
        _partsScanned = true;
      });

      _showMessage('Installation workflow started.');
    }
  }
  Future<void> _saveInstallation() async {
    final inputTds = int.tryParse(_inputTdsController.text.trim());
    final outputTds = int.tryParse(_outputTdsController.text.trim());
    if (inputTds == null || inputTds < 0) {
      _showMessage('Enter a valid Input TDS.');
      return;
    }
    if (outputTds == null || outputTds < 0) {
      _showMessage('Enter a valid Output TDS.');
      return;
    }

    await _runAction(() async {
      final success = await _jobService.completeInstallation(
        jobId: widget.jobId,
        inputTds: inputTds,
        outputTds: outputTds,
        referral: _referralController.text.trim(),
        remarks: _remarksController.text.trim(),
      );
      if (!success) {
        _showMessage('Unable to save installation details.');
        return;
      }
      if (mounted) setState(() => _installationSaved = true);
      _showMessage('Installation saved.');
    });
  }

  Future<void> _generateOtp() async {
    await _runAction(() async {
      final otp = await _jobService.generateOTP(widget.jobId);
      if (otp == null) {
        _showMessage('Unable to generate OTP.');
        return;
      }
      if (mounted) setState(() => _generatedOtp = otp.toString());
      _showMessage('OTP generated. Share it with the customer.');
    });
  }

  Future<void> _verifyOtp() async {
    final otp = _otpController.text.trim();
    if (otp.isEmpty) {
      _showMessage('Enter the customer OTP.');
      return;
    }
    await _runAction(() async {
      final success = await _jobService.verifyOTP(widget.jobId, otp);
      if (!success) {
        _showMessage('Invalid OTP.');
        return;
      }
      if (mounted) setState(() => _otpVerified = true);
      _showMessage('OTP verified.');
    });
  }

  Future<void> _captureSignature() async {
    final signature = await Navigator.of(context).push<Uint8List>(
      MaterialPageRoute<Uint8List>(builder: (_) => const SignatureScreen()),
    );
    if (signature == null || !mounted) return;
    setState(() => _signatureBytes = signature);
    _showMessage('Customer signature captured.');
  }

  Future<void> _completeJob() async {
    if (!_installationSaved ||
        !_afterPhotoUploaded ||
        !_otpVerified ||
        _signatureBytes == null) {
      _showMessage('Complete all required steps before completing the job.');
      return;
    }
    final customerName = await _askCustomerName();
    if (customerName == null || customerName.isEmpty) return;

    await _runAction(() async {
      final signatureUploaded = await _jobService.uploadSignature(
        widget.jobId,
        _signatureBytes!,
        customerName,
      );
      if (!signatureUploaded) {
        _showMessage('Signature upload failed.');
        return;
      }
      final completed = await _jobService.changeJobStatus(
        widget.jobId,
        'COMPLETED',
      );
      if (!completed) {
        _showMessage('Unable to complete the job.');
        return;
      }
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          icon: const Icon(Icons.check_circle, color: Colors.green, size: 48),
          title: const Text('Job completed'),
          content: const Text('All job details have been saved successfully.'),
          actions: [
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Back to My Jobs'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.of(context).pop(true);
    });
  }

  Future<String?> _askCustomerName() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Customer name'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(labelText: 'Name of signatory'),
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

  Future<void> _callCustomer(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (!await launchUrl(uri)) _showMessage('Unable to open the phone app.');
  }

  Future<void> _navigateToCustomer(JobModel job) async {
    if (job.latitude == 0 || job.longitude == 0) {
      _showMessage('Customer location is not available.');
      return;
    }
    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=${job.latitude},${job.longitude}&travelmode=driving',
    );
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _showMessage('Unable to open Maps.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Job Details'), centerTitle: true),
      body: FutureBuilder<JobModel>(
        future: _jobFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return _ErrorView(onRetry: _refresh);
          }
          final job = snapshot.data!;
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _JobHeader(job: job),
                const SizedBox(height: 12),
                _SectionCard(
                  title: 'Customer details',
                  child: Column(
                    children: [
                      _InfoRow('Customer', job.customerName),
                      _InfoRow('Phone', job.phone),
                      _InfoRow('Address', job.address),
                      _InfoRow('Area / City', '${job.area}, ${job.city}'),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _callCustomer(job.phone),
                              icon: const Icon(Icons.call),
                              label: const Text('Call'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _navigateToCustomer(job),
                              icon: const Icon(Icons.navigation),
                              label: const Text('Navigate'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _LocationCard(
                  position: _currentPosition,
                  onRefresh: () => _updateLocation(),
                ),
                const SizedBox(height: 16),
                _WorkflowProgress(
                  status: job.status,
                  beforePhoto: _beforePhotoUploaded,
                  partsScanned: _partsScanned,
                  installationSaved: _installationSaved,
                  afterPhoto: _afterPhotoUploaded,
                  otpVerified: _otpVerified,
                  signatureCaptured: _signatureBytes != null,
                ),
                const SizedBox(height: 16),
                _buildActionArea(job.status),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildActionArea(String status) {
    final currentStatus = status.trim().toUpperCase();
    if (currentStatus == 'ASSIGNED') {
      return _PrimaryAction(
        label: 'Accept Job',
        icon: Icons.assignment_turned_in,
        loading: _isSaving,
        onPressed: () => _changeStatus('ACCEPTED', 'Job accepted.'),
      );
    }
    if (currentStatus == 'ACCEPTED') {
      return _PrimaryAction(
        label: 'Start Journey',
        icon: Icons.directions_car,
        loading: _isSaving,
        onPressed: () => _changeStatus('ON_THE_WAY', 'Journey started.'),
      );
    }
    if (currentStatus == 'ON_THE_WAY') {
      return _PrimaryAction(
        label: 'Mark Arrived',
        icon: Icons.location_on,
        loading: _isSaving,
        onPressed: () => _changeStatus('ARRIVED', 'Arrival recorded.'),
      );
    }
    if (currentStatus == 'ARRIVED') {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _PrimaryAction(
            label: _beforePhotoUploaded
                ? 'Before Photo Uploaded'
                : 'Upload Before Photo',
            icon: Icons.camera_alt,
            loading: _isSaving,
            onPressed: _beforePhotoUploaded
                ? null
                : () => _uploadPhoto(before: true),
          ),
          const SizedBox(height: 12),
          _PrimaryAction(
            label: 'Start Work',
            icon: Icons.build,
            loading: _isSaving,
            onPressed: _beforePhotoUploaded
                ? () => _changeStatus('IN_PROGRESS', 'Work started.')
                : null,
          ),
        ],
      );
    }
    if (currentStatus == 'IN_PROGRESS') return _buildInProgressActions();
    if (currentStatus == 'COMPLETED') return const _CompletedCard();
    return _ErrorView(
      onRetry: _refresh,
      message: 'Unknown job status: $status',
    );
  }

  Widget _buildInProgressActions() {
    Widget action;
    if (!_partsScanned) {
      action = _PrimaryAction(
        label: 'Scan QR Parts',
        icon: Icons.qr_code_scanner,
        loading: _isSaving,
        onPressed: _scanParts,
      );
    } else if (!_installationSaved) {
      action = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _InstallationForm(
            inputTdsController: _inputTdsController,
            outputTdsController: _outputTdsController,
            referralController: _referralController,
            remarksController: _remarksController,
          ),
          const SizedBox(height: 12),
          _PrimaryAction(
            label: 'Save Installation',
            icon: Icons.save,
            loading: _isSaving,
            onPressed: _saveInstallation,
          ),
        ],
      );
    } else if (!_afterPhotoUploaded) {
      action = _PrimaryAction(
        label: 'Upload After Photo',
        icon: Icons.camera_alt,
        loading: _isSaving,
        onPressed: () => _uploadPhoto(before: false),
      );
    } else if (_generatedOtp == null) {
      action = _PrimaryAction(
        label: 'Generate OTP',
        icon: Icons.password,
        loading: _isSaving,
        onPressed: _generateOtp,
      );
    } else if (!_otpVerified) {
      action = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            color: Theme.of(context).colorScheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Text(
                'OTP: $_generatedOtp',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _otpController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Customer OTP',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          _PrimaryAction(
            label: 'Verify OTP',
            icon: Icons.verified_user,
            loading: _isSaving,
            onPressed: _verifyOtp,
          ),
        ],
      );
    } else if (_signatureBytes == null) {
      action = _PrimaryAction(
        label: 'Customer Signature',
        icon: Icons.draw,
        loading: _isSaving,
        onPressed: _captureSignature,
      );
    } else {
      action = _PrimaryAction(
        label: 'Complete Job',
        icon: Icons.check_circle,
        loading: _isSaving,
        onPressed: _completeJob,
      );
    }
    return _SectionCard(title: 'Next step', child: action);
  }
}

class _JobHeader extends StatelessWidget {
  const _JobHeader({required this.job});
  final JobModel job;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            job.customerName,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              Chip(label: Text('Job #${job.jobId}')),
              Chip(label: Text(job.status)),
              Chip(label: Text('Priority: ${job.priority}')),
            ],
          ),
          const SizedBox(height: 8),
          Text('Type: ${job.jobType}  •  Asset: ${job.assetId}'),
          Text('Engineer: ${job.engineerName}'),
        ],
      ),
    ),
  );
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});
  final String title;
  final Widget child;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          child,
        ],
      ),
    ),
  );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.label, this.value);
  final String label;
  final Object? value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Text('$label: ${value ?? '-'}'),
  );
}

class _LocationCard extends StatelessWidget {
  const _LocationCard({required this.position, required this.onRefresh});
  final Position? position;
  final VoidCallback onRefresh;
  @override
  Widget build(BuildContext context) => _SectionCard(
    title: 'Live GPS',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          position == null
              ? 'Location not available yet.'
              : '${position!.latitude.toStringAsFixed(6)}, ${position!.longitude.toStringAsFixed(6)}',
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: onRefresh,
          icon: const Icon(Icons.my_location),
          label: const Text('Refresh GPS'),
        ),
      ],
    ),
  );
}

class _WorkflowProgress extends StatelessWidget {
  const _WorkflowProgress({
    required this.status,
    required this.beforePhoto,
    required this.partsScanned,
    required this.installationSaved,
    required this.afterPhoto,
    required this.otpVerified,
    required this.signatureCaptured,
  });
  final String status;
  final bool beforePhoto;
  final bool partsScanned;
  final bool installationSaved;
  final bool afterPhoto;
  final bool otpVerified;
  final bool signatureCaptured;
  @override
  Widget build(BuildContext context) {
    final normalized = status.trim().toUpperCase();
    final arrived = const {
      'ARRIVED',
      'IN_PROGRESS',
      'COMPLETED',
    }.contains(normalized);
    final started = const {'IN_PROGRESS', 'COMPLETED'}.contains(normalized);
    final items = <(String, bool)>[
      ('Accept job', normalized != 'ASSIGNED'),
      ('Start journey', !{'ASSIGNED', 'ACCEPTED'}.contains(normalized)),
      ('Arrived', arrived),
      ('Before photo', beforePhoto),
      ('Start work', started),
      ('Scan parts', partsScanned),
      ('Save installation', installationSaved),
      ('After photo', afterPhoto),
      ('Verify OTP', otpVerified),
      ('Signature', signatureCaptured),
      ('Complete job', normalized == 'COMPLETED'),
    ];
    return _SectionCard(
      title: 'Progress',
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: items
            .map(
              (item) => Chip(
                avatar: Icon(
                  item.$2 ? Icons.check_circle : Icons.radio_button_unchecked,
                  color: item.$2 ? Colors.green : null,
                  size: 18,
                ),
                label: Text(item.$1),
              ),
            )
            .toList(),
      ),
    );
  }
}

class _InstallationForm extends StatelessWidget {
  const _InstallationForm({
    required this.inputTdsController,
    required this.outputTdsController,
    required this.referralController,
    required this.remarksController,
  });
  final TextEditingController inputTdsController;
  final TextEditingController outputTdsController;
  final TextEditingController referralController;
  final TextEditingController remarksController;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      TextField(
        controller: inputTdsController,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(
          labelText: 'Input TDS *',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 12),
      TextField(
        controller: outputTdsController,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(
          labelText: 'Output TDS *',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 12),
      TextField(
        controller: referralController,
        decoration: const InputDecoration(
          labelText: 'Referral',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 12),
      TextField(
        controller: remarksController,
        minLines: 3,
        maxLines: 5,
        decoration: const InputDecoration(
          labelText: 'Remarks',
          border: OutlineInputBorder(),
        ),
      ),
    ],
  );
}

class _PrimaryAction extends StatelessWidget {
  const _PrimaryAction({
    required this.label,
    required this.icon,
    required this.loading,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final bool loading;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: loading ? null : onPressed,
            icon: loading
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Icon(icon),
            label: Text(label),
          ),
        ),
      ),
    );
  }
}
class _ErrorView extends StatelessWidget {
  const _ErrorView({
    required this.onRetry,
    this.message = 'Unable to load this job.',
  });
  final VoidCallback onRetry;
  final String message;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          FilledButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    ),
  );
}

class _CompletedCard extends StatelessWidget {
  const _CompletedCard();
  @override
  Widget build(BuildContext context) => const Card(
    child: Padding(
      padding: EdgeInsets.all(20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle, color: Colors.green),
          SizedBox(width: 8),
          Text('This job is completed.'),
        ],
      ),
    ),
  );
}
