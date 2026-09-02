import 'package:flutter/material.dart';

import '../../models/shop_product_model.dart';
import '../../services/customer_engagement_service.dart';
import '../../services/shop_service.dart';
import '../customer/referral_screen.dart';
import '../login/login_screen.dart';
import '../rent/rent_payment_screen.dart';
import '../service/service_list_screen.dart';
import 'about_ari_screen.dart';
import 'guest_account_screen.dart';
import 'guest_services_screen.dart';

class ShopScreen extends StatefulWidget {
  const ShopScreen({
    super.key,
    this.service = const ShopService(),
    this.guestMode = false,
  });

  final ShopService service;
  final bool guestMode;

  @override
  State<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends State<ShopScreen> {
  static const navy = Color(0xFF082D4F);
  static const blue = Color(0xFF0B6FD3);
  static const cyan = Color(0xFF32C7E8);
  static const ice = Color(0xFFF4F9FC);
  static const ink = Color(0xFF102A43);
  static const muted = Color(0xFF66788A);

  final _searchController = TextEditingController();
  final _engagementService = const CustomerEngagementService();
  late Future<List<ShopProduct>> _catalog;
  Future<CustomerEngagementData>? _engagement;
  String _selectedCategory = 'All';
  int _unreadCount = 0;

  @override
  void initState() {
    super.initState();
    _catalog = widget.service.fetchCatalog();
    _engagement = _loadEngagement();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<CustomerEngagementData> _loadEngagement() async {
    try {
      final data = await _engagementService.fetch();
      if (mounted && _unreadCount != data.unreadCount) {
        setState(() => _unreadCount = data.unreadCount);
      }
      return data;
    } catch (_) {
      return CustomerEngagementData.empty;
    }
  }

  void _loadCatalog({String? query}) {
    setState(() {
      _selectedCategory = 'All';
      _catalog = widget.service.fetchCatalog(
        query: query ?? _searchController.text,
      );
    });
  }

  Future<void> _refresh() async {
    final next = widget.service.fetchCatalog(query: _searchController.text);
    setState(() => _catalog = next);
    await next;
    final nextEngagement = _loadEngagement();
    setState(() => _engagement = nextEngagement);
    await nextEngagement;
  }

  void _openLogin() => Navigator.of(
        context,
      ).push(MaterialPageRoute(builder: (_) => const LoginScreen()));

  void _openPage(Widget screen) => Navigator.of(
        context,
      ).push(MaterialPageRoute(builder: (_) => screen));

  void _openMemberFeature(Widget screen) {
    if (widget.guestMode) {
      _openLogin();
      return;
    }
    _openPage(screen);
  }

  void _openService() => widget.guestMode
      ? _openPage(
          const GuestServiceDetailScreen(type: GuestServiceType.service),
        )
      : _openMemberFeature(const ServiceListScreen());

  void _openAmc() => widget.guestMode
      ? _openPage(const GuestServiceDetailScreen(type: GuestServiceType.amc))
      : _openMemberFeature(const ServiceListScreen());

  void _openRent() => widget.guestMode
      ? _openPage(
          const GuestServiceDetailScreen(type: GuestServiceType.rental),
        )
      : _openMemberFeature(const RentPaymentScreen());

  void _handleGuestNavigation(int index) {
    switch (index) {
      case 0:
        _searchController.clear();
        _loadCatalog(query: '');
      case 1:
        _openPage(const GuestServicesScreen());
      case 2:
        _openPage(const AboutAriScreen());
      case 3:
        _openPage(const GuestAccountScreen());
    }
  }

  Future<void> _handleEngagement(Map<String, dynamic> item) async {
    final id = (item['id'] as num?)?.toInt();
    if (id != null) {
      await _engagementService.markRead(id);
      if (mounted && _unreadCount > 0) setState(() => _unreadCount--);
    }
    if (!mounted) return;
    switch (item['action']?.toString()) {
      case 'RENT':
        _openRent();
      case 'SERVICE':
        _openService();
      case 'REFERRAL':
        _openMemberFeature(const ReferralScreen());
      case 'SHOP':
        _searchController.clear();
        _loadCatalog(query: '');
    }
  }

  void _showProduct(ShopProduct product) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: .76,
        minChildSize: .55,
        maxChildSize: .95,
        builder: (_, controller) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(30)),
          ),
          child: ListView(
            controller: controller,
            padding: const EdgeInsets.fromLTRB(22, 12, 22, 34),
            children: [
              Center(
                child: Container(
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFD7E3EA),
                    borderRadius: BorderRadius.circular(20),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Container(
                height: 250,
                decoration: BoxDecoration(
                  color: ice,
                  borderRadius: BorderRadius.circular(26),
                ),
                child: product.imageUrls.isEmpty
                    ? const _ProductVisual(size: 120)
                    : PageView.builder(
                        itemCount: product.imageUrls.length,
                        itemBuilder: (_, index) => Padding(
                          padding: const EdgeInsets.all(20),
                          child: Image.network(
                            product.imageUrls[index],
                            fit: BoxFit.contain,
                            errorBuilder: (_, _, _) =>
                                const _ProductVisual(size: 120),
                          ),
                        ),
                      ),
              ),
              const SizedBox(height: 20),
              Text(
                product.modelName,
                style: const TextStyle(
                  color: ink,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '${product.categoryName} • ${product.capacity}',
                style: const TextStyle(color: muted),
              ),
              const SizedBox(height: 15),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _InfoPill(
                    icon: Icons.verified_rounded,
                    label: '${product.warrantyMonths} mo warranty',
                  ),
                  _InfoPill(
                    icon: product.stockQuantity > 0
                        ? Icons.check_circle_rounded
                        : Icons.cancel_rounded,
                    label: product.stockQuantity > 0
                        ? 'In stock'
                        : 'Unavailable',
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '₹${product.sellingPrice.toStringAsFixed(0)}',
                    style: const TextStyle(
                      color: navy,
                      fontSize: 27,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  if (product.mrp > product.sellingPrice) ...[
                    const SizedBox(width: 10),
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(
                        '₹${product.mrp.toStringAsFixed(0)}',
                        style: const TextStyle(
                          color: muted,
                          decoration: TextDecoration.lineThrough,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              if (product.description.trim().isNotEmpty) ...[
                const SizedBox(height: 22),
                const _SectionTitle('About this purifier'),
                const SizedBox(height: 8),
                Text(
                  product.description,
                  style: const TextStyle(color: muted, height: 1.55),
                ),
              ],
              if (product.features.isNotEmpty) ...[
                const SizedBox(height: 22),
                const _SectionTitle('Key features'),
                const SizedBox(height: 10),
                ...product.features.take(6).map(
                      (feature) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(
                              Icons.check_circle_rounded,
                              size: 19,
                              color: Color(0xFF16A085),
                            ),
                            const SizedBox(width: 10),
                            Expanded(child: Text(feature)),
                          ],
                        ),
                      ),
                    ),
              ],
              const SizedBox(height: 22),
              SizedBox(
                height: 54,
                child: FilledButton.icon(
                  onPressed: widget.guestMode
                      ? _openLogin
                      : () => Navigator.pop(context),
                  icon: Icon(
                    widget.guestMode
                        ? Icons.login_rounded
                        : Icons.support_agent_rounded,
                  ),
                  label: Text(
                    widget.guestMode
                        ? 'LOGIN TO CONTINUE'
                        : 'CONTACT ARI TEAM',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ice,
      body: SafeArea(
        bottom: false,
        child: FutureBuilder<List<ShopProduct>>(
          future: _catalog,
          builder: (context, snapshot) {
            final products = snapshot.data ?? const <ShopProduct>[];
            final categories = <String>{
              'All',
              ...products
                  .map((item) => item.categoryName)
                  .where((name) => name.trim().isNotEmpty),
            }.toList();
            final visible = _selectedCategory == 'All'
                ? products
                : products
                    .where((item) => item.categoryName == _selectedCategory)
                    .toList();

            return RefreshIndicator(
              onRefresh: _refresh,
              child: CustomScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                slivers: [
                  SliverToBoxAdapter(
                    child: _TopHeader(
                      guestMode: widget.guestMode,
                      unreadCount: _unreadCount,
                      onLogin: _openLogin,
                      onRefresh: _refresh,
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: _StoreSearch(
                      controller: _searchController,
                      onSearch: _loadCatalog,
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: _DeliveryStrip(
                      guestMode: widget.guestMode,
                      onTap: widget.guestMode ? _openLogin : null,
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: _HeroBanner(
                      product: products.isEmpty ? null : products.first,
                      onExplore: () {
                        _searchController.clear();
                        _loadCatalog(query: '');
                      },
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: _QuickActions(
                      onStore: () => _loadCatalog(query: ''),
                      onService: _openService,
                      onAmc: _openAmc,
                      onRent: _openRent,
                      onFilters: () {
                        _searchController.text = 'filter';
                        _loadCatalog(query: 'filter');
                      },
                      onReferral: () =>
                          _openMemberFeature(const ReferralScreen()),
                    ),
                  ),
                  if (_engagement != null && !widget.guestMode)
                    SliverToBoxAdapter(
                      child: FutureBuilder<CustomerEngagementData>(
                        future: _engagement,
                        builder: (_, engagementSnapshot) {
                          final data = engagementSnapshot.data ??
                              CustomerEngagementData.empty;
                          if (data.items.isEmpty && data.paymentAlert == null) {
                            return const SizedBox.shrink();
                          }
                          return _EngagementCard(
                            data: data,
                            onAction: _handleEngagement,
                            onPayment: _openRent,
                          );
                        },
                      ),
                    ),
                  SliverToBoxAdapter(
                    child: _CategoryStrip(
                      categories: categories,
                      selected: _selectedCategory,
                      onSelected: (value) =>
                          setState(() => _selectedCategory = value),
                    ),
                  ),
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(18, 22, 18, 12),
                      child: Row(
                        children: [
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Recommended for you',
                                  style: TextStyle(
                                    color: ink,
                                    fontSize: 21,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                                SizedBox(height: 3),
                                Text(
                                  'Smart water solutions selected by ARI',
                                  style: TextStyle(color: muted, fontSize: 12.5),
                                ),
                              ],
                            ),
                          ),
                          if (products.isNotEmpty)
                            Text(
                              '${visible.length} items',
                              style: const TextStyle(
                                color: blue,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                  if (snapshot.connectionState == ConnectionState.waiting)
                    const SliverToBoxAdapter(
                      child: Padding(
                        padding: EdgeInsets.all(42),
                        child: Center(child: CircularProgressIndicator()),
                      ),
                    )
                  else if (snapshot.hasError)
                    SliverToBoxAdapter(
                      child: _CatalogError(onRetry: _loadCatalog),
                    )
                  else if (visible.isEmpty)
                    const SliverToBoxAdapter(child: _EmptyCatalog())
                  else
                    SliverPadding(
                      padding: const EdgeInsets.fromLTRB(18, 0, 18, 24),
                      sliver: SliverGrid(
                        delegate: SliverChildBuilderDelegate(
                          (_, index) => _ProductCard(
                            product: visible[index],
                            onTap: () => _showProduct(visible[index]),
                          ),
                          childCount: visible.length,
                        ),
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          crossAxisSpacing: 12,
                          mainAxisSpacing: 12,
                          childAspectRatio: .68,
                        ),
                      ),
                    ),
                  SliverToBoxAdapter(
                    child: _ServiceBanner(
                      onService: _openService,
                      onAmc: _openAmc,
                    ),
                  ),
                  const SliverToBoxAdapter(child: _TrustStrip()),
                  const SliverToBoxAdapter(child: SizedBox(height: 110)),
                ],
              ),
            );
          },
        ),
      ),
      bottomNavigationBar: widget.guestMode
          ? NavigationBar(
              selectedIndex: 0,
              onDestinationSelected: _handleGuestNavigation,
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home_rounded),
                  label: 'Home',
                ),
                NavigationDestination(
                  icon: Icon(Icons.home_repair_service_outlined),
                  selectedIcon: Icon(Icons.home_repair_service_rounded),
                  label: 'Services',
                ),
                NavigationDestination(
                  icon: Icon(Icons.info_outline_rounded),
                  selectedIcon: Icon(Icons.info_rounded),
                  label: 'About',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline_rounded),
                  selectedIcon: Icon(Icons.person_rounded),
                  label: 'Account',
                ),
              ],
            )
          : null,
    );
  }
}

class _TopHeader extends StatelessWidget {
  const _TopHeader({
    required this.guestMode,
    required this.unreadCount,
    required this.onLogin,
    required this.onRefresh,
  });

  final bool guestMode;
  final int unreadCount;
  final VoidCallback onLogin;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 12, 12, 10),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [_ShopScreenState.blue, _ShopScreenState.cyan],
                ),
                borderRadius: BorderRadius.circular(15),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x220B6FD3),
                    blurRadius: 18,
                    offset: Offset(0, 7),
                  ),
                ],
              ),
              child: const Icon(Icons.water_drop_rounded, color: Colors.white),
            ),
            const SizedBox(width: 11),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'ARI SMART RO',
                    style: TextStyle(
                      color: _ShopScreenState.ink,
                      fontSize: 18,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  SizedBox(height: 1),
                  Text(
                    'Pure water. Smarter living.',
                    style: TextStyle(
                      color: _ShopScreenState.muted,
                      fontSize: 11.5,
                    ),
                  ),
                ],
              ),
            ),
            if (!guestMode)
              Badge(
                isLabelVisible: unreadCount > 0,
                label: Text(unreadCount > 9 ? '9+' : '$unreadCount'),
                child: IconButton.filledTonal(
                  onPressed: onRefresh,
                  icon: const Icon(Icons.notifications_none_rounded),
                ),
              )
            else
              TextButton.icon(
                onPressed: onLogin,
                icon: const Icon(Icons.person_outline_rounded, size: 20),
                label: const Text('Login'),
              ),
          ],
        ),
      );
}

