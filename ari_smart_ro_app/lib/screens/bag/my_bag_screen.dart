import 'package:flutter/material.dart';

import '../../models/bag_item_model.dart';
import '../../services/bag_service.dart';

class MyBagScreen extends StatelessWidget {
  MyBagScreen({super.key});

  final BagService bagService = BagService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("My Bag"),
        centerTitle: true,
      ),
      body: FutureBuilder<List<BagItemModel>>(
        future: bagService.getMyBag(),
        builder: (context, snapshot) {
          if (snapshot.connectionState ==
              ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Text(snapshot.error.toString()),
            );
          }

          final items = snapshot.data ?? [];

          if (items.isEmpty) {
            return const Center(
              child: Text("No Parts Found"),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(15),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];

              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: const CircleAvatar(
                    child: Icon(Icons.inventory),
                  ),
                  title: Text(item.partName),
                  subtitle: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Serial : ${item.serialNumber ?? "N/A"}",
                      ),
                      Text(
                        "Status : ${item.status}",
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