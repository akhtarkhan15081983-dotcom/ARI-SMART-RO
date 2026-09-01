import 'package:flutter/material.dart';

import '../../core/app_colors.dart';
import '../../services/saas_admin_service.dart';
import 'saas_company_onboarding_screen.dart';

class SaasSuperAdminScreen extends StatefulWidget {
  const SaasSuperAdminScreen({super.key});

  @override
  State<SaasSuperAdminScreen> createState() => _SaasSuperAdminScreenState();
}

class _SaasSuperAdminScreenState extends State<SaasSuperAdminScreen> {
  final _service = const SaasAdminService();
  final _search = TextEditingController();
  Map<String, dynamic>? _data;
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
      final data = await _service.dashboard();
      if (mounted) setState(() => _data = data);
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error.toString().replaceFirst('Exception: ', ''),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> get _companies {
    final rows = (_data?['companies'] as List<dynamic>? ?? const [])
        .map((row) => Map<String, dynamic>.from(row as Map))
        .toList();
    final query = _search.text.trim().toLowerCase();
    if (query.isEmpty) return rows;
    return rows.where((row) {
      return [
        'name',
        'phone',
        'city',
        'plan',
        'subscription_status',
      ].any((key) => row[key].toString().toLowerCase().contains(query));
    }).toList();
  }