class _StoreSearch extends StatelessWidget {
  const _StoreSearch({required this.controller, required this.onSearch});

  final TextEditingController controller;
  final VoidCallback onSearch;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 6, 18, 8),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(18),
            boxShadow: const [
              BoxShadow(
                color: Color(0x0D0B3954),
                blurRadius: 18,
                offset: Offset(0, 6),
              ),
            ],
          ),
          child: TextField(
            controller: controller,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => onSearch(),
            decoration: InputDecoration(
              hintText: 'Search RO, filters, parts or service',
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: IconButton(
                tooltip: 'Search',
                onPressed: onSearch,
                icon: const Icon(Icons.arrow_forward_rounded),
              ),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              filled: false,
            ),
          ),
        ),
      );
}

class _DeliveryStrip extends StatelessWidget {
  const _DeliveryStrip({required this.guestMode, this.onTap});

  final bool guestMode;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 4, 18, 12),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
            decoration: BoxDecoration(
              color: const Color(0xFFE9F6FC),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFD0EAF5)),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.location_on_outlined,
                  color: _ShopScreenState.blue,
                  size: 20,
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    guestMode
                        ? 'Login to set delivery & service location'
                        : 'Delivery and service support at your saved location',
                    style: const TextStyle(
                      color: _ShopScreenState.ink,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                const Icon(
                  Icons.chevron_right_rounded,
                  color: _ShopScreenState.muted,
                ),
              ],
            ),
          ),
        ),
      );
}

