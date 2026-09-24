import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';

import 'app.dart';
import 'services/client_observability_service.dart';
import 'services/live_location_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final previousFlutterErrorHandler = FlutterError.onError;
  FlutterError.onError = (details) {
    previousFlutterErrorHandler?.call(details);
    unawaited(
      ClientObservabilityService.reportError(
        details.exception,
        details.stack ?? StackTrace.current,
        phase: 'flutter-framework',
      ),
    );
  };

  PlatformDispatcher.instance.onError = (error, stack) {
    unawaited(
      ClientObservabilityService.reportError(
        error,
        stack,
        phase: 'platform-dispatcher',
      ),
    );
    return false;
  };

  runApp(const AriSmartROApp());

  WidgetsBinding.instance.addPostFrameCallback((_) {
    unawaited(LiveLocationService.initialize());
  });
}
