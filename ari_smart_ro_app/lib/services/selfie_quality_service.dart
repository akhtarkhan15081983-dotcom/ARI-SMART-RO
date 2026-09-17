import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:image/image.dart' as img;

class SelfieQualityResult {
  const SelfieQualityResult._(this.isValid, this.message);

  final bool isValid;
  final String message;

  factory SelfieQualityResult.valid() =>
      const SelfieQualityResult._(true, 'Live selfie quality verified.');

  factory SelfieQualityResult.detectorFallback() => const SelfieQualityResult._(
    true,
    'Selfie captured successfully. Device face scan was unavailable, so the selfie will be reviewed after check-in.',
  );

  factory SelfieQualityResult.invalid(String message) =>
      SelfieQualityResult._(false, message);
}

class SelfieQualityService {
  static Future<SelfieQualityResult> validate(String imagePath) async {
    final file = File(imagePath);
    if (!await file.exists()) {
      return SelfieQualityResult.invalid(
        'Selfie image could not be read. Please retake it.',
      );
    }

    File? normalizedFile;

    try {
      // Camera apps do not encode orientation consistently. ML Kit can reject
      // otherwise valid selfies on some Android devices when EXIF rotation or
      // the source image format is unusual. Decode, bake the orientation and
      // provide a standard JPEG for reliable on-device face detection.
      try {
        normalizedFile = await _normalizeForDetection(file);
      } catch (error, stackTrace) {
        debugPrint('SELFIE NORMALIZATION ERROR: $error');
        debugPrintStack(stackTrace: stackTrace);
      }

      List<Face>? faces;
      Object? lastError;
      StackTrace? lastStackTrace;
      final candidates = <File>[
        if (normalizedFile != null) normalizedFile,
        file,
      ];

      for (final candidate in candidates) {
        try {
          faces = await _detectFaces(candidate);
          break;
        } catch (error, stackTrace) {
          lastError = error;
          lastStackTrace = stackTrace;
          debugPrint('SELFIE DETECTION ERROR (${candidate.path}): $error');
        }
      }

      if (faces == null) {
        if (lastStackTrace != null) {
          debugPrintStack(stackTrace: lastStackTrace);
        }

        // Some Android vendor builds can throw from the ML Kit platform
        // channel even for a valid camera JPEG. Do not block attendance only
        // because the optional on-device quality detector failed. We still
        // require a decodable, reasonably sized live camera image here; the
        // server continues to enforce enrolled-device + office GPS checks and
        // stores the selfie for the existing admin identity review workflow.
        final fallback = await _validateDetectorFallback(
          normalizedFile ?? file,
        );
        if (fallback != null) return fallback;

        throw StateError('Face detection failed: $lastError');
      }

      if (faces.isEmpty) {
        return SelfieQualityResult.invalid(
          'No face detected. Keep your full face clearly visible and retake the selfie.',
        );
      }

      if (faces.length != 1) {
        return SelfieQualityResult.invalid(
          'Only one person may appear in the attendance selfie.',
        );
      }

      final face = faces.single;
      final box = face.boundingBox;

      // Reject tiny/distant detections. This is intentionally a capture-quality
      // check only; it does not identify or compare the employee.
      if (box.width < 140 || box.height < 140) {
        return SelfieQualityResult.invalid(
          'Your face is too far from the camera. Move closer and retake the selfie.',
        );
      }

      final yaw = face.headEulerAngleY?.abs();
      final roll = face.headEulerAngleZ?.abs();
      if ((yaw != null && yaw > 22) || (roll != null && roll > 18)) {
        return SelfieQualityResult.invalid(
          'Look straight at the camera and keep your head upright.',
        );
      }

      final leftEye = face.leftEyeOpenProbability;
      final rightEye = face.rightEyeOpenProbability;
      if ((leftEye != null && leftEye < 0.35) ||
          (rightEye != null && rightEye < 0.35)) {
        return SelfieQualityResult.invalid(
          'Keep both eyes open and look at the camera.',
        );
      }

      return SelfieQualityResult.valid();
    } catch (error, stackTrace) {
      debugPrint('SELFIE QUALITY VERIFICATION ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);
      return SelfieQualityResult.invalid(
        'Unable to process this selfie. Please retake it and keep the phone upright.',
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

  static Future<List<Face>> _detectFaces(File image) async {
    // Fast mode uses the lighter on-device detector and is more reliable on
    // vendor Android builds. Classification stays enabled so the existing
    // eyes-open quality check remains active when ML Kit reports it.
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

  static Future<SelfieQualityResult?> _validateDetectorFallback(
    File image,
  ) async {
    try {
      final bytes = await image.readAsBytes();
      if (bytes.length < 20 * 1024) {
        return SelfieQualityResult.invalid(
          'Selfie image quality is too low. Please retake it in good light.',
        );
      }

      final decoded = img.decodeImage(bytes);
      if (decoded == null) return null;
      final normalized = img.bakeOrientation(decoded);
      final shortSide = normalized.width < normalized.height
          ? normalized.width
          : normalized.height;
      final longSide = normalized.width > normalized.height
          ? normalized.width
          : normalized.height;
      if (shortSide < 360 || longSide < 480) {
        return SelfieQualityResult.invalid(
          'Selfie image is too small. Please retake it with the front camera.',
        );
      }

      debugPrint(
        'SELFIE DETECTOR FALLBACK: valid camera image accepted for server review.',
      );
      return SelfieQualityResult.detectorFallback();
    } catch (error, stackTrace) {
      debugPrint('SELFIE FALLBACK ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);
      return null;
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
