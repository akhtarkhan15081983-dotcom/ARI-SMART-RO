import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'location_point_identity.dart';

/// Durable append-only queue for employee GPS points captured while offline.
///
/// Points are written as JSON Lines so a sudden app/process death cannot corrupt
/// the whole backlog. Acknowledged points are removed by atomically replacing the
/// queue file with only the remaining lines.
///
/// The foreground UI isolate and the Android background-service isolate may both
/// touch this queue. An OS file lock serializes reads/mutations across isolates so
/// an acknowledge/compaction cannot overwrite a point that is being appended at
/// the same time.
class LocationQueueStore {
  LocationQueueStore._();

  static const String _fileName = 'pending_location_points_v2.jsonl';
  static const String _lockFileName = '.pending_location_points_v2.lock';
  static const String _sequenceFileName = '.location_sequence_v5';
  static const int maxRetainedPoints = 6000; // ~33h at a 20-second cadence.
  static const int defaultBatchSize = 200;
  static const int _compactEveryAppends = 250;
  static int _appendsSinceCompactionCheck = 0;

  static Future<Directory> _queueDirectory() async {
    final root = await getApplicationSupportDirectory();
    final directory = Directory('${root.path}/ari_live_location');
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  static Future<File> _queueFile() async {
    final directory = await _queueDirectory();
    return File('${directory.path}/$_fileName');
  }

  static Future<T> _withQueueLock<T>(Future<T> Function() action) async {
    final directory = await _queueDirectory();
    final lockFile = File('${directory.path}/$_lockFileName');
    final handle = await lockFile.open(mode: FileMode.append);
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

  /// Allocate a monotonically increasing point sequence across isolates/restarts.
  ///
  /// The same queue file lock protects this tiny counter so the UI and background
  /// isolates cannot allocate the same sequence. If storage is temporarily
  /// unavailable, use the UTC microsecond clock as a fail-safe rather than losing
  /// the GPS fix merely because identity bookkeeping failed.
  static Future<int> nextClientSequence() async {
    final nowMicros = DateTime.now().toUtc().microsecondsSinceEpoch;
    try {
      return await _withQueueLock(() async {
        final directory = await _queueDirectory();
        final sequenceFile = File('${directory.path}/$_sequenceFileName');
        int? persisted;
        if (await sequenceFile.exists()) {
          try {
            persisted = int.tryParse((await sequenceFile.readAsString()).trim());
          } catch (_) {
            persisted = null;
          }
        }

        final next = LocationPointIdentity.nextSequence(
          persisted: persisted,
          nowMicros: nowMicros,
        );
        final temp = File('${sequenceFile.path}.tmp');
        await temp.writeAsString('$next\n', flush: true);
        if (await sequenceFile.exists()) {
          await sequenceFile.delete();
        }
        await temp.rename(sequenceFile.path);
        return next;
      });
    } catch (_) {
      return nowMicros;
    }
  }

  static Future<void> append(Map<String, dynamic> point) async {
    await _withQueueLock(() async {
      final file = await _queueFile();
      await file.writeAsString(
        '${jsonEncode(point)}\n',
        mode: FileMode.append,
        flush: true,
      );

      _appendsSinceCompactionCheck++;
      if (_appendsSinceCompactionCheck >= _compactEveryAppends) {
        _appendsSinceCompactionCheck = 0;
        await _trimIfNeeded(file);
      }
    });
  }

  static Future<List<Map<String, dynamic>>> readBatch({
    int limit = defaultBatchSize,
  }) async {
    return _withQueueLock(() async {
      final file = await _queueFile();
      if (!await file.exists()) return <Map<String, dynamic>>[];

      final points = <Map<String, dynamic>>[];
      try {
        final lines = await file.readAsLines();
        for (final line in lines) {
          if (points.length >= limit) break;
          final trimmed = line.trim();
          if (trimmed.isEmpty) continue;
          try {
            final decoded = jsonDecode(trimmed);
            if (decoded is Map) {
              points.add(Map<String, dynamic>.from(decoded));
            }
          } catch (_) {
            // Keep scanning. One truncated/corrupt line must not block later data.
          }
        }
      } catch (_) {
        return <Map<String, dynamic>>[];
      }
      return points;
    });
  }

  static Future<int> count() async {
    return _withQueueLock(() async {
      final file = await _queueFile();
      if (!await file.exists()) return 0;
      try {
        final lines = await file.readAsLines();
        return lines.where((line) => line.trim().isNotEmpty).length;
      } catch (_) {
        return 0;
      }
    });
  }

  static Future<void> acknowledgeFirst(int count) async {
    if (count <= 0) return;
    await _withQueueLock(() async {
      final file = await _queueFile();
      if (!await file.exists()) return;

      final lines = await file.readAsLines();
      var validSeen = 0;
      final remaining = <String>[];
      for (final line in lines) {
        final trimmed = line.trim();
        if (trimmed.isEmpty) continue;

        var valid = false;
        try {
          valid = jsonDecode(trimmed) is Map;
        } catch (_) {
          // Corrupt lines are intentionally discarded during compaction.
        }
        if (!valid) continue;

        if (validSeen < count) {
          validSeen++;
        } else {
          remaining.add(trimmed);
        }
      }

      await _replaceAtomically(file, remaining);
    });
  }

  /// Caller must already hold [_withQueueLock].
  static Future<void> _trimIfNeeded(File file) async {
    try {
      final lines = await file.readAsLines();
      final valid = <String>[];
      for (final line in lines) {
        final trimmed = line.trim();
        if (trimmed.isEmpty) continue;
        try {
          if (jsonDecode(trimmed) is Map) valid.add(trimmed);
        } catch (_) {
          // Drop only the damaged line; preserve every other recoverable point.
        }
      }
      if (valid.length <= maxRetainedPoints) return;
      await _replaceAtomically(
        file,
        valid.sublist(valid.length - maxRetainedPoints),
      );
    } catch (_) {
      // Queue trimming is best-effort. Never fail location capture because of it.
    }
  }

  /// Caller must already hold [_withQueueLock].
  static Future<void> _replaceAtomically(
    File file,
    List<String> lines,
  ) async {
    final temp = File('${file.path}.tmp');
    final payload = lines.isEmpty ? '' : '${lines.join('\n')}\n';
    await temp.writeAsString(payload, flush: true);
    if (await file.exists()) {
      await file.delete();
    }
    await temp.rename(file.path);
  }
}
