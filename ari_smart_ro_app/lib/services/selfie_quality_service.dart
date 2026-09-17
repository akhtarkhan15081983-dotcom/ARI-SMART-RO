import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:image/image.dart' as img;

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
  /// Validates that the front-camera capture is a real, readable image.
  ///
  /// Face detection is intentionally advisory only. Some Android vendor builds
  /// return no face or throw a platform error for otherwise valid camera JPEGs.
  /// Attendance security is still enforced by live camera capture, server-side
  /// office GPS, enrolled-device/admin override rules, and stored-selfie admin
  /// review. This keeps attendance usable across supported Android phones
  /// without trusting a device-specific ML Kit result as a hard gate.
  static Future<SelfieQualityResult> validate(String imagePath) async {
    final file = File(imagePath);
    if (!await file.exists()) {
      return SelfieQualityResult.invalid(
        'Selfie image could not be read. Please retake it.',
      );
    }

    final basicCheck = await _validateCameraImage(file);
    if (basicCheck != null) return basicCheck;

    File? normalizedFile;
    try {
      try {
        normalizedFile = await _normalizeForDetection(file);
      } catch (error, stackTrace) {
        debugPrint('SELFIE NORMALIZATION ADVISORY: $error');
        debugPrintStack(stackTrace: stackTrace);
      }

      List<Face>? faces;
      Object? lastError;
      final candidates = <File>[
        if (normalizedFile != null) normalizedFile,
        file,
      ];

      for (final candidate in candidates) {
        try {
          faces = await _detectFaces(candidate).timeout(
            const Duration(seconds: 8),
          );
          break;
        } catch (error, stackTrace) {
          lastError = error;
          debugPrint('SELFIE DETECTION ADVISORY (${candidate.path}): $error');
          debugPrintStack(stackTrace: stackTrace);
        }
      }

      if (faces == null) {
        debugPrint(
          'SELFIE DETECTOR ADVISORY: detector unavailable ($lastError); '
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
      // The basic image check already proved this is a usable camera capture.
      // Any later detector/platform failure must not lock an employee out.
      debugPrint('SELFIE QUALITY ADVISORY ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);
      return SelfieQualityResult.accepted(
        'Selfie captured successfully. Device face analysis was skipped and the selfie will be reviewed after check-in.',
      );
    } finally {
      if (normalizedFile != null && normalizedFile.path != file.path) {
        try {
          await normalizedFile.delete();
        } catch (_) {
          // Temporary validation images are safe to leave for OS cleanup.
        }
      }
    }
  }

  /// Returns an invalid result only for problems that are independent of ML Kit
  /// and therefore consistent across Android vendors.
  static Future<SelfieQualityResult?> _validateCameraImage(File image) async {
    try {
      final bytes = await image.readAsBytes();
      if (bytes.length < 12 * 1024) {
        return SelfieQualityResult.invalid(
          'Selfie image quality is too low. Please retake it in good light.',
        );
      }

      final decoded = img.decodeImage(bytes);
      if (decoded == null) {
        return SelfieQualityResult.invalid(
          'Selfie image could not be decoded. Please retake it.',
        );
      }

      final normalized = img.bakeOrientation(decoded);
      final shortSide = normalized.width < normalized.height
          ? normalized.width
          : normalized.height;
      final longSide = normalized.width > normalized.height
          ? normalized.width
          : normalized.height;

      if (shortSide < 240 || longSide < 320) {
        return SelfieQualityResult.invalid(
          'Selfie image is too small. Please retake it with the front camera.',
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

  static Future<File> _normalizeForDetection(File source) async {
    final decoded = img.decodeImage(await source.readAsBytes());
    if (decoded == null) {
      throw const FormatException('Unsupported camera image format.');
    }

    var normalized = img.bakeOrientation(decoded);
    if (normalized.width > 1600 || normalized.height > 1600) {
      normalized = img.copyResize(
        normalized,
        width: normalized.width >= normalized.height ? 1600 : null,
        height: normalized.height > normalized.width ? 1600 : null,
        interpolation: img.Interpolation.linear,
      );
    }

    final separator = Platform.pathSeparator;
    final parent = source.parent.path;
    final normalizedPath =
        '$parent${separator}attendance_${DateTime.now().microsecondsSinceEpoch}.jpg';
    return File(
      normalizedPath,
    ).writeAsBytes(img.encodeJpg(normalized, quality: 92), flush: true);
  }
}
