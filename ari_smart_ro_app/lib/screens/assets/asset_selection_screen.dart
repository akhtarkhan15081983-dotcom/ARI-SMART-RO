import 'package:flutter/material.dart';

import '../../models/asset_model.dart';
import '../../services/asset_service.dart';
import '../../utils/search_utils.dart';

class AssetSelectionScreen extends StatefulWidget {
  const AssetSelectionScreen({super.key});

  @override
  State<AssetSelectionScreen> createState() => _AssetSelectionScreenState();
}

class _AssetSelectionScreenState extends State<AssetSelectionScreen> {
  final AssetService service = AssetService();
  final _searchController = TextEditingController();
  late Future<List<AssetModel>> futureAssets;
  String _query = '';
  String _status = 'ALL';

  @override
  void initState() {
    super.initState();
    futureAssets = service.getAssets();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Select RO Machine")),
      body: FutureBuilder<List<AssetModel>>(
        future: futureAssets,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text(snapshot.error.toString()));
          }

          final assets = snapshot.data ?? const <AssetModel>[];
          final statuses = <String>{
            'ALL',
            ...assets.map((asset) => asset.status.trim().toUpperCase()).where((value) => value.isNotEmpty),
          }.toList();
          final filtered = assets.where((asset) {
            if (_status != 'ALL' && asset.status.trim().toUpperCase() != _status) return false;
            return matchesAllSearchTerms(_query, [
              asset.assetId,
              asset.serialNumber,
              asset.roModelName,
              asset.status,
              asset.id.toString(),
            ]);
          }).toList();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
                child: TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    hintText: 'Search asset ID, serial, RO model or status...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
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
                    padding: const EdgeInsets.symmetric(horizontal: 12),
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
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 2),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('${filtered.length} of ${assets.length} machines'),
                ),
              ),
              Expanded(
                child: assets.isEmpty
                    ? const Center(child: Text("No Machine Available"))
                    : filtered.isEmpty
                        ? const Center(child: Text('No matching machine found'))
                        : ListView.builder(
                            itemCount: filtered.length,
                            itemBuilder: (context, index) {
                              final asset = filtered[index];
                              return Card(
                                margin: const EdgeInsets.all(10),
                                child: ListTile(
                                  leading: const Icon(Icons.water_drop),
                                  title: Text(asset.assetId),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text("Status : ${asset.status}"),
                                      Text(asset.roModelName),
                                      Text("Serial : ${asset.serialNumber}"),
                                    ],
                                  ),
                                  onTap: () => Navigator.pop(context, asset),
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
