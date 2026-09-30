import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:path_provider/path_provider.dart';

class OfflineAttendanceStore {
  OfflineAttendanceStore({Directory? rootDirectoryOverride})
      : _rootDirectoryOverride = rootDirectoryOverride;

  static const String _queueFileName = 'pending_attendance_actions_v1.json';
  static const String _backupFileName = 'pending_attendance_actions_v1.backup.json';
  static const String _lockFileName = '.pending_attendance_actions_v1.lock';
  static const String _mediaFolderName = 'media';
  static const int maxPendingActions = 20;

  final Directory? _rootDirectoryOverride;

  Future<Directory> _rootDirectory() async {
    final override = _rootDirectoryOverride;
    if (override != null) {
      if (!await override.exists()) await override.create(recursive: true);
      return override;
    }
    final base = await getApplicationSupportDirectory();
    final dir = Directory('${base.path}/ari_offline_attendance');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<T> _withLock<T>(Future<T> Function() action) async {
    final root = await _rootDirectory();
    final lock = File('${root.path}/$_lockFileName');
    final handle = await lock.open(mode: FileMode.append);
    await handle.lock(FileLock.exclusive);
    try {
      return await action();
    } finally {
      try {
        await handle.unlock();
      } finally {
        await handle.close();
      }
    }
  }

  Future<File> _queueFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_queueFileName');
  }

  Future<File> _backupFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_backupFileName');
  }

  Future<Directory> _mediaDirectory() async {
    final root = await _rootDirectory();
    final dir = Directory('${root.path}/$_mediaFolderName');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  List<Map<String, dynamic>> _decode(String raw) {
    try {
      final value = jsonDecode(raw);
      if (value is! List) return <Map<String, dynamic>>[];
      return value
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList(growable: true);
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  Future<List<Map<String, dynamic>>> _readUnlocked() async {
    final file = await _queueFile();
    if (await file.exists()) {
      final decoded = _decode(await file.readAsString());
      if (decoded.isNotEmpty || (await file.readAsString()).trim() == '[]') {
        return decoded;
      }
    }
    final backup = await _backupFile();
    if (await backup.exists()) return _decode(await backup.readAsString());
    return <Map<String, dynamic>>[];
  }

  Future<void> _writeUnlocked(List<Map<String, dynamic>> actions) async {
    final file = await _queueFile();
    final backup = await _backupFile();
    final temp = File('${file.path}.tmp');
    final payload = jsonEncode(actions);
    await temp.writeAsString(payload, flush: true);
    if (await file.exists()) await file.delete();
    await temp.rename(file.path);
    await backup.writeAsString(payload, flush: true);
  }

  String newActionId() {
    final random = Random.secure();
    final suffix = List<int>.generate(12, (_) => random.nextInt(256))
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    return '${DateTime.now().toUtc().microsecondsSinceEpoch}-$suffix';
  }

  Future<String> preserveSelfie(String sourcePath, String actionId) async {
    final source = File(sourcePath);
    if (!await source.exists()) {
      throw const FileSystemException('Selfie file is no longer available.');
    }
    final media = await _mediaDirectory();
    final target = File('${media.path}/$actionId.jpg');
    await source.copy(target.path);
    return target.path;
  }

  Future<void> enqueue(Map<String, dynamic> action) async {
    await _withLock(() async {
      final actions = await _readUnlocked();
      final actionId = (action['action_id'] ?? '').toString();
      if (actions.any((row) => row['action_id']?.toString() == actionId)) return;
      if (actions.length >= maxPendingActions) {
        throw const FileSystemException(
          'Too many pending offline attendance actions. Connect to the internet before recording more attendance.',
        );
      }
      actions.add(Map<String, dynamic>.from(action));
      await _writeUnlocked(actions);
    });
  }

  Future<List<Map<String, dynamic>>> pending() async {
    return _withLock(() async {
      final actions = await _readUnlocked();
      actions.sort(
        (a, b) => (a['captured_at'] ?? '')
            .toString()
            .compareTo((b['captured_at'] ?? '').toString()),
      );
      return actions;
    });
  }

  Future<int> count() async => (await pending()).length;

  Future<void> remove(String actionId, {bool deleteMedia = true}) async {
    String? mediaPath;
    await _withLock(() async {
      final actions = await _readUnlocked();
      for (final row in actions) {
        if (row['action_id']?.toString() == actionId) {
          mediaPath = row['selfie_path']?.toString();
          break;
        }
      }
      actions.removeWhere((row) => row['action_id']?.toString() == actionId);
      await _writeUnlocked(actions);
    });
    if (deleteMedia && mediaPath != null && mediaPath!.isNotEmpty) {
      final file = File(mediaPath!);
      if (await file.exists()) {
        try {
          await file.delete();
        } catch (_) {}
      }
    }
  }
}
