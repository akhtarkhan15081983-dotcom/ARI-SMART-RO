import 'package:flutter/material.dart';

import '../../models/bag_item_model.dart';
import '../../services/bag_service.dart';

class EngineerBagAdminScreen extends StatefulWidget {
  const EngineerBagAdminScreen({super.key});

  @override
  State<EngineerBagAdminScreen> createState() => _EngineerBagAdminScreenState();
}

class _EngineerBagAdminScreenState extends State<EngineerBagAdminScreen> {
  final BagService _service = BagService();
  late Future<List<BagItemModel>> _items;

  @override
  void initState() {
    super.initState();
    _items = _service.getAdminEngineerBags();
  }

  Future<void> _refresh() async {
    final next = _service.getAdminEngineerBags();
    setState(() => _items = next);
    await next;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Engineer Bags')),
      body: FutureBuilder<List<BagItemModel>>(
        future: _items,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 52),
                    const SizedBox(height: 12),
                    Text(
                      'Engineer bags load nahi ho sake.\n${snapshot.error}',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _refresh,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }

          final items = snapshot.data ?? const <BagItemModel>[];
          final groups = <int, List<BagItemModel>>{};
          for (final item in items) {
            groups.putIfAbsent(item.engineerId ?? -1, () => []).add(item);
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: groups.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: const [
                      SizedBox(height: 180),
                      Icon(
                        Icons.backpack_outlined,
                        size: 56,
                        color: Colors.grey,
                      ),
                      SizedBox(height: 12),
                      Center(
                        child: Text(
                          'Kisi engineer ko koi part issue nahi hai.',
                        ),
                      ),
                    ],
                  )
                : ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    children: groups.values.map((bagItems) {
                      final engineer = bagItems.first;
                      final name = engineer.engineerName.trim().isEmpty
                          ? 'Engineer'
                          : engineer.engineerName.trim();
                      return Card(
                        margin: const EdgeInsets.only(bottom: 14),
                        child: ExpansionTile(
                          leading: const CircleAvatar(
                            child: Icon(Icons.engineering),
                          ),
                          title: Text(name),
                          subtitle: Text(
                            '${engineer.employeeId} • ${bagItems.length} issued part(s)',
                          ),
                          children: bagItems
                              .map(
                                (item) => ListTile(
                                  leading: const Icon(
                                    Icons.inventory_2_outlined,
                                  ),
                                  title: Text(item.partName),
                                  subtitle: Text(
                                    'Serial: ${item.serialNumber?.trim().isNotEmpty == true ? item.serialNumber : 'N/A'}',
                                  ),
                                  trailing: const Chip(label: Text('ISSUED')),
                                ),
                              )
                              .toList(),
                        ),
                      );
                    }).toList(),
                  ),
          );
        },
      ),
    );
  }
}
