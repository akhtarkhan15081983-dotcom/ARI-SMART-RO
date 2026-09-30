import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:path_provider/path_provider.dart';

class OfflineAttendanceStore {
  OfflineAttendanceStore({Directory? rootDirectoryOverride})
      : _rootDirectoryOverride = rootDirectoryOverride;

  static const String _queueFileName = 'pending_attendance_actions_v1.json';
  static const String _backupFileName = 'pending_attendance_actions_v1.backup.json';
  static const String _snapshotFileName = 'attendance_shift_snapshot_v1.json';
  static const String _snapshotBackupFileName = 'attendance_shift_snapshot_v1.backup.json';
  static const String _lockFileName = '.pending_attendance_actions_v1.lock';
  static const String _mediaFolderName = 'media';
  static const String _quarantineFolderName = 'corrupt_state';
  static const int maxPendingActions = 20;
  static final Map<String, Future<void>> _mutationTails = <String, Future<void>>{};

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
    final key = root.absolute.path;
    final previous = _mutationTails[key] ?? Future<void>.value();
    final gate = Completer<void>();
    final tail = previous.then<void>((_) => gate.future);
    _mutationTails[key] = tail;
    await previous;

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
        if (!gate.isCompleted) gate.complete();
        if (identical(_mutationTails[key], tail)) _mutationTails.remove(key);
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

