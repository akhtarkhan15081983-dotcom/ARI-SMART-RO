import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

import '../models/job_model.dart';
import 'offline_action_dead_letter_store.dart';

class OfflineJobStore {
  OfflineJobStore({Directory? rootDirectoryOverride})
      : _rootDirectoryOverride = rootDirectoryOverride;

  static const _stateFileName = 'offline_job_state_v1.json';
  static const _backupFileName = 'offline_job_state_v1.backup.json';
  static const _recoveryLogFileName = 'offline_job_recovery_events.jsonl';
  static const _mediaFolderName = 'pending_media';
  static const _quarantineFolderName = 'corrupt_state';

  final Directory? _rootDirectoryOverride;

  Map<String, dynamic> _emptyState() => <String, dynamic>{
        'jobs': <String, dynamic>{},
        'queue': <dynamic>[],
        'gps_unavailable': <String, dynamic>{},
      };

  Future<Directory> _rootDirectory() async {
    final override = _rootDirectoryOverride;
    if (override != null) {
      if (!await override.exists()) {
        await override.create(recursive: true);
      }
      return override;
    }

    final base = await getApplicationSupportDirectory();
    final dir = Directory('${base.path}/ari_offline_jobs');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<File> _stateFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_stateFileName');
  }

  Future<File> _backupFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_backupFileName');
  }

  Future<File> _recoveryLogFile() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_recoveryLogFileName');
  }

  Future<Directory> _quarantineDirectory() async {
    final root = await _rootDirectory();
    final dir = Directory('${root.path}/$_quarantineFolderName');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<Directory> _mediaDirectory() async {
    final root = await _rootDirectory();
    final dir = Directory('${root.path}/$_mediaFolderName');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Map<String, dynamic>? _decodeState(String raw) {
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) return null;

      final state = Map<String, dynamic>.from(decoded);
      final jobs = state['jobs'];
      final queue = state['queue'];
      final gpsUnavailable = state['gps_unavailable'];
      if (jobs != null && jobs is! Map) return null;
      if (queue != null && queue is! List) return null;
      if (gpsUnavailable != null && gpsUnavailable is! Map) return null;

      state['jobs'] = Map<String, dynamic>.from(
        jobs as Map? ?? const <String, dynamic>{},
      );
      state['queue'] = List<dynamic>.from(
        queue as List? ?? const <dynamic>[],
      );
      state['gps_unavailable'] = Map<String, dynamic>.from(
        gpsUnavailable as Map? ?? const <String, dynamic>{},
      );
      return state;
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> _readValidFile(File file) async {
    if (!await file.exists()) return null;
    try {
      return _decodeState(await file.readAsString());
    } catch (_) {
      return null;
    }
  }

  Future<String?> _quarantineCorruptFile(File file) async {
    if (!await file.exists()) return null;
    try {
      final dir = await _quarantineDirectory();
      final stamp = DateTime.now().toUtc().microsecondsSinceEpoch;
      final target = File('${dir.path}/state-$stamp.corrupt.json');
      await file.copy(target.path);
      return target.path;
    } catch (_) {
      return null;
    }
  }

  Future<void> _recordRecoveryEvent({
    required String reason,
    String? quarantinedPath,
    String? recoveredFrom,
  }) async {
    try {
      final log = await _recoveryLogFile();
      await log.writeAsString(
        '${jsonEncode(<String, dynamic>{
          'occurred_at': DateTime.now().toUtc().toIso8601String(),
          'reason': reason,
          if (quarantinedPath != null) 'quarantined_path': quarantinedPath,
          if (recoveredFrom != null) 'recovered_from': recoveredFrom,
        })}\n',
        mode: FileMode.append,
        flush: true,
      );
    } catch (_) {
      // Recovery logging must never block field work.
    }
  }

  Future<Map<String, dynamic>> _readState() async {
    final file = await _stateFile();
    if (!await file.exists()) return _emptyState();

    final primary = await _readValidFile(file);
    if (primary != null) return primary;

    final quarantinedPath = await _quarantineCorruptFile(file);
    final backup = await _backupFile();
    final recovered = await _readValidFile(backup);
    if (recovered != null) {
      await _recordRecoveryEvent(
        reason: 'PRIMARY_STATE_CORRUPT',
        quarantinedPath: quarantinedPath,
        recoveredFrom: _backupFileName,
      );
      await _writeState(recovered, preserveExistingAsBackup: false);
      return recovered;
    }

    await _recordRecoveryEvent(
      reason: 'PRIMARY_STATE_CORRUPT_NO_VALID_BACKUP',
      quarantinedPath: quarantinedPath,
    );
    return _emptyState();
  }

  Future<void> _writeState(
    Map<String, dynamic> state, {
    bool preserveExistingAsBackup = true,
  }) async {
    final file = await _stateFile();
    final backup = await _backupFile();
    final temp = File('${file.path}.tmp');
    final payload = jsonEncode(state);

    await temp.writeAsString(payload, flush: true);
    if (_decodeState(await temp.readAsString()) == null) {
      throw const FileSystemException('Offline job state validation failed.');
    }

    if (preserveExistingAsBackup && await file.exists()) {
      final existing = await _readValidFile(file);
      if (existing != null) {
        final backupTemp = File('${backup.path}.tmp');
        await backupTemp.writeAsString(jsonEncode(existing), flush: true);
        if (await backup.exists()) await backup.delete();
        await backupTemp.rename(backup.path);
      }
    }

    if (await file.exists()) await file.delete();
    await temp.rename(file.path);
  }

  Future<void> cacheJobs(List<JobModel> jobs) async {
    final state = await _readState();
    final cached = Map<String, dynamic>.from(
      state['jobs'] as Map? ?? const <String, dynamic>{},
    );
    for (final job in jobs) {
      cached[job.id.toString()] = job.toJson();
    }
    state['jobs'] = cached;
    await _writeState(state);
  }

  Future<void> cacheJob(JobModel job) async {
    final state = await _readState();
    final cached = Map<String, dynamic>.from(
      state['jobs'] as Map? ?? const <String, dynamic>{},
    );
    cached[job.id.toString()] = job.toJson();
    state['jobs'] = cached;
    await _writeState(state);
  }

  Future<List<JobModel>> getCachedJobs() async {
    final state = await _readState();
    final cached = Map<String, dynamic>.from(
      state['jobs'] as Map? ?? const <String, dynamic>{},
    );
    final jobs = <JobModel>[];
    for (final value in cached.values) {
      if (value is Map) {
        try {
          jobs.add(JobModel.fromJson(Map<String, dynamic>.from(value)));
        } catch (_) {
          // One malformed cached job must not hide other usable offline jobs.
        }
      }
    }
    jobs.sort((a, b) => a.scheduledDate.compareTo(b.scheduledDate));
    return jobs;
  }

  Future<JobModel?> getCachedJob(int jobId) async {
    final state = await _readState();
    final cached = Map<String, dynamic>.from(
      state['jobs'] as Map? ?? const <String, dynamic>{},
    );
    final value = cached[jobId.toString()];
    if (value is! Map) return null;
    try {
      return JobModel.fromJson(Map<String, dynamic>.from(value));
    } catch (_) {
      return null;
    }
  }

  Future<void> updateCachedStatus(int jobId, String status) async {
    final state = await _readState();
    final cached = Map<String, dynamic>.from(
      state['jobs'] as Map? ?? const <String, dynamic>{},
    );
    final value = cached[jobId.toString()];
    if (value is Map) {
      final row = Map<String, dynamic>.from(value);
      row['status'] = status;
      cached[jobId.toString()] = row;
      state['jobs'] = cached;
      await _writeState(state);
    }
  }

  String newActionId(String type, int jobId) {
    final random = Random().nextInt(1 << 32).toRadixString(16);
    return '${type.toLowerCase()}-$jobId-${DateTime.now().microsecondsSinceEpoch}-$random';
  }

  Future<String> queueAction({
    required String type,
    required int jobId,
    required Map<String, dynamic> payload,
    String? actionId,
    String? filePath,
  }) async {
    final id = actionId ?? newActionId(type, jobId);
    final state = await _readState();
    final queue = List<Map<String, dynamic>>.from(
      (state['queue'] as List? ?? const <dynamic>[])
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row)),
    );

    if (queue.any((row) => row['id'] == id)) return id;

    queue.add(<String, dynamic>{
      'id': id,
      'type': type,
      'job_id': jobId,
      'payload': payload,
      if (filePath != null) 'file_path': filePath,
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
    state['queue'] = queue;
    await _writeState(state);
    return id;
  }

  Future<String> queuePhoto({
    required int jobId,
    required String sourcePath,
    required String description,
    String? actionId,
  }) async {
    final id = actionId ?? newActionId('PHOTO', jobId);
    final source = File(sourcePath);
    final mediaDir = await _mediaDirectory();
    final extension = sourcePath.toLowerCase().endsWith('.png') ? '.png' : '.jpg';
    final saved = File('${mediaDir.path}/$id$extension');
    if (!await saved.exists()) await source.copy(saved.path);
    return queueAction(
      type: 'PHOTO',
      jobId: jobId,
      payload: <String, dynamic>{'description': description},
      actionId: id,
      filePath: saved.path,
    );
  }

  Future<String> queueSignature({
    required int jobId,
    required Uint8List bytes,
    required String customerName,
    String? actionId,
  }) async {
    final id = actionId ?? newActionId('SIGNATURE', jobId);
    final mediaDir = await _mediaDirectory();
    final saved = File('${mediaDir.path}/$id.png');
    if (!await saved.exists()) await saved.writeAsBytes(bytes, flush: true);
    return queueAction(
      type: 'SIGNATURE',
      jobId: jobId,
      payload: <String, dynamic>{'customer_name': customerName},
      actionId: id,
      filePath: saved.path,
    );
  }

  Future<List<Map<String, dynamic>>> pendingActions() async {
    final state = await _readState();
    final queue = List<Map<String, dynamic>>.from(
      (state['queue'] as List? ?? const <dynamic>[])
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row)),
    );
    if (queue.isEmpty) return queue;

    final valid = <Map<String, dynamic>>[];
    final deadLetters = OfflineActionDeadLetterStore(
      rootDirectoryOverride: _rootDirectoryOverride,
    );
    var changed = false;

    for (final action in queue) {
      final type = (action['type'] ?? '').toString().trim().toUpperCase();
      if (type != 'PHOTO' && type != 'SIGNATURE') {
        valid.add(action);
        continue;
      }

      final filePath = (action['file_path'] ?? '').toString().trim();
      String? reason;
      if (filePath.isEmpty) {
        reason = 'MEDIA_PATH_MISSING';
      } else {
        final file = File(filePath);
        try {
          if (!await file.exists()) {
            reason = 'MEDIA_FILE_MISSING';
          } else if (await file.length() <= 0) {
            reason = 'MEDIA_FILE_EMPTY';
          }
        } catch (_) {
          reason = 'MEDIA_FILE_UNREADABLE';
        }
      }

      if (reason == null) {
        valid.add(action);
        continue;
      }

      changed = true;
      try {
        await deadLetters.append(
          action: action,
          reason: reason,
          detail: filePath.isEmpty ? null : filePath,
        );
      } catch (_) {
        // Do not allow a diagnostic write failure to keep the whole sync queue
        // permanently blocked. The state backup still preserves prior history.
      }
    }

    if (changed) {
      state['queue'] = valid;
      await _writeState(state);
    }
    return valid;
  }

  Future<int> pendingCount({int? jobId}) async {
    final queue = await pendingActions();
    if (jobId == null) return queue.length;
    return queue.where((row) => row['job_id'] == jobId).length;
  }

  Future<void> removeAction(String actionId) async {
    final state = await _readState();
    final queue = List<Map<String, dynamic>>.from(
      (state['queue'] as List? ?? const <dynamic>[])
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row)),
    );
    final row = queue.cast<Map<String, dynamic>?>().firstWhere(
          (item) => item?['id'] == actionId,
          orElse: () => null,
        );
    queue.removeWhere((item) => item['id'] == actionId);
    state['queue'] = queue;
    await _writeState(state);

    final filePath = row?['file_path']?.toString();
    if (filePath != null && filePath.isNotEmpty) {
      final file = File(filePath);
      if (await file.exists()) await file.delete();
    }
  }

  Future<void> setGpsUnavailable(int jobId, bool unavailable) async {
    final state = await _readState();
    final map = Map<String, dynamic>.from(
      state['gps_unavailable'] as Map? ?? const <String, dynamic>{},
    );
    if (unavailable) {
      map[jobId.toString()] = DateTime.now().toUtc().toIso8601String();
    } else {
      map.remove(jobId.toString());
    }
    state['gps_unavailable'] = map;
    await _writeState(state);
  }

  Future<bool> isGpsUnavailable(int jobId) async {
    final state = await _readState();
    final map = Map<String, dynamic>.from(
      state['gps_unavailable'] as Map? ?? const <String, dynamic>{},
    );
    return map.containsKey(jobId.toString());
  }
}
