import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/device_identity_service.dart';
import '../../services/profile_service.dart';

class FaceEnrollmentScreen extends StatefulWidget {
  const FaceEnrollmentScreen({super.key});

  @override
  State<FaceEnrollmentScreen> createState() => _FaceEnrollmentScreenState();
}

class _FaceEnrollmentScreenState extends State<FaceEnrollmentScreen> {
  final _picker = ImagePicker();
  final _service = ProfileService();
  XFile? _photo;
  bool _saving = false;

  Future<void> _capture() async {
    final photo = await _picker.pickImage(
      source: ImageSource.camera,
      preferredCameraDevice: CameraDevice.front,
      imageQuality: 88,
      maxWidth: 1600,
    );
    if (photo != null && mounted) setState(() => _photo = photo);
  }

  Future<void> _enroll() async {
    if (_photo == null || _saving) return;
    setState(() => _saving = true);
    try {
      final deviceId = await DeviceIdentityService.getOrCreate();
      await _service.enrollFace(photoPath: _photo!.path, deviceId: deviceId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Face photo enrolled and this device is now bound.')),
      );
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
      setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Face Enrollment')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Register your real face',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              const Text(
                'Use the front camera in good light. Keep only one face visible. This photo becomes your attendance reference and this phone is bound to your attendance account.',
              ),
              const SizedBox(height: 24),
              Expanded(
                child: Container(
                  clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    color: const Color(0xFFEAF5FF),
                  ),
                  child: _photo == null
                      ? const Center(child: Icon(Icons.face_retouching_natural, size: 110))
                      : Image.file(File(_photo!.path), fit: BoxFit.cover),
                ),
              ),
              const SizedBox(height: 18),
              OutlinedButton.icon(
                onPressed: _saving ? null : _capture,
                icon: const Icon(Icons.camera_alt_outlined),
                label: Text(_photo == null ? 'Open Front Camera' : 'Retake Photo'),
              ),
              const SizedBox(height: 10),
              FilledButton.icon(
                onPressed: _photo == null || _saving ? null : _enroll,
                icon: _saving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.verified_user_outlined),
                label: Text(_saving ? 'Enrolling...' : 'Enroll Face & Device'),
              ),
              const SizedBox(height: 8),
              const Text(
                'Note: capture alone is not anti-spoof liveness verification. Enrollment remains pending until the verification step is completed.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Color(0xFF687386)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
