import 'package:flutter/material.dart';

import '../../services/role_permission_service.dart';

class RoleAccessControlScreen extends StatefulWidget {
  const RoleAccessControlScreen({super.key});

  @override
  State<RoleAccessControlScreen> createState() => _RoleAccessControlScreenState();
}

class _RoleAccessControlScreenState extends State<RoleAccessControlScreen> {
  final _service = const RolePermissionService();
  final _roles = const ['MANAGER', 'OFFICE', 'CALLING', 'ENGINEER'];
  String _role = 'MANAGER';
  bool _loading = true;
  List<Map<String, dynamic>> _catalog = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _service.getPermissions(role: _role);
      if (!mounted) return;
      setState(() {
        _catalog = (data['catalog'] as List<dynamic>? ?? const [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
      });
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _toggle(Map<String, dynamic> row, bool allowed) async {
    final index = _catalog.indexOf(row);
    final previous = row['allowed'] == true;
    setState(() => _catalog[index] = {...row, 'allowed': allowed});
    try {
      await _service.updatePermission(
        role: _role,
        featureKey: row['key'].toString(),
        isAllowed: allowed,
      );
    } catch (error) {
      if (mounted) {
        setState(() => _catalog[index] = {...row, 'allowed': previous});
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Role Access Control')),
        body: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'Admin Permission Center',
                          style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Select a role and allow only the cards/functions that role needs. Admin always keeps full control.',
                        ),
                        const SizedBox(height: 14),
                        DropdownButtonFormField<String>(
                          initialValue: _role,
                          decoration: const InputDecoration(labelText: 'Role'),
                          items: _roles
                              .map(
                                (role) => DropdownMenuItem(
                                  value: role,
                                  child: Text(role),
                                ),
                              )
                              .toList(),
                          onChanged: (value) async {
                            if (value == null) return;
                            setState(() => _role = value);
                            await _load();
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                          itemCount: _catalog.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 6),
                          itemBuilder: (_, index) {
                            final row = _catalog[index];
                            return Card(
                              child: SwitchListTile(
                                value: row['allowed'] == true,
                                onChanged: (value) => _toggle(row, value),
                                secondary: Icon(
                                  row['allowed'] == true
                                      ? Icons.lock_open_rounded
                                      : Icons.lock_outline_rounded,
                                ),
                                title: Text(
                                  row['label']?.toString() ?? row['key'].toString(),
                                  style: const TextStyle(fontWeight: FontWeight.w800),
                                ),
                                subtitle: Text(row['key'].toString()),
                              ),
                            );
                          },
                        ),
                      ),
              ),
            ],
          ),
        ),
      );
}
