import 'package:flutter/material.dart';

import '../../services/notification_center_service.dart';
import '../customer/referral_screen.dart';
import '../rent/rent_payment_screen.dart';
import '../service/service_list_screen.dart';
import '../shop/shop_screen.dart';

class NotificationCenterScreen extends StatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  State<NotificationCenterScreen> createState() => _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends State<NotificationCenterScreen> {
  final _service = const NotificationCenterService();
  bool _loading = true;
  int _unread = 0;
  List<Map<String, dynamic>> _items = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await _service.fetch();
      if (!mounted) return;
      setState(() {
        _items = data.items;
        _unread = data.unreadCount;
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

  Future<void> _markRead(Map<String, dynamic> row) async {
    if (row['is_read'] == true) return;
    await _service.markRead((row['id'] as num).toInt());
    await _load();
  }

  Future<void> _markAll() async {
    await _service.markAllRead();
    await _load();
  }

  void _openAction(Map<String, dynamic> row) {
    final action = row['action']?.toString() ?? 'NONE';
    Widget? target;
    switch (action) {
      case 'RENT':
        target = const RentPaymentScreen();
      case 'SHOP':
        target = const ShopScreen();
      case 'SERVICE':
        target = const ServiceListScreen();
      case 'REFERRAL':
        target = const ReferralScreen();
    }
    if (target != null) {
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => target!));
    }
  }

  IconData _icon(String category) {
    switch (category) {
      case 'RENT':
      case 'PAYMENT':
        return Icons.payments_outlined;
      case 'OFFER':
        return Icons.local_offer_outlined;
      case 'LEAVE':
        return Icons.event_available_outlined;
      case 'PAYROLL':
        return Icons.account_balance_wallet_outlined;
      case 'JOB':
      case 'SERVICE':
      case 'COMPLAINT':
        return Icons.build_circle_outlined;
      case 'ATTENDANCE':
        return Icons.fingerprint;
      case 'SECURITY':
        return Icons.security_outlined;
      case 'HRMS':
        return Icons.badge_outlined;
      default:
        return Icons.notifications_outlined;
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(_unread > 0 ? 'Notifications ($_unread)' : 'Notifications'),
          actions: [
            if (_unread > 0)
              TextButton(
                onPressed: _markAll,
                child: const Text('MARK ALL READ'),
              ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: _load,
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _items.isEmpty
                  ? const ListView(
                      physics: AlwaysScrollableScrollPhysics(),
                      children: [
                        SizedBox(height: 180),
                        Icon(Icons.notifications_none_rounded, size: 64),
                        SizedBox(height: 12),
                        Center(child: Text('No notifications right now')),
                      ],
                    )
                  : ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(14),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, index) {
                        final row = _items[index];
                        final unread = row['is_read'] != true;
                        final priority = row['priority']?.toString() ?? 'NORMAL';
                        return Card(
                          child: InkWell(
                            borderRadius: BorderRadius.circular(16),
                            onTap: () => _markRead(row),
                            child: Padding(
                              padding: const EdgeInsets.all(14),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  CircleAvatar(
                                    child: Icon(_icon(row['category']?.toString() ?? 'GENERAL')),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                row['title']?.toString() ?? '',
                                                style: TextStyle(
                                                  fontWeight: unread ? FontWeight.w900 : FontWeight.w700,
                                                ),
                                              ),
                                            ),
                                            if (unread)
                                              Container(
                                                width: 8,
                                                height: 8,
                                                decoration: const BoxDecoration(
                                                  shape: BoxShape.circle,
                                                  color: Colors.redAccent,
                                                ),
                                              ),
                                          ],
                                        ),
                                        const SizedBox(height: 5),
                                        Text(row['message']?.toString() ?? ''),
                                        const SizedBox(height: 8),
                                        Wrap(
                                          spacing: 6,
                                          runSpacing: 6,
                                          children: [
                                            Chip(label: Text(row['category']?.toString() ?? 'GENERAL')),
                                            if (priority != 'NORMAL')
                                              Chip(label: Text(priority)),
                                          ],
                                        ),
                                        if ((row['action']?.toString() ?? 'NONE') != 'NONE') ...[
                                          const SizedBox(height: 8),
                                          FilledButton.tonalIcon(
                                            onPressed: () async {
                                              await _markRead(row);
                                              if (mounted) _openAction(row);
                                            },
                                            icon: const Icon(Icons.arrow_forward_rounded),
                                            label: Text(
                                              (row['action_label']?.toString().trim().isNotEmpty ?? false)
                                                  ? row['action_label'].toString()
                                                  : 'OPEN',
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
        ),
      );
}
