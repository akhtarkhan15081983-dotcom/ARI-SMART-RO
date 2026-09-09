import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../models/shop_product_model.dart';
import '../../services/public_request_service.dart';

class PublicRequestScreen extends StatefulWidget {
  const PublicRequestScreen({
    super.key,
    required this.requestType,
    required this.title,
    this.product,
    this.planName,
  });

  final String requestType;
  final String title;
  final ShopProduct? product;
  final String? planName;

  @override
  State<PublicRequestScreen> createState() => _PublicRequestScreenState();
}

class _PublicRequestScreenState extends State<PublicRequestScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _alternatePhone = TextEditingController();
  final _email = TextEditingController();
  final _address = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController(text: 'Uttar Pradesh');
  final _pincode = TextEditingController();
  final _notes = TextEditingController();
  final _referralCode = TextEditingController();
  final _service = const PublicRequestService();

  int _quantity = 1;
  String _paymentMethod = 'OFFICE';
  bool _submitting = false;

  bool get _isProduct => widget.product != null;
  bool get _isPurchase => widget.requestType == 'PURCHASE';

  @override
  void dispose() {
    for (final controller in [
      _name,
      _phone,
      _alternatePhone,
      _email,
      _address,
      _city,
      _state,
      _pincode,
      _notes,
      _referralCode,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  String? _required(String? value) =>
      value == null || value.trim().isEmpty ? 'This field is required' : null;

  String? _mobile(String? value, {bool optional = false}) {
    final digits = (value ?? '').replaceAll(RegExp(r'\D'), '');
    if (optional && digits.isEmpty) return null;
    return RegExp(r'^[6-9]\d{9}$').hasMatch(digits)
        ? null
        : 'Enter a valid 10-digit mobile number';
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || _submitting) return;
    FocusScope.of(context).unfocus();
    setState(() => _submitting = true);
    try {
      final result = await _service.submit({
        'request_type': widget.requestType,
        if (widget.product != null) 'product': widget.product!.id,
        'plan_name':
            widget.planName ?? widget.product?.modelName ?? widget.title,
        'customer_name': _name.text.trim(),
        'phone': _phone.text.replaceAll(RegExp(r'\D'), ''),
        'alternate_phone': _alternatePhone.text.replaceAll(RegExp(r'\D'), ''),
        'email': _email.text.trim(),
        'address': _address.text.trim(),
        'city': _city.text.trim(),
        'state': _state.text.trim(),
        'pincode': _pincode.text.trim(),
        'quantity': _quantity,
        'payment_method': _paymentMethod,
        'referral_code': _referralCode.text.trim().toUpperCase(),
        'notes': _notes.text.trim(),
      });
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => AlertDialog(
          icon: const Icon(
            Icons.check_circle_rounded,
            color: Color(0xFF15803D),
            size: 54,
          ),
          title: const Text('Request received'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'No login was required. Our team will call you to verify the details.',
              ),
              const SizedBox(height: 14),
              SelectableText(
                result['request_number']?.toString() ?? '',
                style: const TextStyle(
                  fontWeight: FontWeight.w900,
                  fontSize: 17,
                ),
              ),
            ],
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('DONE'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(error.toString().replaceFirst('Exception: ', '')),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final product = widget.product;
    final unitPrice = widget.requestType == 'RENTAL'
        ? product?.monthlyRent ?? 0
        : product?.sellingPrice ?? 0;
    return Scaffold(
      backgroundColor: const Color(0xFFF4F8FB),
      appBar: AppBar(title: Text(widget.title)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 34),
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF07315E), Color(0xFF078AD8)],
                ),
                borderRadius: BorderRadius.circular(22),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.lock_open_rounded, color: Colors.white),
                      SizedBox(width: 9),
                      Text(
                        'Guest checkout',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 18,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    product?.modelName ?? widget.planName ?? widget.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (_isProduct && unitPrice > 0) ...[
                    const SizedBox(height: 6),
                    Text(
                      widget.requestType == 'RENTAL'
                          ? '₹${unitPrice.toStringAsFixed(0)}/month'
                          : '₹${(unitPrice * _quantity).toStringAsFixed(0)}',
                      style: const TextStyle(
                        color: Color(0xFFE5F8FF),
                        fontSize: 21,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 18),
            const _FormHeading('Contact details'),
            TextFormField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              validator: _required,
              decoration: const InputDecoration(
                labelText: 'Full name *',
                prefixIcon: Icon(Icons.person_outline),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(10),
              ],
              validator: _mobile,
              decoration: const InputDecoration(
                labelText: 'Mobile number *',
                prefixIcon: Icon(Icons.phone_outlined),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _alternatePhone,
              keyboardType: TextInputType.phone,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(10),
              ],
              validator: (value) => _mobile(value, optional: true),
              decoration: const InputDecoration(
                labelText: 'Alternate mobile (optional)',
                prefixIcon: Icon(Icons.phone_android_outlined),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Email (optional)',
                prefixIcon: Icon(Icons.email_outlined),
              ),
            ),
            const SizedBox(height: 20),
            const _FormHeading('Service / delivery address'),
            TextFormField(
              controller: _address,
              minLines: 2,
              maxLines: 3,
              textCapitalization: TextCapitalization.sentences,
              validator: _required,
              decoration: const InputDecoration(
                labelText: 'Complete address *',
                prefixIcon: Icon(Icons.location_on_outlined),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _city,
                    textCapitalization: TextCapitalization.words,
                    validator: _required,
                    decoration: const InputDecoration(labelText: 'City *'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextFormField(
                    controller: _pincode,
                    keyboardType: TextInputType.number,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(6),
                    ],
                    validator: (value) =>
                        RegExp(r'^\d{6}$').hasMatch(value ?? '')
                        ? null
                        : 'Enter 6 digits',
                    decoration: const InputDecoration(labelText: 'Pincode *'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _state,
              textCapitalization: TextCapitalization.words,
              validator: _required,
              decoration: const InputDecoration(labelText: 'State *'),
            ),
            if (_isProduct) ...[
              const SizedBox(height: 20),
              const _FormHeading('Order preference'),
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Quantity',
                      style: TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                  IconButton(
                    onPressed: _quantity > 1
                        ? () => setState(() => _quantity--)
                        : null,
                    icon: const Icon(Icons.remove_circle_outline),
                  ),
                  Text(
                    '$_quantity',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  IconButton(
                    onPressed: () => setState(() => _quantity++),
                    icon: const Icon(Icons.add_circle_outline),
                  ),
                ],
              ),
              DropdownButtonFormField<String>(
                initialValue: _paymentMethod,
                decoration: const InputDecoration(
                  labelText: 'Payment preference',
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'OFFICE',
                    child: Text('Confirm payment with ARI team'),
                  ),
                  DropdownMenuItem(
                    value: 'COD',
                    child: Text('Cash / UPI on delivery'),
                  ),
                ],
                onChanged: (value) =>
                    setState(() => _paymentMethod = value ?? 'OFFICE'),
              ),
            ],
            const SizedBox(height: 12),
            TextFormField(
              controller: _referralCode,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                labelText: 'Referral code (optional)',
                prefixIcon: Icon(Icons.card_giftcard_outlined),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _notes,
              minLines: 2,
              maxLines: 4,
              decoration: InputDecoration(
                labelText: _isPurchase
                    ? 'Delivery instructions (optional)'
                    : 'Tell us your requirement (optional)',
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.verified_rounded),
              label: Text(
                _submitting
                    ? 'SUBMITTING...'
                    : (_isPurchase
                          ? 'PLACE ORDER WITHOUT LOGIN'
                          : 'SUBMIT WITHOUT LOGIN'),
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              'Submitting creates a request only. Final availability, visit time and payment are confirmed transparently by the ARI team.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF60778A),
                fontSize: 11.5,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FormHeading extends StatelessWidget {
  const _FormHeading(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Text(
      text,
      style: Theme.of(
        context,
      ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
    ),
  );
}
