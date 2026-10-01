import 'package:flutter/material.dart';

import '../../services/notification_center_service.dart';

class NotificationOfferAdminScreen extends StatefulWidget {
  const NotificationOfferAdminScreen({super.key});

  @override
  State<NotificationOfferAdminScreen> createState() => _NotificationOfferAdminScreenState();
}

class _NotificationOfferAdminScreenState extends State<NotificationOfferAdminScreen>
    with SingleTickerProviderStateMixin {
  final _service = const NotificationCenterService();
  late final TabController _tabs;
  bool _loading = true;
  List<Map<String, dynamic>> _campaigns = const [];
  List<Map<String, dynamic>> _offers = const [];
  List<Map<String, dynamic>> _offerCustomers = const [];

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    _tabs.addListener(() {
      if (mounted && !_tabs.indexIsChanging) setState(() {});
    });
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final values = await Future.wait([
        _service.adminCampaigns(),
        _service.adminOffers(),
        _service.adminOfferCustomers(),
      ]);
      if (!mounted) return;
      setState(() {
        _campaigns = values[0];
        _offers = values[1];
        _offerCustomers = values[2];
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

  Future<void> _createCampaign() async {
    final title = TextEditingController();
    final message = TextEditingController();
    String audience = 'EMPLOYEES';
    String role = 'ENGINEER';
    String category = 'GENERAL';
    String priority = 'NORMAL';
    DateTime? validUntil;

    final save = await showDialog<bool>(
          context: context,
          builder: (context) => StatefulBuilder(
            builder: (context, setLocal) => AlertDialog(
              title: const Text('New notification'),
              content: SizedBox(
                width: 520,
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
                      TextField(controller: message, maxLines: 4, decoration: const InputDecoration(labelText: 'Message')),
                      DropdownButtonFormField<String>(
                        initialValue: audience,
                        decoration: const InputDecoration(labelText: 'Audience'),
                        items: const [
                          DropdownMenuItem(value: 'ALL', child: Text('Everyone')),
                          DropdownMenuItem(value: 'CUSTOMERS', child: Text('All customers')),
                          DropdownMenuItem(value: 'EMPLOYEES', child: Text('All employees')),
                          DropdownMenuItem(value: 'ROLE', child: Text('Specific employee role')),
                        ],
                        onChanged: (v) => setLocal(() => audience = v ?? audience),
                      ),
                      if (audience == 'ROLE')
                        DropdownButtonFormField<String>(
                          initialValue: role,
                          decoration: const InputDecoration(labelText: 'Role'),
                          items: const [
                            DropdownMenuItem(value: 'MANAGER', child: Text('Manager')),
                            DropdownMenuItem(value: 'OFFICE', child: Text('Office')),
                            DropdownMenuItem(value: 'CALLING', child: Text('Calling')),
                            DropdownMenuItem(value: 'ENGINEER', child: Text('Engineer')),
                          ],
                          onChanged: (v) => setLocal(() => role = v ?? role),
                        ),
                      DropdownButtonFormField<String>(
                        initialValue: category,
                        decoration: const InputDecoration(labelText: 'Category'),
                        items: const [
                          DropdownMenuItem(value: 'GENERAL', child: Text('General')),
                          DropdownMenuItem(value: 'HRMS', child: Text('HRMS')),
                          DropdownMenuItem(value: 'ATTENDANCE', child: Text('Attendance')),
                          DropdownMenuItem(value: 'LEAVE', child: Text('Leave')),
                          DropdownMenuItem(value: 'PAYROLL', child: Text('Payroll')),
                          DropdownMenuItem(value: 'JOB', child: Text('Job')),
                          DropdownMenuItem(value: 'SERVICE', child: Text('Service')),
                          DropdownMenuItem(value: 'COMPLAINT', child: Text('Complaint')),
                          DropdownMenuItem(value: 'RENT', child: Text('Rent')),
                          DropdownMenuItem(value: 'PAYMENT', child: Text('Payment')),
                          DropdownMenuItem(value: 'SYSTEM', child: Text('System')),
                        ],
                        onChanged: (v) => setLocal(() => category = v ?? category),
                      ),
                      DropdownButtonFormField<String>(
                        initialValue: priority,
                        decoration: const InputDecoration(labelText: 'Priority'),
                        items: const [
                          DropdownMenuItem(value: 'LOW', child: Text('Low')),
                          DropdownMenuItem(value: 'NORMAL', child: Text('Normal')),
                          DropdownMenuItem(value: 'HIGH', child: Text('High')),
                          DropdownMenuItem(value: 'CRITICAL', child: Text('Critical')),
                        ],
                        onChanged: (v) => setLocal(() => priority = v ?? priority),
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Expiry'),
                        subtitle: Text(validUntil == null ? 'No expiry' : validUntil.toString()),
                        trailing: const Icon(Icons.event_outlined),
                        onTap: () async {
                          final date = await showDatePicker(
                            context: context,
                            initialDate: DateTime.now().add(const Duration(days: 7)),
                            firstDate: DateTime.now(),
                            lastDate: DateTime.now().add(const Duration(days: 730)),
                          );
                          if (date != null) {
                            setLocal(() => validUntil = DateTime(date.year, date.month, date.day, 23, 59));
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
                FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('SEND')),
              ],
            ),
          ),
        ) ??
        false;

    if (!save || title.text.trim().isEmpty || message.text.trim().isEmpty) return;
    try {
      final result = await _service.createCampaign({
        'title': title.text.trim(),
        'message': message.text.trim(),
        'audience': audience,
        'target_role': audience == 'ROLE' ? role : '',
        'category': category,
        'priority': priority,
        if (validUntil != null) 'valid_until': validUntil!.toIso8601String(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sent to ${result['delivered'] ?? 0} users.')),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      title.dispose();
      message.dispose();
    }
  }

  String _customerLabel(Map<String, dynamic> row) {
    final status = row['is_active'] == true ? 'Active' : 'Inactive';
    final app = row['app_user_id'] == null ? ' • App not linked' : '';
    return '${row['name']} • ${row['customer_id']} • ${row['phone']} • $status$app';
  }

  Future<void> _createOffer() async {
    final title = TextEditingController();
    final message = TextEditingController();
    final discount = TextEditingController();
    final promo = TextEditingController();
    final minAmount = TextEditingController(text: '0');
    final maxDiscount = TextEditingController(text: '0');
    final terms = TextEditingController();
    String audience = 'ALL';
    int? targetCustomerId;
    String scope = 'RENT';
    String discountType = 'PERCENT';
    bool autoApply = true;
    DateTime? validUntil;

    final save = await showDialog<bool>(
          context: context,
          builder: (context) => StatefulBuilder(
            builder: (context, setLocal) => AlertDialog(
              title: const Text('Create customer offer'),
              content: SizedBox(
                width: 580,
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: audience,
                        decoration: const InputDecoration(labelText: 'Send offer to'),
                        items: const [
                          DropdownMenuItem(value: 'ALL', child: Text('All customers')),
                          DropdownMenuItem(value: 'ACTIVE', child: Text('Active customers only')),
                          DropdownMenuItem(value: 'INACTIVE', child: Text('Inactive customers only')),
                          DropdownMenuItem(value: 'TARGETED', child: Text('One customer')),
                        ],
                        onChanged: (v) => setLocal(() {
                          audience = v ?? audience;
                          if (audience != 'TARGETED') targetCustomerId = null;
                        }),
                      ),
                      if (audience == 'TARGETED')
                        DropdownButtonFormField<int>(
                          isExpanded: true,
                          initialValue: targetCustomerId,
                          decoration: const InputDecoration(
                            labelText: 'Select customer',
                            helperText: 'Active and inactive customers are both available.',
                          ),
                          items: _offerCustomers
                              .map(
                                (row) => DropdownMenuItem<int>(
                                  value: (row['id'] as num).toInt(),
                                  child: Text(
                                    _customerLabel(row),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              )
                              .toList(),
                          onChanged: (v) => setLocal(() => targetCustomerId = v),
                        ),
                      const SizedBox(height: 8),
                      TextField(controller: title, decoration: const InputDecoration(labelText: 'Offer title')),
                      TextField(controller: message, maxLines: 3, decoration: const InputDecoration(labelText: 'Customer message')),
                      DropdownButtonFormField<String>(
                        initialValue: scope,
                        decoration: const InputDecoration(labelText: 'Offer applies to'),
                        items: const [
                          DropdownMenuItem(value: 'RENT', child: Text('Monthly rent')),
                          DropdownMenuItem(value: 'PURCHASE', child: Text('Product purchase')),
                          DropdownMenuItem(value: 'SERVICE', child: Text('Service')),
                          DropdownMenuItem(value: 'AMC', child: Text('AMC')),
                          DropdownMenuItem(value: 'REFERRAL', child: Text('Referral')),
                        ],
                        onChanged: (v) => setLocal(() => scope = v ?? scope),
                      ),
                      DropdownButtonFormField<String>(
                        initialValue: discountType,
                        decoration: const InputDecoration(labelText: 'Discount type'),
                        items: const [
                          DropdownMenuItem(value: 'PERCENT', child: Text('Percentage %')),
                          DropdownMenuItem(value: 'FIXED', child: Text('Fixed ₹')),
                        ],
                        onChanged: (v) => setLocal(() => discountType = v ?? discountType),
                      ),
                      TextField(controller: discount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Discount value')),
                      TextField(controller: maxDiscount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Maximum discount ₹ (0 = no cap)')),
                      TextField(controller: minAmount, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Minimum bill ₹')),
                      TextField(controller: promo, decoration: const InputDecoration(labelText: 'Promo code (optional)')),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        value: autoApply,
                        onChanged: (v) => setLocal(() => autoApply = v),
                        title: const Text('Auto apply'),
                        subtitle: const Text('Eligible customers get the discount automatically.'),
                      ),
                      TextField(controller: terms, maxLines: 2, decoration: const InputDecoration(labelText: 'Terms')),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Offer valid until'),
                        subtitle: Text(validUntil == null ? 'No expiry' : validUntil.toString()),
                        trailing: const Icon(Icons.event_outlined),
                        onTap: () async {
                          final date = await showDatePicker(
                            context: context,
                            initialDate: DateTime.now().add(const Duration(days: 7)),
                            firstDate: DateTime.now(),
                            lastDate: DateTime.now().add(const Duration(days: 730)),
                          );
                          if (date != null) {
                            setLocal(() => validUntil = DateTime(date.year, date.month, date.day, 23, 59));
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
                FilledButton(
                  onPressed: audience == 'TARGETED' && targetCustomerId == null
                      ? null
                      : () => Navigator.pop(context, true),
                  child: const Text('CREATE & SEND'),
                ),
              ],
            ),
          ),
        ) ??
        false;

    if (!save || title.text.trim().isEmpty || message.text.trim().isEmpty || discount.text.trim().isEmpty) return;
    try {
      final result = await _service.createOffer({
        'title': title.text.trim(),
        'message': message.text.trim(),
        'audience': audience,
        if (targetCustomerId != null) 'target_customer_id': targetCustomerId,
        'offer_scope': scope,
        'discount_type': discountType,
        'discount_value': discount.text.trim(),
        'max_discount': maxDiscount.text.trim(),
        'minimum_amount': minAmount.text.trim(),
        'promo_code': promo.text.trim(),
        'auto_apply': autoApply,
        'terms': terms.text.trim(),
        'action': scope == 'RENT' ? 'RENT' : (scope == 'PURCHASE' ? 'SHOP' : (scope == 'REFERRAL' ? 'REFERRAL' : 'SERVICE')),
        'action_label': scope == 'RENT' ? 'VIEW RENT' : (scope == 'PURCHASE' ? 'SHOP NOW' : 'VIEW OFFER'),
        'priority': 80,
        if (validUntil != null) 'valid_until': validUntil!.toIso8601String(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Offer sent to ${result['delivered'] ?? 0} customer app inboxes.',
            ),
          ),
        );
      }
      await _load();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      title.dispose();
      message.dispose();
      discount.dispose();
      promo.dispose();
      minAmount.dispose();
      maxDiscount.dispose();
      terms.dispose();
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Notifications & Offers'),
          bottom: TabBar(
            controller: _tabs,
            tabs: const [
              Tab(text: 'NOTIFICATIONS'),
              Tab(text: 'OFFERS'),
            ],
          ),
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () => _tabs.index == 0 ? _createCampaign() : _createOffer(),
          icon: const Icon(Icons.add),
          label: Text(_tabs.index == 0 ? 'SEND ALERT' : 'NEW OFFER'),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(
                controller: _tabs,
                children: [
                  RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(14),
                      itemCount: _campaigns.length,
                      itemBuilder: (_, index) {
                        final row = _campaigns[index];
                        return Card(
                          child: ListTile(
                            leading: const CircleAvatar(child: Icon(Icons.notifications_active_outlined)),
                            title: Text(row['title']?.toString() ?? ''),
                            subtitle: Text(
                              '${row['audience']} • ${row['category']} • ${row['priority']}\n'
                              'Delivered ${row['delivery_count'] ?? 0} • Unread ${row['unread_count'] ?? 0}',
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                  RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(14),
                      itemCount: _offers.length,
                      itemBuilder: (_, index) {
                        final row = _offers[index];
                        final type = row['discount_type']?.toString() ?? 'NONE';
                        final value = row['discount_value']?.toString() ?? '0';
                        return Card(
                          child: ListTile(
                            leading: const CircleAvatar(child: Icon(Icons.local_offer_outlined)),
                            title: Text(row['title']?.toString() ?? ''),
                            subtitle: Text(
                              '${row['audience']} • ${row['offer_scope']} • ${type == 'PERCENT' ? '$value%' : '₹$value'}'
                              '${row['promo_code']?.toString().isNotEmpty == true ? ' • ${row['promo_code']}' : ''}\n'
                              '${row['auto_apply'] == true ? 'Auto apply' : 'Promo code required'}',
                            ),
                            trailing: row['is_active'] == true
                                ? const Icon(Icons.check_circle_outline)
                                : const Icon(Icons.pause_circle_outline),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
      );
}
