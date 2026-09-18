import 'package:flutter/material.dart';

import '../../models/bag_item_model.dart';
import '../../services/bag_service.dart';
import '../../utils/search_utils.dart';

class MyBagScreen extends StatefulWidget {
  const MyBagScreen({super.key});

  @override
  State<MyBagScreen> createState() => _MyBagScreenState();
}

class _MyBagScreenState extends State<MyBagScreen> {
  final BagService bagService = BagService();
  final _searchController = TextEditingController();
  String _query = '';
  String _status = 'ALL';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("My Bag"), centerTitle: true),
      body: FutureBuilder<List<BagItemModel>>(
        future: bagService.getMyBag(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text(snapshot.error.toString()));
          }

          final items = snapshot.data ?? const <BagItemModel>[];
          final statuses = <String>{
            'ALL',
            ...items.map((item) => item.status.trim().toUpperCase()).where((value) => value.isNotEmpty),
          }.toList();

          final filtered = items.where((item) {
            final statusMatches = _status == 'ALL' || item.status.trim().toUpperCase() == _status;
            if (!statusMatches) return false;
            return matchesAllSearchTerms(_query, [
              item.partName,
              item.serialNumber ?? '',
              item.status,
              item.engineerName,
              item.employeeId,
              item.id.toString(),
            ]);
          }).toList();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(15, 15, 15, 8),
                child: TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    hintText: 'Search part, serial, status or employee...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Clear search',
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _query = '');
                            },
                            icon: const Icon(Icons.clear),
                          ),
                  ),
                ),
              ),
              if (statuses.length > 1)
                SizedBox(
                  height: 42,
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 15),
                    scrollDirection: Axis.horizontal,
                    itemCount: statuses.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 8),
                    itemBuilder: (context, index) {
                      final value = statuses[index];
                      return ChoiceChip(
                        label: Text(value == 'ALL' ? 'All' : value.replaceAll('_', ' ')),
                        selected: _status == value,
                        onSelected: (_) => setState(() => _status = value),
                      );
                    },
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(15, 8, 15, 4),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('${filtered.length} of ${items.length} parts'),
                ),
              ),
              Expanded(
                child: items.isEmpty
                    ? const Center(child: Text("No Parts Found"))
                    : filtered.isEmpty
                        ? const Center(child: Text('No matching parts found'))
                        : ListView.builder(
                            padding: const EdgeInsets.all(15),
                            itemCount: filtered.length,
                            itemBuilder: (context, index) {
                              final item = filtered[index];
                              return Card(
                                margin: const EdgeInsets.only(bottom: 12),
                                child: ListTile(
                                  leading: const CircleAvatar(child: Icon(Icons.inventory)),
                                  title: Text(item.partName),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text("Serial : ${item.serialNumber ?? "N/A"}"),
                                      Text("Status : ${item.status}"),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
              ),
            ],
          );
        },
      ),
    );
  }
}
