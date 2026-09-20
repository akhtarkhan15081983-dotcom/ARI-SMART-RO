import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/referral_service.dart';
import '../../utils/search_utils.dart';

class ReferralScreen extends StatefulWidget {
  const ReferralScreen({super.key});

  @override
  State<ReferralScreen> createState() => _ReferralScreenState();
}

class _ReferralScreenState extends State<ReferralScreen> {
  final ReferralService _service = ReferralService();
  final TextEditingController _codeController = TextEditingController();
  final TextEditingController _historySearchController = TextEditingController();
  String _historyQuery = '';
  String _referralFilter = 'ALL';
  String _transactionFilter = 'ALL';

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
    _historySearchController.dispose();
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

  Future<void> _runAction(
    Future<Map<String, dynamic>> Function() action,
  ) async {
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

  bool _capability(String key) {
    final capabilities = _summary['capabilities'];
    return capabilities is Map && capabilities[key] == true;
  }

  String _money(dynamic value) {
    final amount = double.tryParse(value?.toString() ?? '') ?? 0;
    return NumberFormat.currency(
      locale: 'en_IN',
      symbol: '₹',
      decimalDigits: amount == amount.roundToDouble() ? 0 : 2,
    ).format(amount);
  }

  String _date(dynamic value) {
    final parsed = DateTime.tryParse(value?.toString() ?? '')?.toLocal();
    return parsed == null ? '' : DateFormat('dd MMM yyyy, hh:mm a').format(parsed);
  }

  String _inviteMessage(String code) =>
      'ARI Smart RO app join karein aur referral code $code apply karein. '
      'RO shopping, service aur smart customer support ek hi app mein. '
      'Referral खोलें: arismartro://referral?code=$code';

  Future<void> _shareOnWhatsApp(String code) async {
    final uri = Uri.parse(
      'https://wa.me/?text=${Uri.encodeComponent(_inviteMessage(code))}',
    );
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      await Clipboard.setData(ClipboardData(text: _inviteMessage(code)));
      _message('Invite message copied. You can share it anywhere.');
    }
  }

