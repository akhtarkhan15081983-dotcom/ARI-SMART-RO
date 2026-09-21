import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

import '../models/job_model.dart';

class OfflineJobStore {
  static const _stateFileName = 'offline_job_state_v1.json';
  static const _mediaFolderName = 'pending_media';

  Future<Directory> _rootDirectory() async {
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

  Future<Directory> _mediaDirectory() async {
    final root = await _rootDirectory();
    final dir = Directory('${root.path}/$_mediaFolderName');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<Map<String, dynamic>> _readState() async {
    final file = await _stateFile();
    if (!await file.exists()) {
      return <String, dynamic>{
        'jobs': <String, dynamic>{},
        'queue': <dynamic>[],
        'gps_unavailable': <String, dynamic>{},
      };
    }

    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is Map<String, dynamic>) {
        decoded.putIfAbsent('jobs', () => <String, dynamic>{});
        decoded.putIfAbsent('queue', () => <dynamic>[]);
        decoded.putIfAbsent('gps_unavailable', () => <String, dynamic>{});
        return decoded;
      }
    } catch (_) {
      // If the cache is damaged, start clean rather than blocking field work.
    }

    return <String, dynamic>{
      'jobs': <String, dynamic>{},
      'queue': <dynamic>[],
      'gps_unavailable': <String, dynamic>{},
    };
  }

  Future<void> _writeState(Map<String, dynamic> state) async {
    final file = await _stateFile();
    final temp = File('${file.path}.tmp');
    await temp.writeAsString(jsonEncode(state), flush: true);
    if (await file.exists()) {
      await file.delete();
    }
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
        jobs.add(JobModel.fromJson(Map<String, dynamic>.from(value)));
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
    return JobModel.fromJson(Map<String, dynamic>.from(value));
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

    if (queue.any((row) => row['id'] == id)) {
      return id;
    }

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
    if (!await saved.exists()) {
      await source.copy(saved.path);
    }
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
    if (!await saved.exists()) {
      await saved.writeAsBytes(bytes, flush: true);
    }
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
    return List<Map<String, dynamic>>.from(
      (state['queue'] as List? ?? const <dynamic>[])
          .whereType<Map>()
          .map((row) => Map<String, dynamic>.from(row)),
    );
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
      if (await file.exists()) {
        await file.delete();
      }
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
