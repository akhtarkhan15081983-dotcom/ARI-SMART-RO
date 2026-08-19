import 'package:flutter/material.dart';

import '../../models/asset_model.dart';
import '../../services/asset_service.dart';

class AssetSelectionScreen extends StatefulWidget {
  const AssetSelectionScreen({super.key});

  @override
  State<AssetSelectionScreen> createState() =>
      _AssetSelectionScreenState();
}

class _AssetSelectionScreenState
    extends State<AssetSelectionScreen> {

  final AssetService service = AssetService();

  late Future<List<AssetModel>> futureAssets;

  @override
  void initState() {
    super.initState();

    futureAssets = service.getAssets();
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text("Select RO Machine"),
      ),

      body: FutureBuilder<List<AssetModel>>(

        future: futureAssets,

        builder: (context, snapshot) {

          if (snapshot.connectionState ==
              ConnectionState.waiting) {

            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {

            return Center(
              child: Text(
                snapshot.error.toString(),
              ),
            );
          }

          final assets = snapshot.data!;
          print("TOTAL ASSETS = ${assets.length}");

          if (assets.isEmpty) {

            return const Center(
              child: Text("No Machine Available"),
            );
          }

          return ListView.builder(

            itemCount: assets.length,

            itemBuilder: (context, index) {

              final asset = assets[index];
              print("ASSET : ${asset.assetId}");

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
          );
        },
      ),
    );
  }
}