  Future<void> _shareBySms(String code) async {
    final uri = Uri(
      scheme: 'sms',
      queryParameters: {'body': _inviteMessage(code)},
    );
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      await Clipboard.setData(ClipboardData(text: _inviteMessage(code)));
      _message('Invite message copied.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Refer & Earn Wallet'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
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
                    ElevatedButton(
                      onPressed: _load,
                      child: const Text('Retry'),
                    ),
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
                  _statsCard(),
                  const SizedBox(height: 16),
                  _referralCodeCard(),
                  if (_capability('can_apply_referral_code')) ...[
                    const SizedBox(height: 16),
                    _claimCard(),
                  ],
                  const SizedBox(height: 16),
                  _rulesCard(),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _historySearchController,
                    textInputAction: TextInputAction.search,
                    onChanged: (value) => setState(() => _historyQuery = value),
                    decoration: InputDecoration(
                      hintText: 'Search referral, reward or wallet history...',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _historyQuery.isEmpty ? null : IconButton(
                        onPressed: () { _historySearchController.clear(); setState(() => _historyQuery = ''); },
                        icon: const Icon(Icons.clear),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _referralsCard(),
                  const SizedBox(height: 16),
                  _rewardsCard(),
                  const SizedBox(height: 16),
                  _transactionsCard(),
                ],
              ),
            ),
    );
  }

  Widget _walletCard() {
    final balance = _summary['wallet_balance'];
    final points = _summary['points_balance']?.toString() ?? '0';
    final lifetime = _summary['lifetime_earnings'];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('ARI Reward Wallet', style: TextStyle(fontSize: 16)),
            const SizedBox(height: 8),
            Text(
              _money(balance),
              style: Theme.of(
                context,
              ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            Text('$points referral points available'),
            const SizedBox(height: 4),
            Text('Lifetime rewards: ${_money(lifetime)}'),
            const SizedBox(height: 12),
            if (_capability('can_claim_welcome_reward'))
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

  Widget _statsCard() {
    final stats = _summary['referral_stats'];
    final values = stats is Map ? stats : const {};
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Referral Performance',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                _stat('Total', values['total'], Colors.blue),
                _stat('Pending', values['pending'], Colors.orange),
                _stat('Successful', values['qualified'], Colors.green),
                _stat('Review', values['under_review'], Colors.purple),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _stat(String label, dynamic value, Color color) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value?.toString() ?? '0',
            style: TextStyle(
              color: color,
              fontSize: 22,
              fontWeight: FontWeight.w900,
            ),
          ),
          Text(label, style: const TextStyle(fontSize: 11)),
        ],
      ),
    );
  }

  Widget _referralCodeCard() {
    final code = _summary['referral_code']?.toString() ?? '-';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.card_giftcard),
                SizedBox(width: 10),
                Text(
                  'Invite & Earn',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Apna unique code share karein. Eligible friend code apply karega to reward wallet mein automatically credit hoga.',
            ),
            const SizedBox(height: 14),
            SelectableText(
              code,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w900,
                letterSpacing: 2,
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: code == '-'
                        ? null
                        : () async {
                            await Clipboard.setData(
                              ClipboardData(text: _inviteMessage(code)),
                            );
                            if (mounted) _message('Invite message copied.');
                          },
                    icon: const Icon(Icons.copy),
                    label: const Text('Copy'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: code == '-'
                        ? null
                        : () => _shareOnWhatsApp(code),
                    icon: const Icon(Icons.share),
                    label: const Text('WhatsApp'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: code == '-' ? null : () => _shareBySms(code),
                icon: const Icon(Icons.sms_outlined),
                label: const Text('Send using phone SMS'),
              ),
            ),
          ],
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
            const Text(
              'Have a referral code?',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _codeController,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Referral code',
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submitting ? null : _claimReferral,
                child: Text(
                  _submitting ? 'Please wait...' : 'Apply Referral Code',
                ),
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
            Text('• Friend code apply करे: referrer को 100 points = ₹10.'),
            Text('• Points केवल service, parts और new RO purchase में लगेंगे.'),
            Text('• Cash bill में maximum 30% wallet और minimum 70% cash/UPI.'),
            Text(
              '• Successful installation: ₹50/month rent benefit, 12 months तक.',
            ),
            Text('• Rent में customer कम-से-कम ₹100 cash/UPI देगा.'),
            Text('• App referral points rent payment में use नहीं होंगे.'),
          ],
        ),
      ),
    );
  }

  Widget _referralsCard() {
    final referrals = ((_summary['referrals'] as List?) ?? const [])
        .whereType<Map>()
        .where((raw) {
          final status = (raw['status'] ?? 'PENDING').toString().toUpperCase();
          if (_referralFilter != 'ALL' && status != _referralFilter) return false;
          return matchesAllSearchTerms(_historyQuery, raw.entries.map((e) => '${e.key} ${e.value}'));
        })
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'My Referrals (${referrals.length})',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _referralFilter,
              decoration: const InputDecoration(labelText: 'Referral status'),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('All referrals')),
                DropdownMenuItem(value: 'PENDING', child: Text('Pending')),
                DropdownMenuItem(value: 'QUALIFIED', child: Text('Qualified')),
                DropdownMenuItem(value: 'REVIEW', child: Text('Review')),
                DropdownMenuItem(value: 'REJECTED', child: Text('Rejected')),
              ],
              onChanged: (v) => setState(() => _referralFilter = v ?? 'ALL'),
            ),
            const SizedBox(height: 8),
            if (referrals.isEmpty) const Text('No matching referrals.'),
            for (final raw in referrals)
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.person_add_alt_1),
                  title: Text(
                    raw['referred_name']?.toString().trim().isNotEmpty == true
                        ? raw['referred_name'].toString()
                        : 'Referred customer',
                  ),
                  subtitle: Text(
                    '${_referralStatus(raw)}${_date(raw['created_at']).isEmpty ? '' : '\n${_date(raw['created_at'])}'}',
                  ),
                  isThreeLine: true,
                ),
          ],
        ),
      ),
    );
  }

  String _referralStatus(Map raw) {
    final status = raw['status']?.toString() ?? 'PENDING';
    if (status == 'QUALIFIED') {
      return '${raw['referred_type'] ?? 'Customer'} • Installation successful • Benefit active';
    }
    if (status == 'REVIEW') {
      return 'Automatic security review • No action needed';
    }
    if (status == 'REJECTED') return 'Not eligible';
    return 'Code applied • Installation pending';
  }

  Widget _rewardsCard() {
    final rewards = ((_summary['rewards'] as List?) ?? const [])
        .whereType<Map>()
        .where((raw) => matchesAllSearchTerms(_historyQuery, raw.entries.map((e) => '${e.key} ${e.value}')))
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Reward History (${rewards.length})',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            if (rewards.isEmpty) const Text('No rewards yet.'),
            for (final raw in rewards)
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.account_balance_wallet),
                  title: Text(
                    raw['reward_label']?.toString() ??
                        raw['reward_type']?.toString() ??
                        'Reward',
                  ),
                  subtitle: Text(
                    '${raw['status'] ?? ''} • Remaining ${_money(raw['remaining_amount'])}',
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Widget _transactionsCard() {
    final transactions = ((_summary['transactions'] as List?) ?? const [])
        .whereType<Map>()
        .where((raw) {
          final type = (raw['entry_type'] ?? '').toString().toUpperCase();
          if (_transactionFilter != 'ALL' && type != _transactionFilter) return false;
          return matchesAllSearchTerms(_historyQuery, raw.entries.map((e) => '${e.key} ${e.value}'));
        })
        .toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Wallet Transactions (${transactions.length})',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _transactionFilter,
              decoration: const InputDecoration(labelText: 'Transaction type'),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('All transactions')),
                DropdownMenuItem(value: 'CREDIT', child: Text('Credits')),
                DropdownMenuItem(value: 'DEBIT', child: Text('Debits')),
              ],
              onChanged: (v) => setState(() => _transactionFilter = v ?? 'ALL'),
            ),
            const SizedBox(height: 8),
            if (transactions.isEmpty)
              const Text('No matching wallet activity.'),
            for (final raw in transactions)
              if (raw is Map)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: raw['entry_type'] == 'CREDIT'
                        ? Colors.green.shade50
                        : Colors.red.shade50,
                    child: Icon(
                      raw['entry_type'] == 'CREDIT'
                          ? Icons.arrow_downward
                          : Icons.arrow_upward,
                      color: raw['entry_type'] == 'CREDIT'
                          ? Colors.green
                          : Colors.red,
                    ),
                  ),
                  title: Text(raw['description']?.toString() ?? 'Wallet entry'),
                  subtitle: Text(
                    [raw['reward_label'], _date(raw['created_at'])]
                        .where((value) => value?.toString().trim().isNotEmpty == true)
                        .join(' • '),
                  ),
                  trailing: Text(
                    '${raw['entry_type'] == 'CREDIT' ? '+' : '-'}${_money(raw['amount'])}',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: raw['entry_type'] == 'CREDIT'
                          ? Colors.green
                          : Colors.red,
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
