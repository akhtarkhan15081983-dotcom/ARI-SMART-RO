import 'dart:io';

import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';

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

    final detector = FaceDetector(
      options: FaceDetectorOptions(
        enableClassification: true,
        enableLandmarks: true,
        performanceMode: FaceDetectorMode.accurate,
      ),
    );

    try {
      final input = InputImage.fromFilePath(imagePath);
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
    } catch (_) {
      return SelfieQualityResult.invalid(
        'Unable to verify selfie quality. Please retake the photo in good light.',
      );
    } finally {
      await detector.close();
    }
  }
}
