import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/device_capability_service.dart';
import '../../services/device_identity_service.dart';
import '../../services/profile_service.dart';
import '../../services/selfie_quality_service.dart';

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
  bool _capturing = false;
  bool? _lowMemoryDevice;

  @override
  void initState() {
    super.initState();
    _loadDeviceCapability();
  }

  Future<void> _loadDeviceCapability() async {
    final lowMemory = await DeviceCapabilityService.isLowMemoryDevice();
    if (!mounted) return;
    setState(() => _lowMemoryDevice = lowMemory);
  }

  Future<void> _capture() async {
    if (_capturing || _saving) return;
    setState(() => _capturing = true);

    XFile? newPhoto;
    try {
      final lowMemory = _lowMemoryDevice ??
          await DeviceCapabilityService.isLowMemoryDevice();
      if (mounted && _lowMemoryDevice != lowMemory) {
        setState(() => _lowMemoryDevice = lowMemory);
      }

      newPhoto = await _picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        // Redmi 8A-class devices can be killed while the camera returns a
        // large JPEG and Flutter immediately decodes it. Keep the capture
        // deliberately smaller there; the server only needs a clear face
        // reference, not a full-resolution photograph.
        imageQuality: lowMemory ? 72 : 88,
        maxWidth: lowMemory ? 960 : 1600,
        maxHeight: lowMemory ? 1280 : 2200,
      );
      if (newPhoto == null || !mounted) return;

      final result = await SelfieQualityService.validate(newPhoto.path);
      if (!mounted) {
        await _deleteCapture(newPhoto);
        return;
      }
      if (!result.isValid) {
        await _deleteCapture(newPhoto);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result.message)),
        );
        return;
      }

      final oldPhoto = _photo;
      setState(() => _photo = newPhoto);
      if (oldPhoto != null && oldPhoto.path != newPhoto.path) {
        await _deleteCapture(oldPhoto);
      }
    } catch (error) {
      if (newPhoto != null && newPhoto.path != _photo?.path) {
        await _deleteCapture(newPhoto);
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Camera could not finish the selfie safely. Close other apps and try again.',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _capturing = false);
    }
  }

  Future<void> _deleteCapture(XFile capture) async {
    try {
      final file = File(capture.path);
      if (await file.exists()) await file.delete();
    } catch (_) {
      // ImagePicker normally uses app cache. Cleanup is best-effort only and
      // must never turn a recoverable camera failure into an app failure.
    }
  }

  Future<void> _enroll() async {
    final photo = _photo;
    if (photo == null || _saving || _capturing) return;
    setState(() => _saving = true);
    try {
      final deviceId = await DeviceIdentityService.getOrCreate();
      await _service.enrollFace(photoPath: photo.path, deviceId: deviceId);
      await _deleteCapture(photo);
      _photo = null;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Face photo enrolled and this device is now bound.'),
        ),
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
  void dispose() {
    final photo = _photo;
    if (photo != null) {
      // Do not await from dispose; this is cache cleanup only.
      _deleteCapture(photo);
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final lowMemory = _lowMemoryDevice == true;
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
              if (lowMemory) ...[
                const SizedBox(height: 8),
                const Text(
                  'Low-memory safe camera mode is active for this phone.',
                  style: TextStyle(fontSize: 12, color: Color(0xFF687386)),
                ),
              ],
              const SizedBox(height: 24),
              Expanded(
                child: Container(
                  clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(24),
                    color: const Color(0xFFEAF5FF),
                  ),
                  child: _photo == null
                      ? const Center(
                          child: Icon(Icons.face_retouching_natural, size: 110),
                        )
                      : Image.file(
                          File(_photo!.path),
                          fit: BoxFit.cover,
                          // Avoid decoding the camera JPEG at its full native
                          // size just to render an on-screen preview.
                          cacheWidth: lowMemory ? 720 : 1200,
                        ),
                ),
              ),
              const SizedBox(height: 18),
              OutlinedButton.icon(
                onPressed: _saving || _capturing ? null : _capture,
                icon: _capturing
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.camera_alt_outlined),
                label: Text(
                  _capturing
                      ? 'Opening Camera...'
                      : _photo == null
                          ? 'Open Front Camera'
                          : 'Retake Photo',
                ),
              ),
              const SizedBox(height: 10),
              FilledButton.icon(
                onPressed: _photo == null || _saving || _capturing
                    ? null
                    : _enroll,
                icon: _saving
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
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
