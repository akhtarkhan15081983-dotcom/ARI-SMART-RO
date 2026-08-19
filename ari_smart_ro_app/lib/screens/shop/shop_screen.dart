import 'package:flutter/material.dart';

import '../../models/shop_product_model.dart';
import '../../services/shop_service.dart';

class ShopScreen extends StatefulWidget {
  const ShopScreen({super.key, this.service = const ShopService()});

  final ShopService service;

  @override
  State<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends State<ShopScreen> {
  final _searchController = TextEditingController();
  late Future<List<ShopProduct>> _catalog;

  @override
  void initState() {
    super.initState();
    _catalog = widget.service.fetchCatalog();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _search() {
    setState(() {
      _catalog = widget.service.fetchCatalog(query: _searchController.text);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Shop')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _search(),
              decoration: InputDecoration(
                hintText: 'Search RO models',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  onPressed: _search,
                  icon: const Icon(Icons.arrow_forward),
                ),
                border: const OutlineInputBorder(),
              ),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<ShopProduct>>(
              future: _catalog,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text('Unable to load shop products'),
                        const SizedBox(height: 12),
                        FilledButton(onPressed: _search, child: const Text('Retry')),
                      ],
                    ),
                  );
                }
                final products = snapshot.data ?? const <ShopProduct>[];
                if (products.isEmpty) {
                  return const Center(child: Text('No products available'));
                }
                return RefreshIndicator(
                  onRefresh: () async {
                    _search();
                    await _catalog;
                  },
                  child: ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                    itemCount: products.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder: (context, index) {
                      final product = products[index];
                      return Card(
                        child: ListTile(
                          leading: const CircleAvatar(child: Icon(Icons.water_drop)),
                          title: Text(product.modelName),
                          subtitle: Text(
                            '${product.categoryName} • ${product.capacity}\n'
                            '${product.warrantyMonths} months warranty',
                          ),
                          isThreeLine: true,
                          trailing: Text(
                            '₹${product.sellingPrice.toStringAsFixed(0)}',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
