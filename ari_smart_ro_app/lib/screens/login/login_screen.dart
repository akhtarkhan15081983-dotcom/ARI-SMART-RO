import 'package:flutter/material.dart';
import '../dashboard/dashboard_screen.dart';
import '../../controllers/login_controller.dart';
import '../../services/api_service.dart';
import 'customer_onboarding_screen.dart';
import 'existing_customer_first_login_screen.dart';
import 'forgot_password_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const _rememberedLoginKey = 'remembered_login_id';
  final phoneController = TextEditingController();
  final passwordController = TextEditingController();
  final loginController = LoginController();
  bool isLoading = false;
  bool _hidePassword = true;
  bool _rememberMe = false;

  @override
  void initState() {
    super.initState();
    _loadRememberedLogin();
  }

  Future<void> _loadRememberedLogin() async {
    final legacy = await ApiService.rememberedCredentials();
    final legacyIdentifier = legacy?['phone'];
    await ApiService.clearRememberedCredentials();

    var remembered = await ApiService.storage.read(key: _rememberedLoginKey);
    if ((remembered == null || remembered.isEmpty) &&
        legacyIdentifier != null &&
        legacyIdentifier.isNotEmpty) {
      remembered = legacyIdentifier;
      await ApiService.storage.write(
        key: _rememberedLoginKey,
        value: remembered,
      );
    }
    if (!mounted || remembered == null || remembered.isEmpty) return;
    phoneController.text = remembered;
    setState(() => _rememberMe = true);
  }

  @override
  void dispose() {
    phoneController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        centerTitle: true,
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
        elevation: 0,
        title: const Text('ARI SMART RO'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              Image.asset('assets/images/ari_smart_ro_icon.png', height: 220),
              const SizedBox(height: 20),
              const Text(
                'ARI SMART RO',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Sign in to continue',
                style: TextStyle(fontSize: 18, color: Colors.grey),
              ),
              const SizedBox(height: 35),
              TextField(
                controller: phoneController,
                textCapitalization: TextCapitalization.characters,
                autofillHints: const [AutofillHints.username],
                decoration: InputDecoration(
                  labelText: 'Phone / Customer ID / Card No.',
                  prefixIcon: const Icon(Icons.badge_outlined),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              TextField(
                controller: passwordController,
                obscureText: _hidePassword,
                enableSuggestions: false,
                autocorrect: false,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.password],
                decoration: InputDecoration(
                  labelText: 'Password',
                  prefixIcon: const Icon(Icons.lock),
                  suffixIcon: IconButton(
                    tooltip: _hidePassword ? 'Show password' : 'Hide password',
                    onPressed: () => setState(() => _hidePassword = !_hidePassword),
                    icon: Icon(
                      _hidePassword
                          ? Icons.visibility_outlined
                          : Icons.visibility_off_outlined,
                    ),
                  ),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                value: _rememberMe,
                onChanged: isLoading
                    ? null
                    : (value) => setState(() => _rememberMe = value ?? false),
                title: const Text('Remember login ID'),
                subtitle: const Text('Password is never saved by ARI SMART RO'),
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton.icon(
                  onPressed: isLoading
                      ? null
                      : () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const ForgotPasswordScreen(),
                            ),
                          ),
                  icon: const Icon(Icons.lock_reset_rounded),
                  label: const Text('FORGOT PASSWORD?'),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: isLoading
                      ? null
                      : () async {
                          setState(() => isLoading = true);
                          final success = await loginController.login(
                            phone: phoneController.text.trim(),
                            password: passwordController.text.trim(),
                          );
                          if (!context.mounted) return;
                          setState(() => isLoading = false);
                          if (success) {
                            await ApiService.clearRememberedCredentials();
                            if (_rememberMe) {
                              await ApiService.storage.write(
                                key: _rememberedLoginKey,
                                value: phoneController.text.trim(),
                              );
                            } else {
                              await ApiService.storage.delete(
                                key: _rememberedLoginKey,
                              );
                            }
                            if (!context.mounted) return;
                            Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const DashboardScreen(),
                              ),
                            );
                          } else {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  loginController.lastError.isEmpty
                                      ? 'Invalid login or password.'
                                      : loginController.lastError,
                                ),
                              ),
                            );
                          }
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: isLoading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text(
                          'LOGIN',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: isLoading
                      ? null
                      : () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) =>
                                  const ExistingCustomerFirstLoginScreen(),
                            ),
                          ),
                  icon: const Icon(Icons.history_rounded),
                  label: const Text('EXISTING CUSTOMER FIRST LOGIN'),
                ),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: isLoading
                    ? null
                    : () => Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const CustomerOnboardingScreen(),
                          ),
                        ),
                icon: const Icon(Icons.person_add_alt_1),
                label: const Text('CREATE NEW CUSTOMER ACCOUNT'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
