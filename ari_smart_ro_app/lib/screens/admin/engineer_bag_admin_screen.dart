import 'package:flutter/material.dart';

import '../../models/bag_item_model.dart';
import '../../services/bag_service.dart';
import '../../utils/search_utils.dart';

class EngineerBagAdminScreen extends StatefulWidget {
  const EngineerBagAdminScreen({super.key});

  @override
  State<EngineerBagAdminScreen> createState() => _EngineerBagAdminScreenState();
}

class _EngineerBagAdminScreenState extends State<EngineerBagAdminScreen> {
  final BagService _service = BagService();
  late Future<List<BagItemModel>> _items;
  final _searchController = TextEditingController();
  String _query = '';

  @override
  void initState() {
    super.initState();
    _items = _service.getAdminEngineerBags();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
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
          final filtered = items.where((item) => matchesAllSearchTerms(_query, [
            item.partName,
            item.serialNumber ?? '',
            item.status,
            item.engineerName,
            item.employeeId,
            item.id.toString(),
          ])).toList();
          final groups = <int, List<BagItemModel>>{};
          for (final item in filtered) {
            groups.putIfAbsent(item.engineerId ?? -1, () => []).add(item);
          }

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                child: TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    hintText: 'Search employee, ID, part, serial or status...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty ? null : IconButton(
                      onPressed: () { _searchController.clear(); setState(() => _query = ''); },
                      icon: const Icon(Icons.clear),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: Align(alignment: Alignment.centerLeft, child: Text('${filtered.length} of ${items.length} issued parts')),
              ),
              Expanded(child: RefreshIndicator(
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
              )),
            ],
          );
        },
      ),
    );
  }
}