class _HeroBanner extends StatelessWidget {
  const _HeroBanner({required this.product, required this.onExplore});

  final ShopProduct? product;
  final VoidCallback onExplore;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 2, 18, 18),
        child: Container(
          constraints: const BoxConstraints(minHeight: 220),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [
                _ShopScreenState.navy,
                _ShopScreenState.blue,
                _ShopScreenState.cyan,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(28),
            boxShadow: const [
              BoxShadow(
                color: Color(0x330B6FD3),
                blurRadius: 28,
                offset: Offset(0, 12),
              ),
            ],
          ),
          child: Stack(
            children: [
              Positioned(
                right: 14,
                bottom: 12,
                child: SizedBox(
                  width: 135,
                  height: 170,
                  child: product == null || product!.imageUrls.isEmpty
                      ? const _ProductVisual(size: 92, light: true)
                      : Image.network(
                          product!.imageUrls.first,
                          fit: BoxFit.contain,
                          errorBuilder: (_, _, _) =>
                              const _ProductVisual(size: 92, light: true),
                        ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(22, 24, 155, 22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: .14),
                        borderRadius: BorderRadius.circular(50),
                      ),
                      child: const Text(
                        'SMART WATER CARE',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.1,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Upgrade your\nwater experience',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 25,
                        height: 1.08,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 9),
                    const Text(
                      'Purifiers, filters, service and care—inside one premium app.',
                      style: TextStyle(
                        color: Color(0xDDFFFFFF),
                        fontSize: 12.5,
                        height: 1.35,
                      ),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: onExplore,
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: _ShopScreenState.navy,
                        minimumSize: const Size(0, 42),
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                      ),
                      child: const Text('Explore range'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}

class _QuickActions extends StatelessWidget {
  const _QuickActions({
    required this.onStore,
    required this.onService,
    required this.onAmc,
    required this.onRent,
    required this.onFilters,
    required this.onReferral,
  });

  final VoidCallback onStore;
  final VoidCallback onService;
  final VoidCallback onAmc;
  final VoidCallback onRent;
  final VoidCallback onFilters;
  final VoidCallback onReferral;

  @override
  Widget build(BuildContext context) {
    final items = [
      (Icons.shopping_bag_outlined, 'RO Store', onStore),
      (Icons.build_circle_outlined, 'Service', onService),
      (Icons.verified_outlined, 'AMC Plans', onAmc),
      (Icons.currency_rupee_rounded, 'RO on Rent', onRent),
      (Icons.filter_alt_outlined, 'Filters', onFilters),
      (Icons.card_giftcard_rounded, 'Refer & Earn', onReferral),
    ];

    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 8),
      child: GridView.builder(
        itemCount: items.length,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 3,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          childAspectRatio: 1.05,
        ),
        itemBuilder: (_, index) {
          final item = items[index];
          return InkWell(
            onTap: item.$3,
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFFE0EAF0)),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: const Color(0xFFEAF6FC),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      item.$1,
                      color: _ShopScreenState.blue,
                      size: 22,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    item.$2,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: _ShopScreenState.ink,
                      fontWeight: FontWeight.w800,
                      fontSize: 11.5,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _CategoryStrip extends StatelessWidget {
  const _CategoryStrip({
    required this.categories,
    required this.selected,
    required this.onSelected,
  });

  final List<String> categories;
  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    if (categories.length <= 1) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(18, 22, 18, 10),
          child: _SectionTitle('Shop by category'),
        ),
        SizedBox(
          height: 46,
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: 18),
            scrollDirection: Axis.horizontal,
            itemCount: categories.length,
            separatorBuilder: (_, _) => const SizedBox(width: 8),
            itemBuilder: (_, index) {
              final category = categories[index];
              final active = selected == category;
              return ChoiceChip(
                label: Text(category),
                selected: active,
                onSelected: (_) => onSelected(category),
                showCheckmark: false,
                selectedColor: _ShopScreenState.blue,
                backgroundColor: Colors.white,
                labelStyle: TextStyle(
                  color: active ? Colors.white : _ShopScreenState.ink,
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({required this.product, required this.onTap});

  final ShopProduct product;
  final VoidCallback onTap;

  int get discount {
    if (product.mrp <= 0 || product.sellingPrice >= product.mrp) return 0;
    return ((product.mrp - product.sellingPrice) / product.mrp * 100).round();
  }

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(22),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: const Color(0xFFE2EBF0)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Stack(
                    children: [
                      Container(
                        width: double.infinity,
                        margin: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: _ShopScreenState.ice,
                          borderRadius: BorderRadius.circular(17),
                        ),
                        child: product.imageUrls.isEmpty
                            ? const _ProductVisual(size: 70)
                            : Padding(
                                padding: const EdgeInsets.all(12),
                                child: Image.network(
                                  product.imageUrls.first,
                                  fit: BoxFit.contain,
                                  errorBuilder: (_, _, _) =>
                                      const _ProductVisual(size: 70),
                                ),
                              ),
                      ),
                      if (discount > 0)
                        Positioned(
                          left: 13,
                          top: 13,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 5,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0F9D72),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '$discount% OFF',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 9,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        product.modelName,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: _ShopScreenState.ink,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        '${product.capacity} • ${product.warrantyMonths} mo warranty',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: _ShopScreenState.muted,
                          fontSize: 10.5,
                        ),
                      ),
                      const SizedBox(height: 9),
                      Text(
                        '₹${product.sellingPrice.toStringAsFixed(0)}',
                        style: const TextStyle(
                          color: _ShopScreenState.navy,
                          fontSize: 17,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _ServiceBanner extends StatelessWidget {
  const _ServiceBanner({required this.onService, required this.onAmc});

  final VoidCallback onService;
  final VoidCallback onAmc;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 18),
        child: Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFE8F7FC), Color(0xFFF4FBFE)],
            ),
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: const Color(0xFFD5EDF5)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.home_repair_service_rounded,
                color: _ShopScreenState.blue,
                size: 34,
              ),
              const SizedBox(height: 13),
              const Text(
                'Already own an RO?',
                style: TextStyle(
                  color: _ShopScreenState.ink,
                  fontSize: 21,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 5),
              const Text(
                'Book service, manage maintenance and keep your purifier performing at its best.',
                style: TextStyle(
                  color: _ShopScreenState.muted,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: onService,
                      icon: const Icon(Icons.build_rounded),
                      label: const Text('Book Service'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onAmc,
                      icon: const Icon(Icons.verified_outlined),
                      label: const Text('AMC Plans'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
}

class _TrustStrip extends StatelessWidget {
  const _TrustStrip();

  @override
  Widget build(BuildContext context) {
    const items = [
      (Icons.verified_rounded, 'Genuine\nproducts'),
      (Icons.handyman_rounded, 'Professional\ninstallation'),
      (Icons.history_rounded, 'Digital service\nhistory'),
      (Icons.support_agent_rounded, 'Customer\nsupport'),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionTitle('Why choose ARI SMART RO'),
          const SizedBox(height: 12),
          Row(
            children: items
                .map(
                  (item) => Expanded(
                    child: Column(
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: const Color(0xFFEAF6FC),
                            borderRadius: BorderRadius.circular(15),
                          ),
                          child: Icon(item.$1, color: _ShopScreenState.blue),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          item.$2,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: _ShopScreenState.muted,
                            fontSize: 9.5,
                            height: 1.25,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _EngagementCard extends StatelessWidget {
  const _EngagementCard({
    required this.data,
    required this.onAction,
    required this.onPayment,
  });

  final CustomerEngagementData data;
  final ValueChanged<Map<String, dynamic>> onAction;
  final VoidCallback onPayment;

  @override
  Widget build(BuildContext context) {
    final first = data.items.isEmpty ? null : data.items.first;
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 0),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: const Color(0xFFE0EAF0)),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.notifications_active_outlined,
              color: Color(0xFFB7791F),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    first?['title']?.toString() ??
                        (data.paymentAlert != null
                            ? 'Payment reminder'
                            : 'ARI update'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: _ShopScreenState.ink,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    first?['message']?.toString() ??
                        'Tap to review your account update.',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: _ShopScreenState.muted,
                      fontSize: 11.5,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: first != null ? () => onAction(first) : onPayment,
              icon: const Icon(Icons.arrow_forward_rounded),
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogError extends StatelessWidget {
  const _CatalogError({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          children: [
            const Icon(Icons.cloud_off_rounded, size: 42, color: _ShopScreenState.muted),
            const SizedBox(height: 10),
            const Text('Unable to load the store right now.'),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Try again'),
            ),
          ],
        ),
      );
}

class _EmptyCatalog extends StatelessWidget {
  const _EmptyCatalog();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.all(34),
        child: Column(
          children: [
            Icon(Icons.inventory_2_outlined, size: 44, color: _ShopScreenState.muted),
            SizedBox(height: 12),
            Text(
              'No products found. Try another category or search term.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _ShopScreenState.muted),
            ),
          ],
        ),
      );
}

class _ProductVisual extends StatelessWidget {
  const _ProductVisual({required this.size, this.light = false});

  final double size;
  final bool light;

  @override
  Widget build(BuildContext context) => Center(
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: light
                ? Colors.white.withValues(alpha: .14)
                : const Color(0xFFE7F5FB),
            borderRadius: BorderRadius.circular(size * .28),
          ),
          child: Icon(
            Icons.water_drop_rounded,
            size: size * .48,
            color: light ? Colors.white : _ShopScreenState.blue,
          ),
        ),
      );
}

class _InfoPill extends StatelessWidget {
  const _InfoPill({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: const Color(0xFFF0F7FA),
          borderRadius: BorderRadius.circular(50),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 15, color: _ShopScreenState.blue),
            const SizedBox(width: 5),
            Text(
              label,
              style: const TextStyle(
                color: _ShopScreenState.ink,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          color: _ShopScreenState.ink,
          fontSize: 18,
          fontWeight: FontWeight.w900,
        ),
      );
}