  Future<void> _manage(Map<String, dynamic> company) async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 4, 18, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                company['name'].toString(),
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 4),
              Text('${company['plan']} • ${company['subscription_status']}'),
              Text('Workspace: ${company['lifecycle_status'] ?? 'ACTIVE'}'),
              const SizedBox(height: 16),
              ListTile(
                leading: const Icon(
                  Icons.edit_note_rounded,
                  color: AppColors.primary,
                ),
                title: const Text('Edit company details & branding'),
                subtitle: const Text(
                  'Name, contact, address, colours and customer experience',
                ),
                onTap: () => Navigator.pop(context, 'EDIT'),
              ),
              const Divider(),
              const Text(
                'SUBSCRIPTION',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
              ),
              ...const [
                (
                  'ACTIVE',
                  'Activate subscription',
                  Icons.verified_rounded,
                  AppColors.success,
                ),
                (
                  'PAUSED',
                  'Pause access',
                  Icons.pause_circle_outline,
                  AppColors.warning,
                ),
                (
                  'PAST_DUE',
                  'Mark payment overdue',
                  Icons.error_outline,
                  AppColors.error,
                ),
                (
                  'CANCELLED',
                  'Cancel subscription',
                  Icons.cancel_outlined,
                  AppColors.error,
                ),
              ].map(
                (action) => ListTile(
                  leading: Icon(action.$3, color: action.$4),
                  title: Text(action.$2),
                  onTap: () => Navigator.pop(context, 'SUB:${action.$1}'),
                ),
              ),
              const Divider(),
              const Text(
                'COMPANY LIFECYCLE',
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
              ),
              ...[
                (
                  'SUSPEND',
                  'Suspend workspace',
                  Icons.lock_clock_outlined,
                  AppColors.warning,
                ),
                (
                  'DEACTIVATE',
                  'Deactivate company',
                  Icons.block_rounded,
                  AppColors.error,
                ),
                (
                  'ARCHIVE',
                  'Archive company',
                  Icons.archive_outlined,
                  AppColors.textSecondary,
                ),
                (
                  'RESTORE',
                  'Restore company',
                  Icons.restore_rounded,
                  AppColors.success,
                ),
                if (company['lifecycle_status'] == 'ARCHIVED')
                  (
                    'REQUEST_DELETION',
                    'Schedule permanent deletion',
                    Icons.delete_forever_outlined,
                    AppColors.error,
                  ),
                if (company['lifecycle_status'] == 'PENDING_DELETION')
                  (
                    'CANCEL_DELETION',
                    'Cancel scheduled deletion',
                    Icons.settings_backup_restore,
                    AppColors.success,
                  ),
                if (company['lifecycle_status'] == 'PENDING_DELETION')
                  (
                    'PURGE',
                    'Permanently delete after grace period',
                    Icons.delete_forever_rounded,
                    AppColors.error,
                  ),
              ].map(
                (action) => ListTile(
                  leading: Icon(action.$3, color: action.$4),
                  title: Text(action.$2),
                  onTap: () => Navigator.pop(context, 'LIFE:${action.$1}'),
                ),
              ),
              ListTile(
                leading: const Icon(
                  Icons.history_rounded,
                  color: AppColors.primary,
                ),
                title: const Text('View audit history'),
                onTap: () => Navigator.pop(context, 'HISTORY'),
              ),
            ],
          ),
        ),
      ),
    );
    if (selected == null) return;
    // Let the modal bottom-sheet finish removing its inherited widget tree
    // before another route/dialog is pushed on the same Navigator.
    await Future<void>.delayed(const Duration(milliseconds: 350));
    if (!mounted) return;
    if (selected == 'EDIT') {
      await _editCompany(company);
      return;
    }
    if (selected == 'HISTORY') {
      await _showHistory(company);
      return;
    }
    try {
      if (selected.startsWith('SUB:')) {
        await _service.updateSubscriptionStatus(
          (company['id'] as num).toInt(),
          selected.substring(4),
        );
      } else {
        final action = selected.substring(5);
        if (action == 'PURGE') {
          final confirmed = await _confirmPermanentDeletion(company);
          if (!confirmed) return;
          await _load();
          return;
        }
        final reason = await _askReason(action);
        if (reason == null) return;
        await _service.updateCompanyLifecycle(
          (company['id'] as num).toInt(),
          action,
          reason,
        );
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${company['name']} updated successfully.')),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  Future<void> _editCompany(Map<String, dynamic> row) async {
    try {
      final company = await _service.companyDetails((row['id'] as num).toInt());
      if (!mounted) return;
      final name = TextEditingController(text: company['name']?.toString());
      final appName = TextEditingController(
        text: company['app_display_name']?.toString(),
      );
      final phone = TextEditingController(text: company['phone']?.toString());
      final email = TextEditingController(text: company['email']?.toString());
      final supportPhone = TextEditingController(
        text: company['support_phone']?.toString(),
      );
      final tagline = TextEditingController(
        text: company['tagline']?.toString(),
      );
      final welcome = TextEditingController(
        text: company['welcome_message']?.toString(),
      );
      final address = TextEditingController(
        text: company['address']?.toString(),
      );
      final city = TextEditingController(text: company['city']?.toString());
      final state = TextEditingController(text: company['state']?.toString());
      var showShop = company['show_public_shop'] == true;
      final saved =
          await showDialog<bool>(
            context: context,
            builder: (context) => StatefulBuilder(
              builder: (context, setDialogState) => AlertDialog(
                title: const Text('Edit company'),
                content: SizedBox(
                  width: 520,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextField(
                          controller: name,
                          decoration: const InputDecoration(
                            labelText: 'Company name',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: appName,
                          decoration: const InputDecoration(
                            labelText: 'App display name',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: phone,
                          keyboardType: TextInputType.phone,
                          decoration: const InputDecoration(
                            labelText: 'Company phone',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: email,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            labelText: 'Company email',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: supportPhone,
                          keyboardType: TextInputType.phone,
                          decoration: const InputDecoration(
                            labelText: 'Support phone',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: tagline,
                          decoration: const InputDecoration(
                            labelText: 'Brand tagline',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: welcome,
                          maxLines: 3,
                          decoration: const InputDecoration(
                            labelText: 'Welcome message',
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: address,
                          maxLines: 2,
                          decoration: const InputDecoration(
                            labelText: 'Address',
                          ),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: city,
                                decoration: const InputDecoration(
                                  labelText: 'City',
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: state,
                                decoration: const InputDecoration(
                                  labelText: 'State',
                                ),
                              ),
                            ),
                          ],
                        ),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Enable public company shop'),
                          value: showShop,
                          onChanged: (value) =>
                              setDialogState(() => showShop = value),
                        ),
                      ],
                    ),
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('CANCEL'),
                  ),
                  FilledButton(
                    onPressed: () async {
                      if (name.text.trim().isEmpty ||
                          phone.text.trim().length != 10) {
                        return;
                      }
                      try {
                        await _service
                            .updateCompany((row['id'] as num).toInt(), {
                              'name': name.text.trim(),
                              'app_display_name': appName.text.trim(),
                              'phone': phone.text.trim(),
                              'email': email.text.trim(),
                              'support_phone': supportPhone.text.trim(),
                              'tagline': tagline.text.trim(),
                              'welcome_message': welcome.text.trim(),
                              'address': address.text.trim(),
                              'city': city.text.trim(),
                              'state': state.text.trim(),
                              'show_public_shop': showShop,
                            });
                        if (context.mounted) Navigator.pop(context, true);
                      } catch (error) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                error.toString().replaceFirst(
                                  'Exception: ',
                                  '',
                                ),
                              ),
                            ),
                          );
                        }
                      }
                    },
                    child: const Text('SAVE CHANGES'),
                  ),
                ],
              ),
            ),
          ) ??
          false;
      // showDialog completes when pop starts; controllers must remain alive
      // until the dialog route's reverse transition has fully completed.
      await Future<void>.delayed(const Duration(milliseconds: 350));
      for (final controller in [
        name,
        appName,
        phone,
        email,
        supportPhone,
        tagline,
        welcome,
        address,
        city,
        state,
      ]) {
        controller.dispose();
      }
      if (saved) {
        await _load();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Company details updated successfully.'),
            ),
          );
        }
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  Future<bool> _confirmPermanentDeletion(Map<String, dynamic> company) async {
    final slugController = TextEditingController();
    final reasonController = TextEditingController();
    final confirmed =
        await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Permanent deletion'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'This cannot be undone. The 30-day grace period must be complete and the subscription cancelled.',
                  ),
                  const SizedBox(height: 14),
                  Text('Type ${company['slug']} to confirm.'),
                  const SizedBox(height: 8),
                  TextField(
                    controller: slugController,
                    decoration: const InputDecoration(
                      labelText: 'Company slug',
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: reasonController,
                    maxLines: 3,
                    decoration: const InputDecoration(
                      labelText: 'Detailed deletion reason',
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('CANCEL'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: AppColors.error),
                onPressed: () async {
                  try {
                    await _service.permanentlyDeleteCompany(
                      (company['id'] as num).toInt(),
                      slugController.text.trim(),
                      reasonController.text.trim(),
                    );
                    if (context.mounted) Navigator.pop(context, true);
                  } catch (error) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            error.toString().replaceFirst('Exception: ', ''),
                          ),
                        ),
                      );
                    }
                  }
                },
                child: const Text('DELETE PERMANENTLY'),
              ),
            ],
          ),
        ) ??
        false;
    slugController.dispose();
    reasonController.dispose();
    return confirmed;
  }

  Future<String?> _askReason(String action) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(action.replaceAll('_', ' ')),
        content: TextField(
          controller: controller,
          autofocus: true,
          maxLines: 3,
          maxLength: 500,
          decoration: const InputDecoration(
            labelText: 'Reason (required)',
            hintText: 'Enter a clear operational reason',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () {
              final reason = controller.text.trim();
              if (reason.length >= 5) Navigator.pop(context, reason);
            },
            child: const Text('CONFIRM'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<void> _showHistory(Map<String, dynamic> company) async {
    try {
      final events = await _service.lifecycleHistory(
        (company['id'] as num).toInt(),
      );
      if (!mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        showDragHandle: true,
        isScrollControlled: true,
        builder: (context) => SafeArea(
          child: SizedBox(
            height: MediaQuery.sizeOf(context).height * .72,
            child: Column(
              children: [
                ListTile(
                  title: Text('${company['name']} audit history'),
                  subtitle: Text('${events.length} recorded lifecycle actions'),
                ),
                const Divider(height: 1),
                Expanded(
                  child: events.isEmpty
                      ? const Center(
                          child: Text('No lifecycle actions recorded.'),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(16),
                          itemCount: events.length,
                          separatorBuilder: (_, _) => const Divider(),
                          itemBuilder: (_, index) {
                            final event = events[index];
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: const CircleAvatar(
                                child: Icon(Icons.history_rounded),
                              ),
                              title: Text(
                                event['action'].toString().replaceAll('_', ' '),
                              ),
                              subtitle: Text(
                                '${event['reason']}\n${event['actor_name']} • ${event['created_at']}',
                              ),
                              isThreeLine: true,
                              trailing: Text(
                                '${event['previous_status']} → ${event['new_status']}',
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  Future<void> _addCompany() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const SaasCompanyOnboardingScreen()),
    );
    if (created == true) await _load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('SaaS Command Center'),
      actions: [
        IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
      ],
    ),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
        ? _ErrorState(message: _error!, retry: _load)
        : RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 18, 16, 32),
              children: [
                _Header(
                  metrics: Map<String, dynamic>.from(
                    _data?['metrics'] as Map? ?? {},
                  ),
                ),
                const SizedBox(height: 18),
                _MetricGrid(
                  metrics: Map<String, dynamic>.from(
                    _data?['metrics'] as Map? ?? {},
                  ),
                ),
                const SizedBox(height: 22),
                Row(
                  children: [
                    Text(
                      'Companies',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const Spacer(),
                    Text(
                      '${_companies.length} records',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _search,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(
                    hintText: 'Search company, phone, city or plan',
                    prefixIcon: Icon(Icons.search_rounded),
                  ),
                ),
                const SizedBox(height: 12),
                if (_companies.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Center(child: Text('No matching companies.')),
                    ),
                  )
                else
                  ..._companies.map(
                    (company) => _CompanyCard(
                      company: company,
                      onManage: () => _manage(company),
                    ),
                  ),
              ],
            ),
          ),
    floatingActionButton: _error == null
        ? FloatingActionButton.extended(
            onPressed: _addCompany,
            icon: const Icon(Icons.add_business_rounded),
            label: const Text('ADD COMPANY'),
          )
        : null,
  );
}

class _Header extends StatelessWidget {
  const _Header({required this.metrics});
  final Map<String, dynamic> metrics;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(22),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        colors: [AppColors.primaryDark, AppColors.secondary],
      ),
      borderRadius: BorderRadius.circular(24),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.public_rounded, color: Colors.white, size: 30),
            SizedBox(width: 10),
            Text(
              'ARI SaaS Platform',
              style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
        const Text(
          'MONTHLY RECURRING REVENUE',
          style: TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '₹${metrics['monthly_recurring_revenue'] ?? '0.00'}',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 34,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Live subscription health and company operations overview',
          style: TextStyle(color: Colors.white70),
        ),
      ],
    ),
  );
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({required this.metrics});
  final Map<String, dynamic> metrics;

  @override
  Widget build(BuildContext context) {
    final items = [
      (
        'Companies',
        metrics['total_companies'] ?? 0,
        Icons.apartment_rounded,
        AppColors.primary,
      ),
      (
        'Active',
        metrics['active_subscriptions'] ?? 0,
        Icons.verified_rounded,
        AppColors.success,
      ),
      (
        'Trials',
        metrics['trials'] ?? 0,
        Icons.hourglass_top_rounded,
        AppColors.secondary,
      ),
      (
        'Past due',
        metrics['past_due'] ?? 0,
        Icons.warning_amber_rounded,
        AppColors.warning,
      ),
    ];
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: items.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: 1.55,
      ),
      itemBuilder: (_, index) {
        final item = items[index];
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(15),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(item.$3, color: item.$4),
                const SizedBox(height: 8),
                Text(
                  '${item.$2}',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                Text(item.$1),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _CompanyCard extends StatelessWidget {
  const _CompanyCard({required this.company, required this.onManage});
  final Map<String, dynamic> company;
  final VoidCallback onManage;

  Color _statusColor(String status) => switch (status) {
    'ACTIVE' => AppColors.success,
    'TRIAL' => AppColors.secondary,
    'PAST_DUE' || 'CANCELLED' || 'EXPIRED' => AppColors.error,
    _ => AppColors.warning,
  };

  @override
  Widget build(BuildContext context) {
    final status = company['subscription_status'].toString();
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: AppColors.surfaceMuted,
                  child: Text(
                    company['name'].toString().substring(0, 1).toUpperCase(),
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                      color: AppColors.primary,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        company['name'].toString(),
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        '${company['city'] ?? ''} • ${company['phone'] ?? ''}',
                      ),
                    ],
                  ),
                ),
                PopupMenuButton<String>(
                  onSelected: (_) => onManage(),
                  itemBuilder: (_) => const [
                    PopupMenuItem(
                      value: 'manage',
                      child: Text('Manage subscription'),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _Tag(
                  text: company['plan'].toString(),
                  color: AppColors.primary,
                ),
                _Tag(text: status, color: _statusColor(status)),
                _Tag(
                  text: company['lifecycle_status']?.toString() ?? 'ACTIVE',
                  color: company['lifecycle_status'] == 'ACTIVE'
                      ? AppColors.success
                      : AppColors.warning,
                ),
                _Tag(
                  text: '${company['branches']} branches',
                  color: AppColors.textSecondary,
                ),
                _Tag(
                  text: '${company['members']} members',
                  color: AppColors.textSecondary,
                ),
              ],
            ),
            if (company['lifecycle_reason']?.toString().isNotEmpty == true) ...[
              const SizedBox(height: 10),
              Text(
                'Last action: ${company['lifecycle_reason']}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag({required this.text, required this.color});
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .09),
      borderRadius: BorderRadius.circular(30),
    ),
    child: Text(
      text,
      style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800),
    ),
  );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.retry});
  final String message;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.admin_panel_settings_outlined,
            size: 58,
            color: AppColors.error,
          ),
          const SizedBox(height: 14),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 18),
          FilledButton(onPressed: retry, child: const Text('TRY AGAIN')),
        ],
      ),
    ),
  );
}
