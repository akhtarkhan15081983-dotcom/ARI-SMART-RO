import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../services/rent_management_service.dart';

class CalendarRentCollectionScreen extends StatefulWidget {
  const CalendarRentCollectionScreen({super.key, required this.event});
  final Map<String, dynamic> event;

  @override
  State<CalendarRentCollectionScreen> createState() =>
      _CalendarRentCollectionScreenState();
}

class _CalendarRentCollectionScreenState
    extends State<CalendarRentCollectionScreen> {
  final _amount = TextEditingController();
  final _remarks = TextEditingController();
  String _mode = 'CASH';
  bool _saving = false;

  Map<String, dynamic> get _customer =>
      Map<String, dynamic>.from(widget.event['customer'] as Map);

  @override
  void initState() {
    super.initState();
    _amount.text = widget.event['amount']?.toString() ?? '';
  }

  Future<void> _save() async {
    final amount = double.tryParse(_amount.text.trim());
    if (amount == null || amount <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid collected amount.')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await RentManagementService.addRentPayment(
        customerId: _customer['id'] as int,
        amount: amount,
        paymentMode: _mode,
        paymentDate: DateFormat('yyyy-MM-dd').format(DateTime.now()),
        remarks: _remarks.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Rent payment recorded successfully.')),
      );
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Collect Rent')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _customer['name'].toString(),
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 6),
                Text('${_customer['customer_id']} • ${_customer['phone']}'),
                const SizedBox(height: 6),
                Text('${_customer['address']}, ${_customer['city']}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _amount,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            prefixText: '₹ ',
            labelText: 'Amount collected',
          ),
        ),
        const SizedBox(height: 14),
        DropdownButtonFormField<String>(
          initialValue: _mode,
          decoration: const InputDecoration(labelText: 'Payment mode'),
          items: const [
            DropdownMenuItem(value: 'CASH', child: Text('Cash')),
            DropdownMenuItem(value: 'UPI', child: Text('UPI')),
            DropdownMenuItem(value: 'BANK', child: Text('Bank transfer')),
            DropdownMenuItem(value: 'OTHER', child: Text('Other')),
          ],
          onChanged: (value) => setState(() => _mode = value ?? 'CASH'),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _remarks,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Remarks / transaction reference',
          ),
        ),
        const SizedBox(height: 22),
        FilledButton.icon(
          onPressed: _saving ? null : _save,
          icon: _saving
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.verified),
          label: const Text('Confirm Collection'),
        ),
        const SizedBox(height: 10),
        const Text(
          'Payment server par employee name aur time ke saath audit record mein save hoga.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.black54),
        ),
      ],
    ),
  );

  @override
  void dispose() {
    _amount.dispose();
    _remarks.dispose();
    super.dispose();
  }
}
