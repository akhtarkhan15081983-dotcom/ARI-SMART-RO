import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/product_management_service.dart';

class ProductManagementScreen extends StatefulWidget {
  const ProductManagementScreen({super.key});

  @override
  State<ProductManagementScreen> createState() =>
      _ProductManagementScreenState();
}

class _ProductManagementScreenState extends State<ProductManagementScreen> {
  final _service = const ProductManagementService();
  final _search = TextEditingController();
  List<Map<String, dynamic>> _products = const [];
  List<Map<String, dynamic>> _categories = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final values = await Future.wait([
        _service.products(),
        _service.categories(),
      ]);
      if (!mounted) return;
      setState(() {
        _products = values[0];
        _categories = values[1];
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addCategory() async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add category'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Category name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    controller.dispose();
    if (name == null || name.isEmpty) return;
    try {
      await _service.createCategory(name);
      await _load();
    } catch (error) {
      _message(error.toString());
    }
  }

  Future<void> _openForm([Map<String, dynamic>? product]) async {
    final saved = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => _ProductFormScreen(
          product: product,
          categories: _categories,
          service: _service,
        ),
      ),
    );
    if (saved == true) await _load();
  }

  void _message(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    final query = _search.text.trim().toLowerCase();
    final visible = _products.where((product) {
      final text = [
        product['model_name'],
        product['category_name'],
        product['capacity'],
      ].join(' ').toLowerCase();
      return query.isEmpty || text.contains(query);
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Product Management'),
        actions: [
          IconButton(onPressed: _addCategory, icon: const Icon(Icons.category)),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _categories.isEmpty ? _addCategory : () => _openForm(),
        icon: const Icon(Icons.add),
        label: Text(_categories.isEmpty ? 'Add category' : 'Add product'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(_error!, textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    FilledButton(onPressed: _load, child: const Text('Retry')),
                  ],
                ),
              ),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                children: [
                  TextField(
                    controller: _search,
                    onChanged: (_) => setState(() {}),
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search),
                      hintText: 'Search name, category or capacity',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (visible.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(32),
                      child: Text(
                        'No products found. Add your first product.',
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ...visible.map(
                    (product) => Card(
                      child: ListTile(
                        leading: _ProductThumbnail(product: product),
                        title: Text(product['model_name']?.toString() ?? ''),
                        subtitle: Text(
                          '${product['category_name'] ?? ''} • ${product['capacity'] ?? ''}\n'
                          'Sale ₹${product['selling_price'] ?? 0} • Rent ₹${product['monthly_rent'] ?? 0}\n'
                          'Stock ${product['stock_quantity'] ?? 0} • ${product['is_active'] == true ? 'Active' : 'Inactive'}',
                        ),
                        isThreeLine: true,
                        trailing: const Icon(Icons.edit_outlined),
                        onTap: () => _openForm(product),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _ProductThumbnail extends StatelessWidget {
  const _ProductThumbnail({required this.product});
  final Map<String, dynamic> product;

  @override
  Widget build(BuildContext context) {
    final images = product['images'] as List<dynamic>? ?? const [];
    final url = images.isEmpty
        ? ''
        : (images.first as Map<String, dynamic>)['image_url']?.toString() ?? '';
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        width: 54,
        height: 54,
        child: url.isEmpty
            ? const ColoredBox(
                color: Color(0xFFE0F2FE),
                child: Icon(Icons.water_drop_outlined),
              )
            : Image.network(url, fit: BoxFit.cover),
      ),
    );
  }
}

class _ProductFormScreen extends StatefulWidget {
  const _ProductFormScreen({
    required this.product,
    required this.categories,
    required this.service,
  });

  final Map<String, dynamic>? product;
  final List<Map<String, dynamic>> categories;
  final ProductManagementService service;

  @override
  State<_ProductFormScreen> createState() => _ProductFormScreenState();
}

class _ProductFormScreenState extends State<_ProductFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final Map<String, TextEditingController> _fields = {};
  int? _categoryId;
  bool _forSale = true;
  bool _forRent = false;
  bool _active = true;
  bool _saving = false;
  XFile? _image;

  TextEditingController _controller(String key, [String fallback = '']) =>
      _fields.putIfAbsent(
        key,
        () => TextEditingController(
          text: widget.product?[key]?.toString() ?? fallback,
        ),
      );

  @override
  void initState() {
    super.initState();
    _categoryId =
        (widget.product?['category'] as num?)?.toInt() ??
        (widget.categories.firstOrNull?['id'] as num?)?.toInt();
    _forSale = widget.product?['available_for_sale'] as bool? ?? true;
    _forRent = widget.product?['available_for_rent'] as bool? ?? false;
    _active = widget.product?['is_active'] as bool? ?? true;
  }

  @override
  void dispose() {
    for (final controller in _fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _pickImage() async {
    final image = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
      maxWidth: 1600,
    );
    if (image != null && mounted) setState(() => _image = image);
  }

  num _number(String key) =>
      num.tryParse(_controller(key, '0').text.trim()) ?? 0;

  Future<void> _save() async {
    if (!_formKey.currentState!.validate() || _categoryId == null) return;
    if (!_forSale && !_forRent) {
      _show('Select Sale, Rent, or both.');
      return;
    }
    setState(() => _saving = true);
    try {
      final saved = await widget.service.saveProduct(
        id: (widget.product?['id'] as num?)?.toInt(),
        data: {
          'category': _categoryId,
          'model_name': _controller('model_name').text.trim(),
          'capacity': _controller('capacity').text.trim(),
          'business_type': _forRent && !_forSale ? 'RENT' : 'SALE',
          'available_for_sale': _forSale,
          'available_for_rent': _forRent,
          'selling_price': _number('selling_price'),
          'mrp': _number('mrp'),
          'monthly_rent': _number('monthly_rent'),
          'installation_charge': _number('installation_charge'),
          'security_deposit': _number('security_deposit'),
          'stock_quantity': _number('stock_quantity').toInt(),
          'warranty_months': _number('warranty_months').toInt(),
          'description': _controller('description').text.trim(),
          'features': _controller('features').text.trim(),
          'is_active': _active,
        },
      );
      if (_image != null) {
        await widget.service.uploadImage(
          (saved['id'] as num).toInt(),
          _image!.path,
        );
      }
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      _show(error.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _show(String message) => ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
  );

  Widget _text(
    String key,
    String label, {
    bool required = false,
    bool number = false,
    int lines = 1,
    String fallback = '',
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextFormField(
      controller: _controller(key, fallback),
      keyboardType: number
          ? const TextInputType.numberWithOptions(decimal: true)
          : TextInputType.text,
      maxLines: lines,
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      validator: required
          ? (value) => value == null || value.trim().isEmpty ? 'Required' : null
          : null,
    ),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.product == null ? 'Add Product' : 'Edit Product'),
    ),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          DropdownButtonFormField<int>(
            initialValue: _categoryId,
            decoration: const InputDecoration(
              labelText: 'Category',
              border: OutlineInputBorder(),
            ),
            items: widget.categories
                .map(
                  (category) => DropdownMenuItem<int>(
                    value: (category['id'] as num).toInt(),
                    child: Text(category['name']?.toString() ?? ''),
                  ),
                )
                .toList(),
            onChanged: (value) => setState(() => _categoryId = value),
          ),
          const SizedBox(height: 12),
          _text('model_name', 'Product / model name', required: true),
          _text('capacity', 'Capacity (example: 12 LPH)', required: true),
          SwitchListTile(
            title: const Text('Available for sale'),
            value: _forSale,
            onChanged: (v) => setState(() => _forSale = v),
          ),
          SwitchListTile(
            title: const Text('Available for rent'),
            value: _forRent,
            onChanged: (v) => setState(() => _forRent = v),
          ),
          if (_forSale) ...[
            _text(
              'selling_price',
              'Selling price',
              number: true,
              fallback: '0',
            ),
            _text('mrp', 'MRP', number: true, fallback: '0'),
          ],
          if (_forRent) ...[
            _text('monthly_rent', 'Monthly rent', number: true, fallback: '0'),
            _text(
              'security_deposit',
              'Security deposit',
              number: true,
              fallback: '0',
            ),
          ],
          _text(
            'installation_charge',
            'Installation charge',
            number: true,
            fallback: '0',
          ),
          _text(
            'stock_quantity',
            'Stock quantity',
            number: true,
            fallback: '0',
          ),
          _text(
            'warranty_months',
            'Warranty months',
            number: true,
            fallback: '12',
          ),
          _text('description', 'Description', lines: 3),
          _text('features', 'Features (one per line)', lines: 4),
          SwitchListTile(
            title: const Text('Active in shop'),
            value: _active,
            onChanged: (v) => setState(() => _active = v),
          ),
          OutlinedButton.icon(
            onPressed: _pickImage,
            icon: const Icon(Icons.add_photo_alternate_outlined),
            label: Text(
              _image == null ? 'Choose product photo' : 'Change product photo',
            ),
          ),
          if (_image != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Image.file(
                File(_image!.path),
                height: 180,
                fit: BoxFit.contain,
              ),
            ),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save),
            label: Text(_saving ? 'Saving...' : 'Save Product'),
          ),
        ],
      ),
    ),
  );
}
