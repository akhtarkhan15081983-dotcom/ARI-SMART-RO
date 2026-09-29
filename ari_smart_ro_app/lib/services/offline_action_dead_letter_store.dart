import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

/// Append-only diagnostic store for offline actions that cannot be retried.
///
/// A broken media action must not block every later field action forever. We
/// preserve enough local evidence here before removing it from the active queue.
class OfflineActionDeadLetterStore {
  OfflineActionDeadLetterStore({Directory? rootDirectoryOverride})
      : _rootDirectoryOverride = rootDirectoryOverride;

  static const String _fileName = 'offline_action_dead_letters.jsonl';
  final Directory? _rootDirectoryOverride;

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

  Future<File> _file() async {
    final root = await _rootDirectory();
    return File('${root.path}/$_fileName');
  }

  Future<void> append({
    required Map<String, dynamic> action,
    required String reason,
    String? detail,
  }) async {
    final file = await _file();
    final record = <String, dynamic>{
      'failed_at': DateTime.now().toUtc().toIso8601String(),
      'reason': reason,
      if (detail != null && detail.isNotEmpty) 'detail': detail,
      'action': Map<String, dynamic>.from(action),
    };
    await file.writeAsString(
      '${jsonEncode(record)}\n',
      mode: FileMode.append,
      flush: true,
    );
  }

  Future<List<Map<String, dynamic>>> entries() async {
    final file = await _file();
    if (!await file.exists()) return <Map<String, dynamic>>[];

    final result = <Map<String, dynamic>>[];
    try {
      for (final line in await file.readAsLines()) {
        final trimmed = line.trim();
        if (trimmed.isEmpty) continue;
        try {
          final decoded = jsonDecode(trimmed);
          if (decoded is Map) {
            result.add(Map<String, dynamic>.from(decoded));
          }
        } catch (_) {
          // One damaged diagnostic line must not hide later dead letters.
        }
      }
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
    return result;
  }

  Future<int> count() async => (await entries()).length;
}
