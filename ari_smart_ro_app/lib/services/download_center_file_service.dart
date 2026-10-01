import 'dart:io';

const Set<String> downloadCenterExtensions = {'.pdf', '.xlsx', '.csv'};

bool isDownloadCenterFile(FileSystemEntity entity) {
  if (entity is! File) return false;
  final path = entity.path.toLowerCase();
  return downloadCenterExtensions.any(path.endsWith);
}

Future<List<File>> discoverDownloadCenterFiles(Directory root) async {
  final files = <File>[];
  try {
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (!isDownloadCenterFile(entity)) continue;
      try {
        await (entity as File).stat();
        files.add(entity);
      } on FileSystemException {
        // File may disappear between directory listing and metadata read.
      }
    }
  } on FileSystemException {
    rethrow;
  }

  final dated = <({File file, DateTime modified})>[];
  for (final file in files) {
    try {
      final stat = await file.stat();
      dated.add((file: file, modified: stat.modified));
    } on FileSystemException {
      // Ignore files removed while the list is being refreshed.
    }
  }
  dated.sort((a, b) => b.modified.compareTo(a.modified));
  return dated.map((item) => item.file).toList(growable: false);
}
