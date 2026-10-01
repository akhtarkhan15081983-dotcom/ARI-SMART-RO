import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../services/ro_parts_passport_service.dart';

class ROPartsPassportCustomerCard extends StatefulWidget {
  const ROPartsPassportCustomerCard({super.key});

  @override
  State<ROPartsPassportCustomerCard> createState() =>
      _ROPartsPassportCustomerCardState();
}

class _ROPartsPassportCustomerCardState
    extends State<ROPartsPassportCustomerCard> {
  final ROPartsPassportService _service = const ROPartsPassportService();
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = _service.customerPassport();
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() => _future = _service.customerPassport());
    await _future;
  }

  String _formatDateTime(dynamic value) {
    final raw = (value ?? '').toString().trim();
    if (raw.isEmpty) return 'Not verified yet';
    try {
      final parsed = DateTime.parse(raw).toLocal();
      return DateFormat('dd MMM yyyy • hh:mm a').format(parsed);
    } catch (_) {
      return raw;
    }
  }

  String _statusLabel(dynamic value) {
    final raw = (value ?? '').toString().trim();
    if (raw.isEmpty) return 'ACTIVE';
    return raw.replaceAll('_', ' ').toUpperCase();
  }

  Future<void> _showPhoto({required String url, required String label}) async {
    if (url.isEmpty || !mounted) return;
    await showDialog<void>(
      context: context,
      barrierColor: Colors.black87,
      builder: (context) => Dialog.fullscreen(
        backgroundColor: Colors.black,
        child: SafeArea(
          child: Stack(
            children: [
              Positioned.fill(
                child: InteractiveViewer(
                  minScale: 1,
                  maxScale: 4,
                  child: Center(
                    child: Image.network(
                      url,
                      fit: BoxFit.contain,
                      errorBuilder: (_, __, ___) => const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.broken_image_outlined,
                            color: Colors.white70,
                            size: 54,
                          ),
                          SizedBox(height: 12),
                          Text(
                            'Unable to load this RO photo.',
                            style: TextStyle(color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Positioned(
                top: 8,
                left: 8,
                child: IconButton.filled(
                  tooltip: 'Close',
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ),
              Positioned(
                left: 16,
                right: 16,
                bottom: 18,
                child: Center(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: .72),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      label,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Card(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            ),
          );
        }
        if (snapshot.hasError) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Icon(Icons.cloud_off_outlined, size: 34),
                  const SizedBox(height: 8),
                  const Text(
                    'RO parts passport could not be loaded.',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                ],
              ),
            ),
          );
        }

        final data = snapshot.data ?? const <String, dynamic>{};
        final assets = data['assets'] as List<dynamic>? ?? const [];
        if (assets.isEmpty) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.document_scanner_outlined),
                      const SizedBox(width: 10),
                      Text(
                        'RO Visual Parts Passport',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Your engineer has not created the first 3–4 photo RO baseline yet. It will appear here after the next verified visit.',
                  ),
                ],
              ),
            ),
          );
        }

        return Column(
          children: assets.whereType<Map>().map((raw) {
            return _assetCard(Map<String, dynamic>.from(raw));
          }).toList(),
        );
      },
    );
  }

  Widget _passportFact({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 16),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 5),
            Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ],
        ),
      ),
    );
  }

  Widget _assetCard(Map<String, dynamic> asset) {
    final photos = asset['photos'] as List<dynamic>? ?? const [];
    final parts = asset['parts'] as List<dynamic>? ?? const [];
    final history = asset['replacement_history'] as List<dynamic>? ?? const [];
    final assetNumber = (asset['asset_number'] ?? '').toString();
    final serialNumber = (asset['serial_number'] ?? '').toString().trim();
    final roModel = (asset['ro_model'] ?? '').toString();
    final status = _statusLabel(asset['status']);
    final lastVisualCheck = _formatDateTime(asset['last_visual_check']);

    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            color: Theme.of(context).colorScheme.primaryContainer,
            child: Row(
              children: [
                const CircleAvatar(child: Icon(Icons.water_drop_outlined)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'MY RO • DIGITAL PASSPORT',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        assetNumber.isEmpty ? roModel : assetNumber,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      if (roModel.isNotEmpty && roModel != assetNumber)
                        Text(roModel),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Refresh',
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            child: Row(
              children: [
                _passportFact(
                  icon: Icons.qr_code_2,
                  label: 'RO Serial',
                  value: serialNumber.isEmpty ? 'Not recorded' : serialNumber,
                ),
                const SizedBox(width: 10),
                _passportFact(
                  icon: Icons.verified_outlined,
                  label: 'RO Status',
                  value: status,
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.fact_check_outlined, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Last verified visual check',
                          style: Theme.of(context).textTheme.labelMedium,
                        ),
                        const SizedBox(height: 3),
                        Text(
                          lastVisualCheck,
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (photos.isNotEmpty) ...[
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Text(
                'Latest verified RO photos',
                style: TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
            SizedBox(
              height: 150,
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                scrollDirection: Axis.horizontal,
                itemCount: photos.length,
                separatorBuilder: (_, __) => const SizedBox(width: 10),
                itemBuilder: (_, index) {
                  final item = photos[index] is Map
                      ? Map<String, dynamic>.from(photos[index] as Map)
                      : const <String, dynamic>{};
                  final url = (item['url'] ?? '').toString();
                  final angle = (item['angle'] ?? '')
                      .toString()
                      .replaceAll('_', ' ');
                  final label = angle.isEmpty ? 'RO photo' : angle;
                  return SizedBox(
                    width: 190,
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: url.isEmpty
                            ? null
                            : () => _showPhoto(url: url, label: label),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              if (url.isNotEmpty)
                                Image.network(
                                  url,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) =>
                                      const ColoredBox(
                                        color: Color(0xFFF1F5F9),
                                        child: Icon(
                                          Icons.broken_image_outlined,
                                          size: 34,
                                        ),
                                      ),
                                )
                              else
                                const ColoredBox(
                                  color: Color(0xFFF1F5F9),
                                  child: Icon(
                                    Icons.image_not_supported_outlined,
                                    size: 34,
                                  ),
                                ),
                              Positioned(
                                left: 8,
                                bottom: 8,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 4,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: .65),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    label,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ),
                              if (url.isNotEmpty)
                                const Positioned(
                                  right: 8,
                                  top: 8,
                                  child: CircleAvatar(
                                    radius: 16,
                                    child: Icon(Icons.zoom_in, size: 18),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
            child: Row(
              children: [
                const Icon(Icons.settings_outlined, size: 20),
                const SizedBox(width: 8),
                Text(
                  'Identified parts (${parts.length})',
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
              ],
            ),
          ),
          if (parts.isEmpty)
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: Text('No confirmed visual parts record is available yet.'),
            )
          else
            ...parts.whereType<Map>().map((raw) {
              final item = Map<String, dynamic>.from(raw);
              final dateSource = (item['date_source'] ?? '').toString();
              final isBaseline = dateSource == 'BASELINE_ASSUMED';
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: isBaseline
                      ? Colors.orange.withValues(alpha: .12)
                      : Colors.green.withValues(alpha: .12),
                  child: Icon(
                    isBaseline
                        ? Icons.flag_outlined
                        : Icons.verified_outlined,
                    color: isBaseline
                        ? Colors.orange.shade800
                        : Colors.green.shade700,
                  ),
                ),
                title: Text(
                  (item['part_name'] ?? '').toString(),
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                subtitle: Text(
                  (item['date_label'] ?? 'Date not available').toString(),
                ),
              );
            }),
          if (history.isNotEmpty)
            ExpansionTile(
              leading: const Icon(Icons.history),
              title: const Text('Replacement history'),
              subtitle: Text(
                '${history.length} verified change record${history.length == 1 ? '' : 's'}',
              ),
              children: history.whereType<Map>().map((raw) {
                final item = Map<String, dynamic>.from(raw);
                final engineer = (item['engineer'] ?? '').toString();
                return ListTile(
                  dense: true,
                  title: Text((item['part_name'] ?? '').toString()),
                  subtitle: Text(
                    '${item['date_label'] ?? ''}${engineer.isEmpty ? '' : ' • $engineer'}',
                  ),
                );
              }).toList(),
            ),
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 10, 16, 16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.privacy_tip_outlined, size: 18),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'These photos and part records belong to your linked RO only. A baseline date means the first verified ARI scan; it does not claim the part was changed on that date.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
