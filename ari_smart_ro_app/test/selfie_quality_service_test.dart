import 'dart:io';

import 'package:ari_smart_ro_app/services/selfie_quality_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('accepts a sufficiently sized JPEG camera capture', () async {
    final directory = await Directory.systemTemp.createTemp('selfie-test-');
    addTearDown(() => directory.delete(recursive: true));
    final file = File('${directory.path}${Platform.pathSeparator}selfie.jpg');
    await file.writeAsBytes(<int>[0xff, 0xd8, ...List<int>.filled(22000, 1)]);

    expect(await SelfieQualityService.isPlausibleCameraImage(file), isTrue);
  });

  test('rejects a non-image file', () async {
    final directory = await Directory.systemTemp.createTemp('selfie-test-');
    addTearDown(() => directory.delete(recursive: true));
    final file = File('${directory.path}${Platform.pathSeparator}invalid.bin');
    await file.writeAsBytes(List<int>.filled(22000, 1));

    expect(await SelfieQualityService.isPlausibleCameraImage(file), isFalse);
  });
}
