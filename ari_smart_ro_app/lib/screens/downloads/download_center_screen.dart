import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

class DownloadCenterScreen extends StatefulWidget {
  const DownloadCenterScreen({super.key});
  @override
  State<DownloadCenterScreen> createState() => _DownloadCenterScreenState();
}

class _DownloadCenterScreenState extends State<DownloadCenterScreen> {
  bool _loading = true;
  List<File> _files = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final root = await getApplicationDocumentsDirectory();
    final files = <File>[];
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File) continue;
      final name = entity.path.toLowerCase();
      if (name.endsWith('.pdf') || name.endsWith('.xlsx') || name.endsWith('.csv')) {
        files.add(entity);
      }
    }
    files.sort((a, b) => b.statSync().modified.compareTo(a.statSync().modified));
    if (mounted) setState(() { _files = files; _loading = false; });
  }

  String _name(File file) => file.path.split(Platform.pathSeparator).last;

  Future<void> _open(File file) async {
    final uri = Uri.file(file.path);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No compatible app found to open this file.')));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Download Center'), actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))]),
    body: _loading
      ? const Center(child: CircularProgressIndicator())
      : _files.isEmpty
        ? const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('No archived reports or PDFs yet. Download a report, payroll, inventory Excel or QR PDF and it will appear here.')))
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: _files.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final f = _files[i];
                final stat = f.statSync();
                return Card(child: ListTile(
                  leading: Icon(_name(f).toLowerCase().endsWith('.pdf') ? Icons.picture_as_pdf_outlined : Icons.table_view_outlined),
                  title: Text(_name(f), maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Text('${(stat.size / 1024).toStringAsFixed(1)} KB • ${stat.modified.toLocal()}'),
                  trailing: const Icon(Icons.open_in_new),
                  onTap: () => _open(f),
                ));
              },
            ),
          ),
  );
}
