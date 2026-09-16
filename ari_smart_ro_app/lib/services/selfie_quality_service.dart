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

    final detector = FaceDetector(
      options: FaceDetectorOptions(
        enableClassification: true,
        enableLandmarks: false,
        performanceMode: FaceDetectorMode.accurate,
      ),
    );

    try {
      // Camera apps do not encode orientation consistently. ML Kit can reject
      // otherwise valid selfies on some Android devices when EXIF rotation or
      // the source image format is unusual. Decode, bake the orientation and
      // provide a standard JPEG for reliable on-device face detection.
      normalizedFile = await _normalizeForDetection(file);
      final input = InputImage.fromFilePath(normalizedFile.path);
      final faces = await detector.processImage(input);

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
      await detector.close();
      if (normalizedFile != null && normalizedFile.path != file.path) {
        try {
          await normalizedFile.delete();
        } catch (_) {
          // Temporary validation images are safe to leave for OS cleanup.
        }
      }
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
