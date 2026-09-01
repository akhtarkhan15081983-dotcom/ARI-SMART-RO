import 'package:flutter/material.dart';

import '../../core/app_colors.dart';
import '../../services/saas_admin_service.dart';

class SaasCompanyOnboardingScreen extends StatefulWidget {
  const SaasCompanyOnboardingScreen({super.key});

  @override
  State<SaasCompanyOnboardingScreen> createState() =>
      _SaasCompanyOnboardingScreenState();
}

class _SaasCompanyOnboardingScreenState
    extends State<SaasCompanyOnboardingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _service = const SaasAdminService();
  final _name = TextEditingController();
  final _legalName = TextEditingController();
  final _appName = TextEditingController();
  final _tagline = TextEditingController();
  final _welcome = TextEditingController();
  final _slug = TextEditingController();
  final _companyPhone = TextEditingController();
  final _email = TextEditingController();
  final _gstin = TextEditingController();
  final _address = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController();
  final _pincode = TextEditingController();
  final _ownerName = TextEditingController();
  final _ownerPhone = TextEditingController();
  final _password = TextEditingController();
  List<Map<String, dynamic>> _plans = const [];
  String? _planCode;
  bool _loadingPlans = true;
  bool _saving = false;
  bool _hidePassword = true;
  bool _showPublicShop = false;

  @override
  void initState() {
    super.initState();
    _loadPlans();
  }

  Future<void> _loadPlans() async {
    try {
      final plans = await _service.plans();
      if (mounted) {
        setState(() {
          _plans = plans;
          _planCode = plans.isEmpty ? null : plans.first['code'].toString();
          _loadingPlans = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() => _loadingPlans = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    }
  }

  String _makeSlug(String value) => value
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');

  String? _required(String? value) =>
      value == null || value.trim().isEmpty ? 'Required' : null;
  String? _phone(String? value) =>
      value != null && RegExp(r'^\d{10}$').hasMatch(value.trim())
      ? null
      : 'Enter a valid 10-digit number';

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || _planCode == null) return;
    setState(() => _saving = true);
    try {
      final result = await _service.onboardCompany({
        'name': _name.text.trim(),
        'legal_name': _legalName.text.trim(),
        'app_display_name': _appName.text.trim(),
        'tagline': _tagline.text.trim(),
        'welcome_message': _welcome.text.trim(),
        'show_public_shop': _showPublicShop,
        'enabled_modules': [
          if (_showPublicShop) 'SHOP',
          'SERVICE',
          'COMPLAINT',
          'ACCOUNT',
        ],
        'slug': _slug.text.trim(),
        'phone': _companyPhone.text.trim(),
        'email': _email.text.trim(),
        'gstin': _gstin.text.trim().toUpperCase(),
        'address': _address.text.trim(),
        'city': _city.text.trim(),
        'state': _state.text.trim(),
        'pincode': _pincode.text.trim(),
        'owner_name': _ownerName.text.trim(),
        'owner_phone': _ownerPhone.text.trim(),
        'initial_password': _password.text,
        'plan_code': _planCode,
      });
      if (!mounted) return;
      final owner = Map<String, dynamic>.from(result['owner'] as Map);
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) => AlertDialog(
          icon: const Icon(
            Icons.verified_rounded,
            color: AppColors.success,
            size: 42,
          ),
          title: const Text('Company onboarded'),
          content: Text(
            '${_name.text.trim()} is ready with a 14-day trial.\n\nOwner login: ${owner['phone']}\n\nShare the initial password securely and ask the owner to change it after first login.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('DONE'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    for (final controller in [
      _name,
      _legalName,
      _appName,
      _tagline,
      _welcome,
      _slug,
      _companyPhone,
      _email,
      _gstin,
      _address,
      _city,
      _state,
      _pincode,
      _ownerName,
      _ownerPhone,
      _password,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Onboard Company')),
    body: Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 110),
        children: [
          const _Intro(),
          const SizedBox(height: 22),
          const _SectionTitle(
            number: '1',
            title: 'Company identity',
            subtitle: 'Official business and storefront information',
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _name,
            validator: _required,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Company name *',
              prefixIcon: Icon(Icons.apartment_rounded),
            ),
            onChanged: (value) {
              _slug.text = _makeSlug(value);
              if (_appName.text.isEmpty) _appName.text = value;
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _legalName,
            decoration: const InputDecoration(
              labelText: 'Legal name',
              prefixIcon: Icon(Icons.gavel_rounded),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _appName,
            decoration: const InputDecoration(
              labelText: 'App display name',
              prefixIcon: Icon(Icons.phone_android_rounded),
              helperText: 'Shown instead of ARI branding',
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _tagline,
            decoration: const InputDecoration(
              labelText: 'Brand tagline',
              prefixIcon: Icon(Icons.format_quote_rounded),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _welcome,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Welcome message',
              prefixIcon: Icon(Icons.waving_hand_outlined),
            ),
          ),
          SwitchListTile.adaptive(
            contentPadding: EdgeInsets.zero,
            value: _showPublicShop,
            onChanged: (value) => setState(() => _showPublicShop = value),
            title: const Text('Enable public company shop'),
            subtitle: const Text(
              'Keep off for a login-first app without public storefront.',
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _slug,
            validator: _required,
            decoration: const InputDecoration(
              labelText: 'Company URL code *',
              prefixIcon: Icon(Icons.link_rounded),
              helperText: 'Lowercase letters, numbers and hyphens',
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _companyPhone,
                  validator: _phone,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'Business phone *',
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Business email',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _gstin,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'GSTIN (optional)',
              prefixIcon: Icon(Icons.receipt_long_rounded),
            ),
          ),
          const SizedBox(height: 22),
          const _SectionTitle(
            number: '2',
            title: 'Head office',
            subtitle: 'The first branch is created automatically',
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _address,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Office address',
              prefixIcon: Icon(Icons.location_on_outlined),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _city,
                  validator: _required,
                  decoration: const InputDecoration(labelText: 'City *'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextFormField(
                  controller: _state,
                  validator: _required,
                  decoration: const InputDecoration(labelText: 'State *'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _pincode,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Pincode'),
          ),
          const SizedBox(height: 22),
          const _SectionTitle(
            number: '3',
            title: 'Company owner',
            subtitle: 'Creates a non-superuser company owner account',
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _ownerName,
            validator: _required,
            textCapitalization: TextCapitalization.words,
            decoration: const InputDecoration(
              labelText: 'Owner full name *',
              prefixIcon: Icon(Icons.person_outline_rounded),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _ownerPhone,
            validator: _phone,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Owner login phone *',
              prefixIcon: Icon(Icons.phone_android_rounded),
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _password,
            validator: (value) => value != null && value.length >= 8
                ? null
                : 'Use at least 8 characters',
            obscureText: _hidePassword,
            decoration: InputDecoration(
              labelText: 'Initial password *',
              prefixIcon: const Icon(Icons.password_rounded),
              suffixIcon: IconButton(
                onPressed: () => setState(() => _hidePassword = !_hidePassword),
                icon: Icon(
                  _hidePassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
              ),
              helperText: 'Use letters, numbers and a special character',
            ),
          ),
          const SizedBox(height: 22),
          const _SectionTitle(
            number: '4',
            title: 'Subscription',
            subtitle: 'Starts with a protected 14-day trial',
          ),
          const SizedBox(height: 12),
          if (_loadingPlans)
            const Center(child: CircularProgressIndicator())
          else
            DropdownButtonFormField<String>(
              initialValue: _planCode,
              decoration: const InputDecoration(
                labelText: 'Select plan *',
                prefixIcon: Icon(Icons.workspace_premium_outlined),
              ),
              items: _plans
                  .map(
                    (plan) => DropdownMenuItem(
                      value: plan['code'].toString(),
                      child: Text('${plan['name']} • ₹${plan['price']}/month'),
                    ),
                  )
                  .toList(),
              onChanged: (value) => setState(() => _planCode = value),
            ),
        ],
      ),
    ),
    bottomNavigationBar: SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
        child: FilledButton.icon(
          onPressed: _saving ? null : _submit,
          icon: _saving
              ? const SizedBox.square(
                  dimension: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.rocket_launch_rounded),
          label: Text(
            _saving ? 'CREATING COMPANY...' : 'CREATE COMPANY & TRIAL',
          ),
        ),
      ),
    ),
  );
}

class _Intro extends StatelessWidget {
  const _Intro();
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        colors: [AppColors.primaryDark, AppColors.secondary],
      ),
      borderRadius: BorderRadius.circular(22),
    ),
    child: const Row(
      children: [
        Icon(Icons.domain_add_rounded, color: Colors.white, size: 38),
        SizedBox(width: 15),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Professional tenant onboarding',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 19,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 5),
              Text(
                'Company, head office, owner access and subscription are created together.',
                style: TextStyle(color: Colors.white70, height: 1.4),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.number,
    required this.title,
    required this.subtitle,
  });
  final String number;
  final String title;
  final String subtitle;
  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      CircleAvatar(
        radius: 16,
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        child: Text(
          number,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
      ),
      const SizedBox(width: 11),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            Text(subtitle),
          ],
        ),
      ),
    ],
  );
}
