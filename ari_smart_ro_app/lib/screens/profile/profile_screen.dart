import 'package:flutter/material.dart';

import '../../models/profile_model.dart';
import '../../services/api_service.dart';
import '../../services/profile_service.dart';
import '../login/login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ProfileService _service = ProfileService();

  ProfileModel? _profile;
  bool _isLoading = true;
  bool _isLoggingOut = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final profile = await _service.getProfile();
      if (!mounted) return;

      setState(() {
        _profile = profile;
        _isLoading = false;
      });
    } catch (error) {
      debugPrint('Unable to load profile: $error');
      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _errorMessage = 'Unable to load your profile. Please try again.';
      });
    }
  }

  Future<void> _logout() async {
    if (_isLoggingOut) return;

    setState(() => _isLoggingOut = true);

    try {
      await ApiService.logout();
      if (!mounted) return;

      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    } catch (error) {
      debugPrint('Logout failed: $error');
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not log out. Please try again.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      setState(() => _isLoggingOut = false);
    }
  }

  void _showComingSoon(String feature) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$feature will be available soon.'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_profile == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('My Profile')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.person_off_outlined, size: 56),
                const SizedBox(height: 12),
                Text(
                  _errorMessage ?? 'Profile not found.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _loadProfile,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Try Again'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final profile = _profile!;
    final topPadding = MediaQuery.of(context).padding.top;

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8FC),
      body: RefreshIndicator(
        onRefresh: _loadProfile,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: _ProfileHeader(profile: profile, topPadding: topPadding),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  const _SectionTitle(title: 'Personal Information'),
                  const SizedBox(height: 10),
                  _InfoCard(
                    children: [
                      _InfoRow(Icons.phone_outlined, 'Phone', profile.phone),
                      _InfoRow(
                        Icons.badge_outlined,
                        'Employee ID',
                        profile.employeeId,
                      ),
                      _InfoRow(
                        Icons.work_outline,
                        'Designation',
                        profile.designation,
                      ),
                      _InfoRow(Icons.email_outlined, 'Email', profile.email),
                      _InfoRow(
                        Icons.calendar_today_outlined,
                        'Joining Date',
                        profile.joiningDate,
                      ),
                      _InfoRow(
                        Icons.person_outline,
                        'Gender',
                        profile.gender,
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  const _SectionTitle(title: 'Address'),
                  const SizedBox(height: 10),
                  _InfoCard(
                    children: [
                      _InfoRow(
                        Icons.location_city_outlined,
                        'City',
                        profile.city,
                      ),
                      _InfoRow(Icons.map_outlined, 'State', profile.state),
                      _InfoRow(
                        Icons.home_outlined,
                        'Address',
                        profile.address,
                        isLast: true,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  _ActionButton(
                    icon: Icons.edit_outlined,
                    label: 'Edit Profile',
                    onPressed: () => _showComingSoon('Edit Profile'),
                  ),
                  const SizedBox(height: 12),
                  _ActionButton(
                    icon: Icons.lock_outline,
                    label: 'Change Password',
                    onPressed: () => _showComingSoon('Change Password'),
                  ),
                  const SizedBox(height: 12),
                  _ActionButton(
                    icon: Icons.logout_rounded,
                    label: _isLoggingOut ? 'Logging out...' : 'Logout',
                    onPressed: _isLoggingOut ? null : _logout,
                    isDestructive: true,
                  ),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.profile, required this.topPadding});

  final ProfileModel profile;
  final double topPadding;

  @override
  Widget build(BuildContext context) {
    final photoUrl = profile.photo?.trim() ?? '';

    return Container(
      padding: EdgeInsets.fromLTRB(20, topPadding + 14, 20, 36),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF0A70D8), Color(0xFF17A0D5)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              IconButton(
                onPressed: () => Navigator.of(context).maybePop(),
                icon: const Icon(Icons.arrow_back_ios_new_rounded),
                color: Colors.white,
                tooltip: 'Back',
              ),
              const Expanded(
                child: Text(
                  'My Profile',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 48),
            ],
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(4),
            decoration: const BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
            ),
            child: CircleAvatar(
              radius: 54,
              backgroundColor: const Color(0xFFE1F1FF),
              backgroundImage: photoUrl.isNotEmpty ? NetworkImage(photoUrl) : null,
              onBackgroundImageError:
                  photoUrl.isNotEmpty ? (_, __) {} : null,
              child: photoUrl.isEmpty
                  ? const Icon(Icons.person_rounded, size: 58, color: Color(0xFF0A70D8))
                  : null,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            _displayValue(profile.fullName),
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 25,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              borderRadius: BorderRadius.circular(99),
              border: Border.all(color: Colors.white.withOpacity(0.35)),
            ),
            child: Text(
              _displayValue(profile.role).toUpperCase(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Text(
        title,
        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
      );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) => Card(
        elevation: 0,
        color: Colors.white,
        clipBehavior: Clip.antiAlias,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: const BorderSide(color: Color(0xFFE5EAF2)),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Column(children: children),
        ),
      );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.icon, this.label, this.value, {this.isLast = false});

  final IconData icon;
  final String label;
  final String value;
  final bool isLast;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: const Color(0xFFEAF5FF),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: const Color(0xFF0A70D8), size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        label,
                        style: const TextStyle(color: Color(0xFF687386), fontSize: 12),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        _displayValue(value),
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (!isLast) const Divider(height: 1, color: Color(0xFFEEF1F5)),
        ],
      );
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.isDestructive = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool isDestructive;

  @override
  Widget build(BuildContext context) {
    final color = isDestructive ? const Color(0xFFD63B3B) : const Color(0xFF0A70D8);

    return SizedBox(
      width: double.infinity,
      height: 52,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
        style: OutlinedButton.styleFrom(
          foregroundColor: color,
          side: BorderSide(color: color.withOpacity(0.45)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

String _displayValue(String value) {
  final trimmed = value.trim();
  return trimmed.isEmpty ? 'Not available' : trimmed;
}
