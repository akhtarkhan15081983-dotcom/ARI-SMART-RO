import 'package:flutter/material.dart';

import '../../models/profile_model.dart';
import '../../services/profile_service.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _profileService = ProfileService();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _pincodeController = TextEditingController();
  final _emergencyNameController = TextEditingController();
  final _emergencyContactController = TextEditingController();

  bool _isLoadingProfile = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _pincodeController.dispose();
    _emergencyNameController.dispose();
    _emergencyContactController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    try {
      final ProfileModel profile = await _profileService.getProfile();
      if (!mounted) return;

      _firstNameController.text = profile.firstName;
      _lastNameController.text = profile.lastName;
      _pincodeController.text = profile.pincode;
      _emergencyNameController.text = profile.emergencyName;
      _emergencyContactController.text = profile.emergencyContact;
    } catch (_) {
      if (mounted) {
        _showSnackBar(
          'Unable to load your profile. Please try again.',
          isError: true,
        );
      }
    } finally {
      if (mounted) setState(() => _isLoadingProfile = false);
    }
  }

  Future<void> _saveProfile() async {
    print("SAVE BUTTON CLICKED");
    FocusScope.of(context).unfocus();
    if (!(_formKey.currentState?.validate() ?? false)) {
      print("FORM VALIDATION FAILED");

      return;
    }

    print("FORM VALIDATION PASSED");

    setState(() => _isSaving = true);
    try {
      print("PREPARING DATA...");
      final payload = <String, String>{
        'first_name': _firstNameController.text.trim(),
        'last_name': _lastNameController.text.trim(),
        'pincode': _pincodeController.text.trim(),
        'emergency_name': _emergencyNameController.text.trim(),
        'emergency_contact': _emergencyContactController.text.trim(),
      };
      print(payload);

      await _profileService.updateProfile(payload);

      if (!mounted) return;
      _showSnackBar('Profile updated successfully.');
      await Future<void>.delayed(const Duration(milliseconds: 550));
      if (mounted) Navigator.of(context).pop(true);
    } catch (_) {
      if (mounted) {
        _showSnackBar(
          'Could not update your profile. Please try again.',
          isError: true,
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  void _showSnackBar(String message, {bool isError = false}) {
    final scheme = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          behavior: SnackBarBehavior.floating,
          backgroundColor: isError ? scheme.error : scheme.inverseSurface,
        ),
      );
  }

  String? _required(String? value, String label) {
    if (value == null || value.trim().isEmpty) return '$label is required.';
    return null;
  }

  String? _pincodeValidator(String? value) {
    final requiredMessage = _required(value, 'Pincode');
    if (requiredMessage != null) return requiredMessage;
    if (!RegExp(r'^\d{6}$').hasMatch(value!.trim())) {
      return 'Enter a valid 6-digit pincode.';
    }
    return null;
  }

  String? _phoneValidator(String? value) {
    final requiredMessage = _required(value, 'Emergency contact');
    if (requiredMessage != null) return requiredMessage;
    final digits = value!.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.length < 10 || digits.length > 15) {
      return 'Enter a valid emergency contact number.';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Edit Profile')),
      body: _isLoadingProfile
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: Form(
                key: _formKey,
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                  children: [
                    Text('Personal details', style: theme.textTheme.titleLarge),
                    const SizedBox(height: 6),
                    Text(
                      'Keep your information current so we can serve you better.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 24),
                    _sectionCard(
                      context,
                      children: [
                        _field(
                          controller: _firstNameController,
                          label: 'First name',
                          icon: Icons.person_outline,
                          textCapitalization: TextCapitalization.words,
                          validator: (value) => _required(value, 'First name'),
                        ),
                        const SizedBox(height: 16),
                        _field(
                          controller: _lastNameController,
                          label: 'Last name',
                          icon: Icons.person_outline,
                          textCapitalization: TextCapitalization.words,
                          validator: (value) => _required(value, 'Last name'),
                        ),
                        const SizedBox(height: 16),
                        _field(
                          controller: _pincodeController,
                          label: 'Pincode',
                          icon: Icons.location_on_outlined,
                          keyboardType: TextInputType.number,
                          maxLength: 6,
                          validator: _pincodeValidator,
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    Text(
                      'Emergency contact',
                      style: theme.textTheme.titleLarge,
                    ),
                    const SizedBox(height: 12),
                    _sectionCard(
                      context,
                      children: [
                        _field(
                          controller: _emergencyNameController,
                          label: 'Contact name',
                          icon: Icons.contact_emergency_outlined,
                          textCapitalization: TextCapitalization.words,
                          validator: (value) =>
                              _required(value, 'Contact name'),
                        ),
                        const SizedBox(height: 16),
                        _field(
                          controller: _emergencyContactController,
                          label: 'Contact number',
                          icon: Icons.phone_outlined,
                          keyboardType: TextInputType.phone,
                          validator: _phoneValidator,
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                    FilledButton(
                      onPressed: _isSaving ? null : _saveProfile,
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(52),
                      ),
                      child: _isSaving
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.5,
                              ),
                            )
                          : const Text('Save changes'),
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _sectionCard(BuildContext context, {required List<Widget> children}) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: children),
      ),
    );
  }

  Widget _field({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    required String? Function(String?) validator,
    TextInputType? keyboardType,
    TextCapitalization textCapitalization = TextCapitalization.none,
    int? maxLength,
  }) {
    return TextFormField(
      controller: controller,
      validator: validator,
      keyboardType: keyboardType,
      textCapitalization: textCapitalization,
      maxLength: maxLength,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
      ),
    );
  }
}
