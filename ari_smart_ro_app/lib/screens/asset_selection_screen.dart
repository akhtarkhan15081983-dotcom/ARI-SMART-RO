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

  late Future<List<AssetModel>> futureAssets;
  final _searchController = TextEditingController();
  String _query = '';
  String _statusFilter = 'ALL';

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
          final statuses = <String>{'ALL', ...assets.map((a) => a.status.toUpperCase())}.toList();
          final filtered = assets.where((asset) {
            if (_statusFilter != 'ALL' && asset.status.toUpperCase() != _statusFilter) return false;
            return matchesAllSearchTerms(_query, [asset.assetId, asset.serialNumber, asset.roModelName, asset.status, asset.id.toString()]);
          }).toList();

          if (assets.isEmpty) {
            return const Center(child: Text("No Machine Available"));
          }

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
                child: TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onChanged: (value) => setState(() => _query = value),
                  decoration: InputDecoration(
                    hintText: 'Search asset ID, serial, model or status...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _query.isEmpty ? null : IconButton(
                      onPressed: () { _searchController.clear(); setState(() => _query = ''); },
                      icon: const Icon(Icons.clear),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: DropdownButtonFormField<String>(
                  initialValue: _statusFilter,
                  decoration: const InputDecoration(labelText: 'Status filter'),
                  items: statuses.map((v) => DropdownMenuItem(value: v, child: Text(v == 'ALL' ? 'All statuses' : v.replaceAll('_', ' ')))).toList(),
                  onChanged: (v) => setState(() => _statusFilter = v ?? 'ALL'),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 2),
                child: Align(alignment: Alignment.centerLeft, child: Text('${filtered.length} of ${assets.length} machines')),
              ),
              Expanded(child: filtered.isEmpty
                  ? const Center(child: Text('No matching machine found'))
                  : ListView.builder(
            itemCount: filtered.length,

            itemBuilder: (context, index) {
              final asset = filtered[index];

              return Card(
                margin: const EdgeInsets.all(8),

                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.water_drop,
                        color: Colors.blue,
                        size: 35,
                      ),

                      const SizedBox(width: 12),

                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              asset.assetId,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),

                            const SizedBox(height: 5),

                            Text("Status : ${asset.status}"),
                            Text("Serial : ${asset.serialNumber}"),
                          ],
                        ),
                      ),

                      ElevatedButton(
                        onPressed: () {
                          Navigator.pop(context, asset);
                        },
                        child: const Text("Select"),
                      ),
                    ],
                  ),
                ),
              );
            },
          )),
            ],
          );
        },
      ),
    );
  }
}
