import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import '../qr/qr_scanner_screen.dart';
import 'dart:typed_data';
import 'package:ari_smart_ro_app/screens/jobs/signature_screen.dart';

import '../../models/job_model.dart';
import '../../services/job_service.dart';



class JobDetailsScreen extends StatefulWidget {
  final int jobId;

  const JobDetailsScreen({super.key, required this.jobId});

  @override
  State<JobDetailsScreen> createState() => _JobDetailsScreenState();
}

class _JobDetailsScreenState extends State<JobDetailsScreen> {
  final JobService _jobService = JobService();
  final ImagePicker _picker = ImagePicker();

  late Future<JobModel> _jobFuture;
  bool _isSaving = false;
  bool _beforePhotoUploaded = false;

  Uint8List? _signatureBytes;

  Position? _currentPosition;

  @override
  void initState() {
    super.initState();
    _jobFuture = _jobService.getJobDetail(widget.jobId);
    _startLocationTracking();
  }

  Future<void> _startLocationTracking() async {
    try {
      print("GPS START");

      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      print("Service Enabled : $serviceEnabled");

      if (!serviceEnabled) {
        _showMessage("Please enable location");
        return;
      }

      LocationPermission permission =
          await Geolocator.checkPermission();

      print("Permission : $permission");

      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        print("Permission After Request : $permission");
      }

      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      print("Latitude : ${position.latitude}");
      print("Longitude : ${position.longitude}");

      bool ok = await _jobService.uploadGPS(
        widget.jobId,
        position.latitude,
        position.longitude,
      );

      print("UPLOAD RESULT : $ok");

      if (!mounted) return;

      setState(() {
        _currentPosition = position;
      });
    } catch (e, s) {
      print("GPS ERROR : $e");
      print(s);

      if (!mounted) return;

      _showMessage("Unable to update your GPS location.");
    }
  }

  Future<void> _uploadBeforePhoto() async {
    final image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );
    if (image == null) return;

    await _runAction(() async {
      final success = await _jobService.uploadPhoto(
        widget.jobId,
        image.path,
        'Before Photo',
      );
      if (success) {

        setState(() {
          _beforePhotoUploaded = true;
        });

        _refresh();

        _showMessage("Before Photo Uploaded");

      } else {

        _showMessage("Photo Upload Failed");

      }
    });
  }

  Future<void> _captureSignature() async {

    final result = await Navigator.push<Uint8List>(
      context,
      MaterialPageRoute(
        builder: (_) => const SignatureScreen(),
      ),
    );

    if (result != null) {

      setState(() {
        _signatureBytes = result;
      });

      _showMessage("Signature captured");
    }
  }

  Future<void> _uploadAfterPhoto() async {

    final XFile? image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );

    if (image == null) return;

    await _runAction(() async {

      final success = await _jobService.uploadPhoto(
        widget.jobId,
        image.path,
        "After Photo",
      );

      if (success) {

        _showMessage("After Photo Uploaded");

      } else {

        _showMessage("Photo Upload Failed");

      }

    });

  }
  Future<void> _changeStatus(String status, String successMessage) async {
    await _runAction(() async {
      final success = await _jobService.changeJobStatus(widget.jobId, status);
      if (success) {
        _showMessage(successMessage);
        _refresh();
      } else {
        _showMessage('Could not update the job status.');
      }
    });
  }

  Future<void> _completeJob() async {

    if (_signatureBytes == null) {
      _showMessage("Please capture customer signature first.");
      return;
    }

    final controller = TextEditingController();

    final customerName = await showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text("Customer Name"),
          content: TextField(
            controller: controller,
            decoration: const InputDecoration(
              hintText: "Enter customer name",
            ),
          ),
          actions: [

            TextButton(
              onPressed: () {
                Navigator.pop(context);
              },
              child: const Text("Cancel"),
            ),

            ElevatedButton(
              onPressed: () {
                Navigator.pop(
                  context,
                  controller.text.trim(),
                );
              },
              child: const Text("OK"),
            ),

          ],
        );
      },
    );

    if (customerName == null || customerName.isEmpty) {
      return;
    }

    await _runAction(() async {

      final uploaded =
          await _jobService.uploadSignature(
        widget.jobId,
        _signatureBytes!,
        customerName,
      );

      if (!uploaded) {
        _showMessage("Signature upload failed.");
        return;
      }

      final completed =
          await _jobService.changeJobStatus(
        widget.jobId,
        "COMPLETED",
      );

      if (completed) {

        _showMessage("Job Completed Successfully.");

        _refresh();

      } else {

        _showMessage("Unable to complete job.");

      }

    });

  }

  Future<void> _runAction(Future<void> Function() action) async {
    if (_isSaving) return;

    setState(() => _isSaving = true);

    try {
      await action();
    } catch (e, s) {
      print("ERROR : $e");
      print(s);

      _showMessage(e.toString());
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  void _refresh() {
    if (!mounted) return;

    setState(() {
      _jobFuture = _jobService.getJobDetail(widget.jobId);
    });
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Job Details'), centerTitle: true),
      body: FutureBuilder<JobModel>(
        future: _jobFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return _ErrorView(onRetry: _refresh);
          }

          final job = snapshot.data!;
          return RefreshIndicator(
            onRefresh: () async => _refresh(),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _StatusCard(job: job),
                const SizedBox(height: 12),
                _DetailsCard(
                  title: 'Customer Details',
                  children: [
                    _DetailRow('Customer', job.customerName),
                    _DetailRow('Phone', job.phone),
                    _DetailRow('Address', job.address),
                    _DetailRow('Area / City', '${job.area}, ${job.city}'),
                  ],
                ),
                const SizedBox(height: 12),
                _DetailsCard(
                  title: 'Job Details',
                  children: [
                    _DetailRow('Job ID', job.jobId),
                    _DetailRow('Type', job.jobType),
                    _DetailRow('Priority', job.priority),
                    _DetailRow('Asset ID', job.assetId),
                    _DetailRow('Engineer', job.engineerName),
                  ],
                ),
                const SizedBox(height: 12),
                _LocationCard(position: _currentPosition, onRefresh: _startLocationTracking),
                const SizedBox(height: 20),
                ..._actionButtons(job.status),
              ],
            ),
          );
        },
      ),
    );
  }

  List<Widget> _actionButtons(String status) {
    final normalized = status.trim().toUpperCase();
    if (normalized == 'ACCEPTED') {
      return [_ActionButton(label: 'Start Journey', icon: Icons.directions_car, loading: _isSaving, onPressed: () => _changeStatus('ON_THE_WAY', 'Status updated: On the way.'))];
    }
    if (normalized == 'ON_THE_WAY') {
      return [_ActionButton(label: 'Mark as Arrived', icon: Icons.location_on, loading: _isSaving, onPressed: () => _changeStatus('ARRIVED', 'Status updated: Arrived.'))];
    }
    if (normalized == 'ARRIVED') {
      return [
        OutlinedButton.icon(
          onPressed: (_isSaving || _beforePhotoUploaded)
              ? null
              : _uploadBeforePhoto,
          icon: const Icon(Icons.camera_alt),
          label: Text(
            _beforePhotoUploaded
                ? "Before Photo Uploaded ✓"
                : "Upload Before Photo",
          ),
        ),
        const SizedBox(height: 10),
        _ActionButton(label: 'Start Work', icon: Icons.build, loading: _isSaving, onPressed: _beforePhotoUploaded ? () => _changeStatus('IN_PROGRESS', 'Work started.') : null),
      ];
    }
    if (normalized == 'IN_PROGRESS') {
      return [

        _ActionButton(
          label: "Start Installation",
          icon: Icons.qr_code_scanner,
          loading: _isSaving,
          onPressed: () async {
            await Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => QRScanScreen(
                  jobId: widget.jobId,
                ),
              ),
            );
          },
        ),

        const SizedBox(height: 12),

        OutlinedButton.icon(
          onPressed: _isSaving ? null : _uploadAfterPhoto,
          icon: const Icon(Icons.camera_alt),
          label: const Text("Upload After Photo"),
        ),

        const SizedBox(height: 12),

        _ActionButton(
          label: "Customer Signature",
          icon: Icons.draw,
          loading: _isSaving,
          onPressed: _captureSignature,
        ),

        const SizedBox(height: 12),

        _ActionButton(
          label: "Complete Job",
          icon: Icons.check_circle,
          loading: _isSaving,
          onPressed: _completeJob,
        ),

      ];
    }
    return [const Center(child: Text('No actions are available for this job.'))];
  }
}

