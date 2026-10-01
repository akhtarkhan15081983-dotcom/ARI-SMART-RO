import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/download_center_file_service.dart';

class DownloadCenterScreen extends StatefulWidget {
  const DownloadCenterScreen({super.key});
  @override
  State<DownloadCenterScreen> createState() => _DownloadCenterScreenState();
}

class _DownloadCenterScreenState extends State<DownloadCenterScreen> {
  static const MethodChannel _downloadsChannel = MethodChannel('com.arismartro.app/downloads');
  bool _loading = true;
  List<File> _files = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) setState(() => _loading = true);
    try {
      final root = await getApplicationDocumentsDirectory();
      final files = await discoverDownloadCenterFiles(root);
      if (mounted) {
        setState(() {
          _files = files;
          _loading = false;
        });
      }
    } on FileSystemException catch (error) {
      if (!mounted) return;
      setState(() {
        _files = const [];
        _loading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Unable to read Download Center: ${error.message}')),
      );
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _files = const [];
        _loading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to refresh Download Center right now.')),
      );
    }
  }

  String _name(File file) => file.path.split(Platform.pathSeparator).last;

  Future<void> _open(File file) async {
    if (!await file.exists()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('This file is no longer available. Refreshing the list.')),
        );
      }
      await _load();
      return;
    }
    try {
      var opened = false;
      if (Platform.isAndroid) {
        opened = await _downloadsChannel.invokeMethod<bool>(
              'openFile',
              {'path': file.path},
            ) ??
            false;
      } else {
        final uri = Uri.file(file.path);
        opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
      if (!opened && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No compatible app found to open this file.')),
        );
      }
    } on PlatformException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error.code == 'OPEN_DENIED'
                  ? 'This file cannot be opened from outside ARI SMART RO storage.'
                  : 'Unable to open this file. It may be unavailable or unsupported.',
            ),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Unable to open this file. It may be unavailable or unsupported.')),
        );
      }
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
                FileStat? stat;
                try {
                  stat = f.statSync();
                } on FileSystemException {
                  stat = null;
                }
                return Card(child: ListTile(
                  leading: Icon(_name(f).toLowerCase().endsWith('.pdf') ? Icons.picture_as_pdf_outlined : Icons.table_view_outlined),
                  title: Text(_name(f), maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Text(
                    stat == null
                        ? 'File unavailable • pull to refresh'
                        : '${(stat.size / 1024).toStringAsFixed(1)} KB • ${stat.modified.toLocal()}',
                  ),
                  trailing: const Icon(Icons.open_in_new),
                  onTap: () => _open(f),
                ));
              },
            ),
          ),
  );
}
