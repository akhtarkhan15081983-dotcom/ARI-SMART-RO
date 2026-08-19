import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../services/referral_service.dart';

class ReferralScreen extends StatefulWidget {
  const ReferralScreen({super.key});

  @override
  State<ReferralScreen> createState() => _ReferralScreenState();
}

class _ReferralScreenState extends State<ReferralScreen> {
  final ReferralService _service = ReferralService();
  final TextEditingController _codeController = TextEditingController();

  bool _loading = true;
  bool _submitting = false;
  String? _error;
  Map<String, dynamic> _summary = <String, dynamic>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.getReferralSummary();
      if (!mounted) return;
      setState(() => _summary = data);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _claimReferral() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      _message('Please enter a referral code.');
      return;
    }
    await _runAction(() => _service.claimReferral(code));
  }

  Future<void> _claimWelcome() async {
    await _runAction(_service.claimWelcomeReward);
  }

  Future<void> _runAction(Future<Map<String, dynamic>> Function() action) async {
    if (_submitting) return;
    setState(() => _submitting = true);
    try {
      final result = await action();
      if (!mounted) return;
      _message(result['message']?.toString() ?? 'Done.');
      _codeController.clear();
      await _load();
    } catch (e) {
      if (mounted) _message(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _message(String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Referral & Rewards'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
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
                        ElevatedButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _walletCard(),
                      const SizedBox(height: 16),
                      _referralCodeCard(),
                      const SizedBox(height: 16),
                      _claimCard(),
                      const SizedBox(height: 16),
                      _rulesCard(),
                      const SizedBox(height: 16),
                      _referralsCard(),
                      const SizedBox(height: 16),
                      _rewardsCard(),
                    ],
                  ),
                ),
    );
  }

  Widget _walletCard() {
    final balance = _summary['wallet_balance']?.toString() ?? '0.00';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('ARI Reward Wallet', style: TextStyle(fontSize: 16)),
            const SizedBox(height: 8),
            Text('₹$balance', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _submitting ? null : _claimWelcome,
              icon: const Icon(Icons.redeem),
              label: const Text('Claim ₹50 Welcome Reward'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _referralCodeCard() {
    final code = _summary['referral_code']?.toString() ?? '-';
    return Card(
      child: ListTile(
        leading: const Icon(Icons.card_giftcard),
        title: const Text('Your Referral Code'),
        subtitle: SelectableText(code, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        trailing: IconButton(
          tooltip: 'Copy code',
          onPressed: code == '-' ? null : () async {
            await Clipboard.setData(ClipboardData(text: code));
            if (mounted) _message('Referral code copied.');
          },
          icon: const Icon(Icons.copy),
        ),
      ),
    );
  }

  Widget _claimCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Have a referral code?', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: _codeController,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(border: OutlineInputBorder(), labelText: 'Referral code'),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submitting ? null : _claimReferral,
                child: Text(_submitting ? 'Please wait...' : 'Apply Referral Code'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _rulesCard() {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Reward Rules', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text('• Welcome reward: ₹50, valid for 90 days.'),
            Text('• Wallet can cover up to 40% of an eligible bill.'),
            Text('• Rent referral reward: ₹50/month for up to 12 months.'),
            Text('• On rent, customer must pay at least ₹100.'),
            Text('• Rent-to-purchase referral reward follows the 15% rule.'),
          ],
        ),
      ),
    );
  }

  Widget _referralsCard() {
    final referrals = (_summary['referrals'] as List?) ?? const [];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('My Referrals (${referrals.length})', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (referrals.isEmpty) const Text('No referrals yet.'),
            for (final raw in referrals)
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.person_add_alt_1),
                  title: Text(raw['referred_name']?.toString().trim().isNotEmpty == true ? raw['referred_name'].toString() : 'Referred customer'),
                  subtitle: Text('${raw['referred_type'] ?? 'Pending'} • ${raw['status'] ?? 'PENDING'}'),
                ),
          ],
        ),
      ),
    );
  }

  Widget _rewardsCard() {
    final rewards = (_summary['rewards'] as List?) ?? const [];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Reward History (${rewards.length})', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (rewards.isEmpty) const Text('No rewards yet.'),
            for (final raw in rewards)
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.account_balance_wallet),
                  title: Text(raw['reward_label']?.toString() ?? raw['reward_type']?.toString() ?? 'Reward'),
                  subtitle: Text('${raw['status'] ?? ''} • Remaining ₹${raw['remaining_amount'] ?? '0.00'}'),
                ),
          ],
        ),
      ),
    );
  }
}
