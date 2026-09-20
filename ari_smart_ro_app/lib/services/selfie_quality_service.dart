import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

class SelfieQualityResult {
  const SelfieQualityResult._(this.isValid, this.message);

  final bool isValid;
  final String message;

  factory SelfieQualityResult.accepted(String message) =>
      SelfieQualityResult._(true, message);

  factory SelfieQualityResult.invalid(String message) =>
      SelfieQualityResult._(false, message);
}

class SelfieQualityService {
  /// Validates that a front-camera capture is readable while keeping peak
  /// memory usage low enough for older/low-RAM Android phones.
  ///
  /// Face detection is advisory only. Attendance security is still enforced by
  /// live camera capture, server-side office GPS, enrolled-device/admin
  /// override rules, and stored-selfie admin review.
  static Future<SelfieQualityResult> validate(String imagePath) async {
    final file = File(imagePath);
    if (!await file.exists()) {
      return SelfieQualityResult.invalid(
        'Selfie image could not be read. Please retake it.',
      );
    }

    final basicCheck = await _validateCameraImage(file);
    if (basicCheck != null) return basicCheck;

    try {
      List<Face>? faces;
      Object? detectorError;

      try {
        // Process the camera file directly. Do not decode/copy the full image in
        // Dart first: that creates a large temporary bitmap and can make
        // low-memory phones restart the app after the camera closes.
        faces = await _detectFaces(file).timeout(const Duration(seconds: 6));
      } catch (error, stackTrace) {
        detectorError = error;
        debugPrint('SELFIE DETECTION ADVISORY: $error');
        debugPrintStack(stackTrace: stackTrace);
      }

      if (faces == null) {
        debugPrint(
          'SELFIE DETECTOR ADVISORY: detector unavailable ($detectorError); '
          'valid camera image accepted for server review.',
        );
        return SelfieQualityResult.accepted(
          'Selfie captured. Face scan was unavailable on this phone, so it will be reviewed after check-in.',
        );
      }

      if (faces.isEmpty) {
        return SelfieQualityResult.accepted(
          'Selfie captured. Face scan could not confirm a face on this phone; attendance can continue and the selfie will be reviewed.',
        );
      }

      if (faces.length != 1) {
        return SelfieQualityResult.accepted(
          'Selfie captured. The phone detected more than one face-like area; attendance can continue and the selfie will be reviewed.',
        );
      }

      final face = faces.single;
      final box = face.boundingBox;
      final yaw = face.headEulerAngleY?.abs();
      final roll = face.headEulerAngleZ?.abs();
      final leftEye = face.leftEyeOpenProbability;
      final rightEye = face.rightEyeOpenProbability;

      final advisory = <String>[];
      if (box.width < 140 || box.height < 140) {
        advisory.add('face appears small');
      }
      if ((yaw != null && yaw > 22) || (roll != null && roll > 18)) {
        advisory.add('head angle is not straight');
      }
      if ((leftEye != null && leftEye < 0.35) ||
          (rightEye != null && rightEye < 0.35)) {
        advisory.add('eyes may not be fully open');
      }

      if (advisory.isNotEmpty) {
        return SelfieQualityResult.accepted(
          'Selfie captured (${advisory.join(', ')}). Attendance can continue; admin review remains available.',
        );
      }

      return SelfieQualityResult.accepted(
        'Live selfie captured successfully.',
      );
    } catch (error, stackTrace) {
      debugPrint('SELFIE QUALITY ADVISORY ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);
      return SelfieQualityResult.accepted(
        'Selfie captured successfully. Device face analysis was skipped and the selfie will be reviewed after check-in.',
      );
    }
  }

  /// Keep this check intentionally lightweight. Reading and decoding a complete
  /// camera JPEG into a Dart bitmap can temporarily consume tens of megabytes
  /// even when the compressed file itself is small.
  static Future<SelfieQualityResult?> _validateCameraImage(File image) async {
    try {
      final length = await image.length();
      if (length < 12 * 1024) {
        return SelfieQualityResult.invalid(
          'Selfie image quality is too low. Please retake it in good light.',
        );
      }
      return null;
    } catch (error, stackTrace) {
      debugPrint('SELFIE IMAGE CHECK ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);
      return SelfieQualityResult.invalid(
        'Selfie image could not be read. Please retake it.',
      );
    }
  }

  static Future<List<Face>> _detectFaces(File image) async {
    final detector = FaceDetector(
      options: FaceDetectorOptions(
        enableClassification: true,
        enableLandmarks: false,
        performanceMode: FaceDetectorMode.fast,
      ),
    );
    try {
      return await detector.processImage(InputImage.fromFilePath(image.path));
    } finally {
      await detector.close();
    }
  }
}