class _StatusCard extends StatelessWidget {
  final JobModel job;
  const _StatusCard({required this.job});
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(16), child: Row(children: [const Icon(Icons.assignment_outlined, size: 32), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(job.jobId, style: Theme.of(context).textTheme.titleLarge), const SizedBox(height: 4), Text('Status: ${job.status}')])), Chip(label: Text(job.priority))])));
}

class _DetailsCard extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _DetailsCard({
    required this.title,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const Divider(),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  const _DetailRow(this.label, this.value);
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [SizedBox(width: 100, child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600))), Expanded(child: Text(value.isEmpty ? '-' : value))]));
}

class _LocationCard extends StatelessWidget {
  final Position? position;
  final VoidCallback onRefresh;
  const _LocationCard({required this.position, required this.onRefresh});
  @override
  Widget build(BuildContext context) => Card(child: ListTile(leading: const Icon(Icons.my_location), title: const Text('GPS Location'), subtitle: Text(position == null ? 'Getting current location...' : '${position!.latitude.toStringAsFixed(6)}, ${position!.longitude.toStringAsFixed(6)}'), trailing: IconButton(icon: const Icon(Icons.refresh), onPressed: onRefresh)));
}

class _ActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool loading;
  final VoidCallback? onPressed;
  const _ActionButton({required this.label, required this.icon, required this.loading, required this.onPressed});
  @override
  Widget build(BuildContext context) => SizedBox(width: double.infinity, child: ElevatedButton.icon(onPressed: loading ? null : onPressed, icon: loading ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : Icon(icon), label: Text(label)));
}

class _ErrorView extends StatelessWidget {
  final VoidCallback onRetry;
  const _ErrorView({required this.onRetry});
  @override
  Widget build(BuildContext context) => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [const Text('Unable to load job details.'), const SizedBox(height: 12), ElevatedButton(onPressed: onRetry, child: const Text('Retry'))]));
}
