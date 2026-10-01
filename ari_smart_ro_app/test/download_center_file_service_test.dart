import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/download_center_file_service.dart';

void main() {
  test('download center discovers supported files newest first', () async {
    final root = await Directory.systemTemp.createTemp('ari-download-center-');
    addTearDown(() => root.delete(recursive: true));

    final older = File('${root.path}${Platform.pathSeparator}older.pdf');
    final newer = File('${root.path}${Platform.pathSeparator}newer.xlsx');
    final ignored = File('${root.path}${Platform.pathSeparator}notes.txt');

    await older.writeAsString('old');
    await newer.writeAsString('new');
    await ignored.writeAsString('ignore');

    final now = DateTime.now();
    await older.setLastModified(now.subtract(const Duration(minutes: 5)));
    await newer.setLastModified(now);

    final files = await discoverDownloadCenterFiles(root);

    expect(files.map((file) => file.path).toList(), [newer.path, older.path]);
  });

  test('download center ignores files removed during refresh', () async {
    final root = await Directory.systemTemp.createTemp('ari-download-center-race-');
    addTearDown(() async {
      if (await root.exists()) {
        await root.delete(recursive: true);
      }
    });

    final keep = File('${root.path}${Platform.pathSeparator}keep.csv');
    final removed = File('${root.path}${Platform.pathSeparator}removed.pdf');
    await keep.writeAsString('keep');
    await removed.writeAsString('remove');
    await removed.delete();

    final files = await discoverDownloadCenterFiles(root);

    expect(files.map((file) => file.path), contains(keep.path));
    expect(files.map((file) => file.path), isNot(contains(removed.path)));
  });

  test('download center extension filter is case insensitive', () async {
    final root = await Directory.systemTemp.createTemp('ari-download-center-ext-');
    addTearDown(() => root.delete(recursive: true));

    final pdf = File('${root.path}${Platform.pathSeparator}REPORT.PDF');
    final csv = File('${root.path}${Platform.pathSeparator}data.CSV');
    final xlsx = File('${root.path}${Platform.pathSeparator}sheet.XLSX');
    await pdf.writeAsString('pdf');
    await csv.writeAsString('csv');
    await xlsx.writeAsString('xlsx');

    final files = await discoverDownloadCenterFiles(root);
    final names = files.map((file) => file.path.split(Platform.pathSeparator).last).toSet();

    expect(names, {'REPORT.PDF', 'data.CSV', 'sheet.XLSX'});
  });
}