  Future<File> _snapshotFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_snapshotFileName');
  }

  Future<File> _snapshotBackupFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_snapshotBackupFileName');
  }

  Future<Directory> _mediaDirectory() async {
    final root = await _rootDirectory();
    final dir = Directory('${root.path}/$_mediaFolderName');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  List<Map<String, dynamic>>? _decode(String raw) {
    try {
      final value = jsonDecode(raw);
      if (value is! List) return null;
      return value
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row))
          .toList(growable: true);
    } catch (_) {
      return null;
    }
  }

  Map<String, dynamic>? _decodeSnapshot(String raw) {
    try {
      final value = jsonDecode(raw);
      if (value is! Map) return null;
      return Map<String, dynamic>.from(value);
    } catch (_) {
      return null;
    }
  }

  Future<List<Map<String, dynamic>>?> _readValid(File file) async {
    if (!await file.exists()) return null;
    try {
      return _decode(await file.readAsString());
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> _readValidSnapshot(File file) async {
    if (!await file.exists()) return null;
    try {
      return _decodeSnapshot(await file.readAsString());
    } catch (_) {
      return null;
    }
  }

  Future<void> _quarantine(File file) async {
    if (!await file.exists()) return;
    try {
      final root = await _rootDirectory();
      final dir = Directory('${root.path}/$_quarantineFolderName');
      if (!await dir.exists()) await dir.create(recursive: true);
      final stamp = DateTime.now().toUtc().microsecondsSinceEpoch;
      await file.copy('${dir.path}/attendance-$stamp.corrupt.json');
    } catch (_) {}
  }

  Future<List<Map<String, dynamic>>> _readUnlocked() async {
    final file = await _queueFile();
    final temp = File('${file.path}.tmp');
    final primary = await _readValid(file);
    final tempState = await _readValid(temp);

    if (primary != null) {
      if (await temp.exists()) {
        if (tempState == null) await _quarantine(temp);
        try {
          await temp.delete();
        } catch (_) {}
      }
      return primary;
    }

    if (tempState != null) {
      await _quarantine(file);
      if (await file.exists()) await file.delete();
      await temp.rename(file.path);
      return tempState;
    }

    final backup = await _backupFile();
    final recovered = await _readValid(backup);
    if (recovered != null) {
      await _quarantine(file);
      await _writeUnlocked(recovered, writeBackup: false);
      return recovered;
    }

    await _quarantine(file);
    return <Map<String, dynamic>>[];
  }

  Future<Map<String, dynamic>?> _readSnapshotUnlocked() async {
    final file = await _snapshotFile();
    final temp = File('${file.path}.tmp');
    final primary = await _readValidSnapshot(file);
    final tempState = await _readValidSnapshot(temp);

    if (primary != null) {
      if (await temp.exists()) {
        if (tempState == null) await _quarantine(temp);
        try {
          await temp.delete();
        } catch (_) {}
      }
      return primary;
    }

    if (tempState != null) {
      await _quarantine(file);
      if (await file.exists()) await file.delete();
      await temp.rename(file.path);
      return tempState;
    }

    final backup = await _snapshotBackupFile();
    final recovered = await _readValidSnapshot(backup);
    if (recovered != null) {
      await _quarantine(file);
      await _writeSnapshotUnlocked(recovered, writeBackup: false);
      return recovered;
    }

    await _quarantine(file);
    return null;
  }

  Future<void> _writeUnlocked(
    List<Map<String, dynamic>> actions, {
    bool writeBackup = true,
  }) async {
    final file = await _queueFile();
    final backup = await _backupFile();
    final temp = File('${file.path}.tmp');
    final payload = jsonEncode(actions);
    await temp.writeAsString(payload, flush: true);
    if (_decode(await temp.readAsString()) == null) {
      throw const FileSystemException('Offline attendance queue validation failed.');
    }

    if (writeBackup) {
      final backupTemp = File('${backup.path}.tmp');
      await backupTemp.writeAsString(payload, flush: true);
      if (await backup.exists()) await backup.delete();
      await backupTemp.rename(backup.path);
    }
    if (await file.exists()) await file.delete();
    await temp.rename(file.path);
  }

  Future<void> _writeSnapshotUnlocked(
    Map<String, dynamic> snapshot, {
    bool writeBackup = true,
  }) async {
    final file = await _snapshotFile();
    final backup = await _snapshotBackupFile();
    final temp = File('${file.path}.tmp');
    final payload = jsonEncode(snapshot);
    await temp.writeAsString(payload, flush: true);
    if (_decodeSnapshot(await temp.readAsString()) == null) {
      throw const FileSystemException('Attendance snapshot validation failed.');
    }

    if (writeBackup) {
      final backupTemp = File('${backup.path}.tmp');
      await backupTemp.writeAsString(payload, flush: true);
      if (await backup.exists()) await backup.delete();
      await backupTemp.rename(backup.path);
    }
    if (await file.exists()) await file.delete();
    await temp.rename(file.path);
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
      actions.sort((a, b) => (a['captured_at'] ?? '')
          .toString()
          .compareTo((b['captured_at'] ?? '').toString()));
      return actions;
    });
  }

  Future<int> count() async => (await pending()).length;

  Future<void> saveShiftSnapshot({
    required DateTime checkIn,
    DateTime? checkOut,
  }) async {
    final localCheckIn = checkIn.toLocal();
    await _withLock(() async {
      await _writeSnapshotUnlocked(<String, dynamic>{
        'date': _localDate(localCheckIn),
        'check_in': checkIn.toUtc().toIso8601String(),
        'check_out': checkOut?.toUtc().toIso8601String(),
        'updated_at': DateTime.now().toUtc().toIso8601String(),
      });
    });
  }

  Future<Map<String, dynamic>?> todayShiftSnapshot({DateTime? now}) async {
    return _withLock(() async {
      final snapshot = await _readSnapshotUnlocked();
      if (snapshot == null) return null;
      final localNow = (now ?? DateTime.now()).toLocal();
      if (snapshot['date']?.toString() != _localDate(localNow)) return null;
      return Map<String, dynamic>.from(snapshot);
    });
  }

  Future<void> closeShiftSnapshot(DateTime checkOut) async {
    await _withLock(() async {
      final snapshot = await _readSnapshotUnlocked();
      if (snapshot == null) return;
      final localNow = checkOut.toLocal();
      if (snapshot['date']?.toString() != _localDate(localNow)) return;
      final checkIn = DateTime.tryParse(snapshot['check_in']?.toString() ?? '');
      if (checkIn == null) return;
      snapshot['check_out'] = checkOut.toUtc().toIso8601String();
      snapshot['updated_at'] = DateTime.now().toUtc().toIso8601String();
      await _writeSnapshotUnlocked(snapshot);
    });
  }

  String _localDate(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

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
