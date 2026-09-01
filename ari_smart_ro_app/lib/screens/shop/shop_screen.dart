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
  static const _blue = Color(0xFF0868D7);
  static const _navy = Color(0xFF07315E);
  final _searchController = TextEditingController();
  final _engagementService = const CustomerEngagementService();
  late Future<List<ShopProduct>> _catalog;
  Future<CustomerEngagementData>? _engagement;
  int _unreadCount = 0;
  String _selectedCategory = 'All';

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

  void _loadCatalog() => setState(() {
    _selectedCategory = 'All';
    _catalog = widget.service.fetchCatalog(query: _searchController.text);
  });

  Future<void> _refresh() async {
    final next = widget.service.fetchCatalog(query: _searchController.text);
    setState(() => _catalog = next);
    await next;
    final engagement = _loadEngagement();
    setState(() => _engagement = engagement);
    await engagement;
  }

  Future<CustomerEngagementData> _loadEngagement() async {
    try {
      final data = await _engagementService.fetch();
      if (mounted && data.unreadCount != _unreadCount) {
        setState(() => _unreadCount = data.unreadCount);
      }
      return data;
    } catch (_) {
      return CustomerEngagementData.empty;
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
        _openMemberFeature(const RentPaymentScreen());
      case 'SERVICE':
        _openMemberFeature(const ServiceListScreen());
      case 'REFERRAL':
        _openMemberFeature(const ReferralScreen());
      case 'SHOP':
        _searchController.clear();
        _loadCatalog();
    }
  }

  void _openLogin() => Navigator.of(
    context,
  ).push(MaterialPageRoute(builder: (_) => const LoginScreen()));

  void _openGuestPage(Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));

  void _handleGuestNavigation(int index) {
    switch (index) {
      case 0:
        _searchController.clear();
        _loadCatalog();
        return;
      case 1:
        _openGuestPage(const GuestServicesScreen());
        return;
      case 2:
        _openGuestPage(const AboutAriScreen());
        return;
      case 3:
        _openGuestPage(const GuestAccountScreen());
        return;
    }
  }

  void _openMemberFeature(Widget screen) {
    if (widget.guestMode) {
      _openLogin();
      return;
    }
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  void _openImageViewer(List<String> images, int initialIndex) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) =>
            _FullScreenGallery(images: images, initialIndex: initialIndex),
        fullscreenDialog: true,
      ),
    );
  }

  void _showProduct(ShopProduct product) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  height: 280,
                  child: product.imageUrls.isEmpty
                      ? const Center(child: _ProductVisual(size: 150))
                      : PageView.builder(
                          itemCount: product.imageUrls.length,
                          itemBuilder: (_, index) => GestureDetector(
                            onTap: () =>
                                _openImageViewer(product.imageUrls, index),
                            child: Image.network(
                              product.imageUrls[index],
                              fit: BoxFit.contain,
                              errorBuilder: (_, _, _) => const Center(
                                child: _ProductVisual(size: 150),
                              ),
                            ),
                          ),
                        ),
                ),
                if (product.imageUrls.isNotEmpty)
                  Center(
                    child: Text(
                      product.imageUrls.length > 1
                          ? 'Swipe photos • Tap to zoom'
                          : 'Tap photo to zoom',
                      style: Theme.of(
                        context,
                      ).textTheme.bodySmall?.copyWith(color: Colors.black54),
                    ),
                  ),
                const SizedBox(height: 18),
                Text(
                  product.modelName,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '${product.categoryName} • ${product.capacity}',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(color: Colors.black54),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    const Icon(Icons.verified_outlined, color: _blue),
                    const SizedBox(width: 8),
                    Text('${product.warrantyMonths} months warranty'),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  '₹${product.sellingPrice.toStringAsFixed(0)}',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: _navy,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                if (product.mrp > product.sellingPrice) ...[
                  const SizedBox(height: 3),
                  Text(
                    'MRP ₹${product.mrp.toStringAsFixed(0)}',
                    style: const TextStyle(
                      color: Colors.black45,
                      decoration: TextDecoration.lineThrough,
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                Text(
                  product.stockQuantity > 0
                      ? 'In stock'
                      : 'Currently unavailable',
                  style: TextStyle(
                    color: product.stockQuantity > 0
                        ? Colors.green.shade700
                        : Colors.red.shade700,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (product.description.trim().isNotEmpty) ...[
                  const SizedBox(height: 20),
                  Text(
                    'About this product',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Text(
                    product.description,
                    style: const TextStyle(height: 1.45),
                  ),
                ],
                if (product.features.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  Text(
                    'Key features',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 7),
                  ...product.features.map(
                    (feature) => Padding(
                      padding: const EdgeInsets.only(bottom: 7),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Padding(
                            padding: EdgeInsets.only(top: 3),
                            child: Icon(
                              Icons.check_circle,
                              color: _blue,
                              size: 17,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(child: Text(feature)),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton.icon(
                    onPressed: widget.guestMode
                        ? _openLogin
                        : () => Navigator.pop(context),
                    icon: Icon(
                      widget.guestMode ? Icons.login : Icons.support_agent,
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
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FB),
      appBar: AppBar(
        backgroundColor: _blue,
        foregroundColor: Colors.white,
        elevation: 0,
        titleSpacing: 16,
        title: const Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: Colors.white,
              child: Icon(Icons.water_drop, color: _blue, size: 21),
            ),
            SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ARI SMART RO',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    letterSpacing: .4,
                  ),
                ),
                Text(
                  'Pure water. Smart living.',
                  style: TextStyle(fontSize: 10, color: Colors.white70),
                ),
              ],
            ),
          ],
        ),
        actions: [
          if (!widget.guestMode)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: Badge(
                isLabelVisible: _unreadCount > 0,
                label: Text(_unreadCount > 9 ? '9+' : '$_unreadCount'),
                child: IconButton(
                  tooltip: 'Offers & alerts',
                  onPressed: _refresh,
                  icon: const Icon(Icons.notifications_none_rounded),
                ),
              ),
            ),
          if (widget.guestMode)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: TextButton.icon(
                onPressed: _openLogin,
                style: TextButton.styleFrom(foregroundColor: Colors.white),
                icon: const Icon(Icons.account_circle_outlined),
                label: const Text(
                  'Login',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ),
        ],
      ),
      body: FutureBuilder<List<ShopProduct>>(
        future: _catalog,
        builder: (context, snapshot) {
          final products = snapshot.data ?? const <ShopProduct>[];
          final categories = <String>{
            'All',
            ...products
                .map((p) => p.categoryName)
                .where((name) => name.trim().isNotEmpty),
          }.toList();
          final visible = _selectedCategory == 'All'
              ? products
              : products
                    .where((p) => p.categoryName == _selectedCategory)
                    .toList();

          return RefreshIndicator(
            onRefresh: _refresh,
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: _Hero(
                    imageUrl:
                        products.isEmpty || products.first.imageUrls.isEmpty
                        ? null
                        : products.first.imageUrls.first,
                    onShopNow: () {
                      _searchController.clear();
                      _loadCatalog();
                    },
                  ),
                ),
                const SliverToBoxAdapter(child: _AssuranceStrip()),
                if (_engagement != null)
                  SliverToBoxAdapter(
                    child: FutureBuilder<CustomerEngagementData>(
                      future: _engagement,
                      builder: (_, snapshot) => _CustomerEngagementSection(
                        data: snapshot.data ?? CustomerEngagementData.empty,
                        onAction: _handleEngagement,
                        onPayment: () =>
                            _openMemberFeature(const RentPaymentScreen()),
                      ),
                    ),
                  ),
                SliverToBoxAdapter(
                  child: _ServiceShortcuts(
                    onService: () => widget.guestMode
                        ? _openGuestPage(
                            const GuestServiceDetailScreen(
                              type: GuestServiceType.service,
                            ),
                          )
                        : _openMemberFeature(const ServiceListScreen()),
                    onAmc: () => widget.guestMode
                        ? _openGuestPage(
                            const GuestServiceDetailScreen(
                              type: GuestServiceType.amc,
                            ),
                          )
                        : _openMemberFeature(const ServiceListScreen()),
                    onRent: () => widget.guestMode
                        ? _openGuestPage(
                            const GuestServiceDetailScreen(
                              type: GuestServiceType.rental,
                            ),
                          )
                        : _openMemberFeature(const RentPaymentScreen()),
                    onParts: () {
                      _searchController.text = 'filter';
                      _loadCatalog();
                    },
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
                    child: TextField(
                      controller: _searchController,
                      textInputAction: TextInputAction.search,
                      onSubmitted: (_) => _loadCatalog(),
                      decoration: InputDecoration(
                        hintText: 'Search purifier, capacity or category',
                        prefixIcon: const Icon(Icons.search),
                        suffixIcon: IconButton(
                          onPressed: _loadCatalog,
                          icon: const Icon(Icons.arrow_forward_rounded),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: BorderSide.none,
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: const BorderSide(
                            color: Color(0xFFE2E8F0),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                if (categories.length > 1)
                  SliverToBoxAdapter(
                    child: SizedBox(
                      height: 54,
                      child: ListView.separated(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 6,
                        ),
                        scrollDirection: Axis.horizontal,
                        itemCount: categories.length,
                        separatorBuilder: (_, _) => const SizedBox(width: 8),
                        itemBuilder: (_, index) {
                          final category = categories[index];
                          return ChoiceChip(
                            label: Text(category),
                            selected: category == _selectedCategory,
                            onSelected: (_) =>
                                setState(() => _selectedCategory = category),
                          );
                        },
                      ),
                    ),
                  ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
                    child: Row(
                      children: [
                        Text(
                          'Explore our range',
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(
                                fontWeight: FontWeight.w800,
                                color: _navy,
                              ),
                        ),
                        const Spacer(),
                        if (products.isNotEmpty)
                          Text(
                            '${visible.length} products',
                            style: const TextStyle(color: Colors.black54),
                          ),
                      ],
                    ),
                  ),
                ),
                if (snapshot.connectionState == ConnectionState.waiting)
                  const SliverFillRemaining(
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (snapshot.hasError)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _StoreMessage(
                      icon: Icons.cloud_off_rounded,
                      title: 'Store is temporarily unavailable',
                      message:
                          'You can still explore Services, About and Account. Pull down or tap retry when the server is available.',
                      button: 'TRY AGAIN',
                      onPressed: _loadCatalog,
                    ),
                  )
                else if (visible.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _StoreMessage(
                      icon: Icons.water_drop_outlined,
                      title: products.isEmpty
                          ? 'Products coming soon'
                          : 'No matching products',
                      message: products.isEmpty
                          ? 'Our online catalogue is being prepared. Please check again shortly.'
                          : 'Try another category or search term.',
                      button: products.isEmpty ? 'REFRESH' : 'CLEAR SEARCH',
                      onPressed: products.isEmpty
                          ? _refresh
                          : () {
                              _searchController.clear();
                              _loadCatalog();
                            },
                    ),
                  )
                else
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
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
                  child: _ExpertHelpCard(
                    onTap: () => _openMemberFeature(const ServiceListScreen()),
                  ),
                ),
                const SliverToBoxAdapter(child: _TrustStrip()),
              ],
            ),
          );
        },
      ),
      bottomNavigationBar: widget.guestMode
          ? NavigationBar(
              selectedIndex: 0,
              onDestinationSelected: _handleGuestNavigation,
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.storefront_outlined),
                  selectedIcon: Icon(Icons.storefront),
                  label: 'Shop',
                ),
                NavigationDestination(
                  icon: Icon(Icons.home_repair_service_outlined),
                  selectedIcon: Icon(Icons.home_repair_service),
                  label: 'Services',
                ),
                NavigationDestination(
                  icon: Icon(Icons.info_outline),
                  selectedIcon: Icon(Icons.info),
                  label: 'About',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline),
                  selectedIcon: Icon(Icons.person),
                  label: 'Account',
                ),
              ],
            )
          : null,
    );
  }
}

class _FullScreenGallery extends StatefulWidget {
  const _FullScreenGallery({required this.images, required this.initialIndex});
  final List<String> images;
  final int initialIndex;

  @override
  State<_FullScreenGallery> createState() => _FullScreenGalleryState();
}

class _FullScreenGalleryState extends State<_FullScreenGallery> {
  late final TransformationController _transformController;
  late int _index;
  bool _zoomed = false;

  @override
  void initState() {
    super.initState();
    _index = widget.initialIndex;
    _transformController = TransformationController();
  }

  @override
  void dispose() {
    _transformController.dispose();
    super.dispose();
  }

  void _showImage(int index) {
    if (index < 0 || index >= widget.images.length) return;
    _transformController.value = Matrix4.identity();
    setState(() {
      _index = index;
      _zoomed = false;
    });
  }

  void _toggleZoom() {
    _transformController.value = _zoomed
        ? Matrix4.identity()
        : Matrix4.diagonal3Values(2.5, 2.5, 1);
    setState(() => _zoomed = !_zoomed);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: Colors.black,
    appBar: AppBar(
      backgroundColor: Colors.black,
      foregroundColor: Colors.white,
      title: Text('${_index + 1} / ${widget.images.length}'),
    ),
    body: Stack(
      children: [
        Positioned.fill(
          child: GestureDetector(
            onDoubleTap: _toggleZoom,
            child: InteractiveViewer(
              transformationController: _transformController,
              minScale: 1,
              maxScale: 4,
              panEnabled: true,
              scaleEnabled: true,
              boundaryMargin: const EdgeInsets.all(120),
              onInteractionEnd: (_) {
                final zoomed =
                    _transformController.value.getMaxScaleOnAxis() > 1.05;
                if (zoomed != _zoomed) setState(() => _zoomed = zoomed);
              },
              child: SizedBox.expand(
                child: Image.network(
                  widget.images[_index],
                  fit: BoxFit.contain,
                  errorBuilder: (_, _, _) => const Icon(
                    Icons.broken_image_outlined,
                    color: Colors.white54,
                    size: 72,
                  ),
                ),
              ),
            ),
          ),
        ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 28,
          child: Column(
            children: [
              const Text(
                'Pinch or double-tap to zoom',
                style: TextStyle(color: Colors.white70),
              ),
              if (widget.images.length > 1) ...[
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton.filled(
                      onPressed: _index > 0
                          ? () => _showImage(_index - 1)
                          : null,
                      icon: const Icon(Icons.chevron_left),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 18),
                      child: Text(
                        '${_index + 1} / ${widget.images.length}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    IconButton.filled(
                      onPressed: _index < widget.images.length - 1
                          ? () => _showImage(_index + 1)
                          : null,
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ],
    ),
  );
}

class _CustomerEngagementSection extends StatelessWidget {
  const _CustomerEngagementSection({
    required this.data,
    required this.onAction,
    required this.onPayment,
  });

  final CustomerEngagementData data;
  final ValueChanged<Map<String, dynamic>> onAction;
  final VoidCallback onPayment;

  IconData _icon(String kind) => switch (kind) {
    'OFFER' => Icons.local_offer_outlined,
    'PAYMENT' => Icons.account_balance_wallet_outlined,
    'SERVICE' => Icons.home_repair_service_outlined,
    _ => Icons.campaign_outlined,
  };

  @override
  Widget build(BuildContext context) {
    if (data.paymentAlert == null && data.items.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'For you',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: const Color(0xFF07315E),
                ),
              ),
              const Spacer(),
              if (data.unreadCount > 0)
                Text(
                  '${data.unreadCount} new',
                  style: const TextStyle(
                    color: Color(0xFF0868D7),
                    fontWeight: FontWeight.w800,
                    fontSize: 12,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 11),
          if (data.paymentAlert case final alert?)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF7E6),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFF5D89A)),
              ),
              child: Row(
                children: [
                  const CircleAvatar(
                    backgroundColor: Color(0xFFFFE7B0),
                    child: Icon(
                      Icons.notifications_active_outlined,
                      color: Color(0xFF9A6200),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          alert['title']?.toString() ?? 'Payment due',
                          style: const TextStyle(
                            fontWeight: FontWeight.w900,
                            color: Color(0xFF6D4700),
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          alert['message']?.toString() ?? '',
                          style: const TextStyle(
                            fontSize: 11.5,
                            color: Color(0xFF795F2B),
                          ),
                        ),
                      ],
                    ),
                  ),
                  TextButton(onPressed: onPayment, child: const Text('VIEW')),
                ],
              ),
            ),
          ...data.items.map((item) {
            final code = item['promo_code']?.toString() ?? '';
            final badge = item['badge']?.toString() ?? '';
            final expiry = item['valid_until']?.toString();
            final actionLabel = item['action_label']?.toString() ?? '';
            return InkWell(
              onTap: () => onAction(item),
              borderRadius: BorderRadius.circular(18),
              child: Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: const EdgeInsets.all(15),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFEDF7FF), Color(0xFFF8FBFF)],
                  ),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFD4E8F8)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(13),
                      ),
                      child: Icon(
                        _icon(item['kind']?.toString() ?? ''),
                        color: const Color(0xFF0868D7),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (badge.isNotEmpty)
                            Text(
                              badge,
                              style: const TextStyle(
                                color: Color(0xFF087B51),
                                fontSize: 10,
                                fontWeight: FontWeight.w900,
                                letterSpacing: .5,
                              ),
                            ),
                          Text(
                            item['title']?.toString() ?? '',
                            style: const TextStyle(
                              color: Color(0xFF07315E),
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            item['message']?.toString() ?? '',
                            style: const TextStyle(
                              color: Color(0xFF52677E),
                              fontSize: 11.5,
                              height: 1.3,
                            ),
                          ),
                          if (code.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text(
                              'CODE  $code',
                              style: const TextStyle(
                                color: Color(0xFF0868D7),
                                fontWeight: FontWeight.w900,
                                letterSpacing: .8,
                              ),
                            ),
                          ],
                          if (expiry != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                'Valid until ${expiry.length >= 10 ? expiry.substring(0, 10) : expiry}',
                                style: const TextStyle(
                                  color: Colors.black45,
                                  fontSize: 10,
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    if (actionLabel.isNotEmpty)
                      const Padding(
                        padding: EdgeInsets.only(top: 6),
                        child: Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 15,
                          color: Color(0xFF0868D7),
                        ),
                      ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _ServiceShortcuts extends StatelessWidget {
  const _ServiceShortcuts({
    required this.onService,
    required this.onAmc,
    required this.onRent,
    required this.onParts,
  });
  final VoidCallback onService;
  final VoidCallback onAmc;
  final VoidCallback onRent;
  final VoidCallback onParts;

  @override
  Widget build(BuildContext context) {
    final items = [
      (Icons.build_circle_outlined, 'Book Service', onService),
      (Icons.verified_outlined, 'AMC Plans', onAmc),
      (Icons.currency_rupee_rounded, 'RO on Rent', onRent),
      (Icons.settings_outlined, 'Spare Parts', onParts),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'How can we help?',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w800,
              color: const Color(0xFF07315E),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: items
                .map(
                  (item) => Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 3),
                      child: InkWell(
                        onTap: item.$3,
                        borderRadius: BorderRadius.circular(14),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            vertical: 12,
                            horizontal: 4,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0xFFE4EBF3)),
                          ),
                          child: Column(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(11),
                                decoration: BoxDecoration(
                                  color: const Color(0xFFE9F5FF),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: Icon(
                                  item.$1,
                                  color: const Color(0xFF0868D7),
                                ),
                              ),
                              const SizedBox(height: 7),
                              Text(
                                item.$2,
                                textAlign: TextAlign.center,
                                maxLines: 2,
                                style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
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

class _TrustStrip extends StatelessWidget {
  const _TrustStrip();

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.fromLTRB(16, 4, 16, 28),
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 16),
    decoration: BoxDecoration(
      color: const Color(0xFF07315E),
      borderRadius: BorderRadius.circular(18),
    ),
    child: const Row(
      children: [
        Expanded(
          child: _TrustItem(
            icon: Icons.qr_code_scanner,
            label: 'QR verified\nparts',
          ),
        ),
        SizedBox(height: 38, child: VerticalDivider(color: Colors.white24)),
        Expanded(
          child: _TrustItem(
            icon: Icons.engineering_outlined,
            label: 'Tracked\nservice',
          ),
        ),
        SizedBox(height: 38, child: VerticalDivider(color: Colors.white24)),
        Expanded(
          child: _TrustItem(
            icon: Icons.history_rounded,
            label: 'Digital\nhistory',
          ),
        ),
      ],
    ),
  );
}

class _TrustItem extends StatelessWidget {
  const _TrustItem({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Icon(icon, color: const Color(0xFF4DDCFF), size: 22),
      const SizedBox(height: 6),
      Text(
        label,
        textAlign: TextAlign.center,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 10,
          height: 1.25,
          fontWeight: FontWeight.w700,
        ),
      ),
    ],
  );
}

class _Hero extends StatelessWidget {
  const _Hero({required this.onShopNow, this.imageUrl});
  final VoidCallback onShopNow;
  final String? imageUrl;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
    padding: const EdgeInsets.fromLTRB(20, 22, 14, 20),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        colors: [Color(0xFF07315E), Color(0xFF078AD8)],
      ),
      borderRadius: BorderRadius.circular(22),
      boxShadow: const [
        BoxShadow(
          color: Color(0x2607315E),
          blurRadius: 18,
          offset: Offset(0, 8),
        ),
      ],
    ),
    child: Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: .13),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Text(
                  'COMPLETE WATER CARE',
                  style: TextStyle(
                    color: Color(0xFFBDEEFF),
                    fontSize: 9,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'PURE WATER.\nSMARTER SERVICE.',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 21,
                  height: 1.12,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -.2,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Explore reliable RO solutions for every home and business.',
                style: TextStyle(color: Colors.white70, height: 1.35),
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: onShopNow,
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: const Color(0xFF07315E),
                ),
                icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                label: const Text('EXPLORE RO'),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),
        Container(
          width: 108,
          height: 142,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: .12),
            borderRadius: BorderRadius.circular(24),
          ),
          child: imageUrl == null
              ? const Icon(
                  Icons.water_drop_rounded,
                  size: 76,
                  color: Color(0xAAFFFFFF),
                )
              : ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: Image.network(
                    imageUrl!,
                    fit: BoxFit.contain,
                    errorBuilder: (_, _, _) => const Icon(
                      Icons.water_drop_rounded,
                      size: 76,
                      color: Color(0xAAFFFFFF),
                    ),
                  ),
                ),
        ),
      ],
    ),
  );
}

class _AssuranceStrip extends StatelessWidget {
  const _AssuranceStrip();

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
    padding: const EdgeInsets.symmetric(vertical: 12),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      border: Border.all(color: const Color(0xFFE4EBF3)),
    ),
    child: const Row(
      children: [
        Expanded(
          child: _AssuranceItem(
            icon: Icons.verified_user_outlined,
            label: 'Verified\nproducts',
          ),
        ),
        SizedBox(height: 34, child: VerticalDivider(color: Color(0xFFE1E7EF))),
        Expanded(
          child: _AssuranceItem(
            icon: Icons.engineering_outlined,
            label: 'Expert\ninstallation',
          ),
        ),
        SizedBox(height: 34, child: VerticalDivider(color: Color(0xFFE1E7EF))),
        Expanded(
          child: _AssuranceItem(
            icon: Icons.support_agent_rounded,
            label: 'Service\nsupport',
          ),
        ),
      ],
    ),
  );
}

class _AssuranceItem extends StatelessWidget {
  const _AssuranceItem({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      Icon(icon, size: 21, color: const Color(0xFF0868D7)),
      const SizedBox(width: 6),
      Text(
        label,
        style: const TextStyle(
          fontSize: 10.5,
          height: 1.2,
          fontWeight: FontWeight.w700,
          color: Color(0xFF30445C),
        ),
      ),
    ],
  );
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({required this.product, required this.onTap});
  final ShopProduct product;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final discount = product.mrp > product.sellingPrice && product.mrp > 0
        ? ((product.mrp - product.sellingPrice) / product.mrp * 100).round()
        : 0;
    return Material(
      color: Colors.white,
      elevation: 1,
      shadowColor: const Color(0x1807315E),
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Stack(
                  children: [
                    Center(
                      child: _ProductVisual(
                        size: 110,
                        imageUrl: product.imageUrls.isEmpty
                            ? null
                            : product.imageUrls.first,
                      ),
                    ),
                    if (discount > 0)
                      Positioned(
                        top: 0,
                        left: 0,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFFDCFCE7),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            '$discount% OFF',
                            style: const TextStyle(
                              fontSize: 9,
                              color: Color(0xFF16753D),
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Text(
                product.categoryName.toUpperCase(),
                maxLines: 1,
                style: const TextStyle(
                  fontSize: 10,
                  color: Color(0xFF0868D7),
                  fontWeight: FontWeight.w800,
                  letterSpacing: .5,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                product.modelName,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  height: 1.15,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                '${product.capacity} • ${product.warrantyMonths}M warranty',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, color: Colors.black54),
              ),
              const SizedBox(height: 8),
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '₹${product.sellingPrice.toStringAsFixed(0)}',
                    style: const TextStyle(
                      fontSize: 17,
                      color: Color(0xFF07315E),
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  if (product.mrp > product.sellingPrice) ...[
                    const SizedBox(width: 5),
                    Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Text(
                        '₹${product.mrp.toStringAsFixed(0)}',
                        style: const TextStyle(
                          fontSize: 10,
                          color: Colors.black38,
                          decoration: TextDecoration.lineThrough,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 5),
              Text(
                product.stockQuantity > 0 ? 'IN STOCK' : 'UNAVAILABLE',
                style: TextStyle(
                  fontSize: 9,
                  letterSpacing: .5,
                  fontWeight: FontWeight.w900,
                  color: product.stockQuantity > 0
                      ? const Color(0xFF16834A)
                      : Colors.red.shade700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExpertHelpCard extends StatelessWidget {
  const _ExpertHelpCard({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.fromLTRB(16, 2, 16, 18),
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: const Color(0xFFEAF5FF),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: const Color(0xFFCDE6FA)),
    ),
    child: Row(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: const BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.support_agent_rounded,
            color: Color(0xFF0868D7),
            size: 28,
          ),
        ),
        const SizedBox(width: 13),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Not sure which RO is right?',
                style: TextStyle(
                  color: Color(0xFF07315E),
                  fontWeight: FontWeight.w900,
                  fontSize: 15,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Get help based on your water and family needs.',
                style: TextStyle(
                  color: Color(0xFF52677E),
                  fontSize: 11.5,
                  height: 1.3,
                ),
              ),
            ],
          ),
        ),
        IconButton.filled(
          onPressed: onTap,
          icon: const Icon(Icons.arrow_forward_rounded),
          style: IconButton.styleFrom(backgroundColor: const Color(0xFF0868D7)),
        ),
      ],
    ),
  );
}

class _ProductVisual extends StatelessWidget {
  const _ProductVisual({required this.size, this.imageUrl});
  final double size;
  final String? imageUrl;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      color: const Color(0xFFE9F5FF),
      borderRadius: BorderRadius.circular(22),
    ),
    child: imageUrl == null
        ? Icon(
            Icons.water_drop_rounded,
            size: size * .52,
            color: const Color(0xFF078AD8),
          )
        : ClipRRect(
            borderRadius: BorderRadius.circular(22),
            child: Image.network(
              imageUrl!,
              fit: BoxFit.contain,
              errorBuilder: (_, _, _) => Icon(
                Icons.water_drop_rounded,
                size: size * .52,
                color: const Color(0xFF078AD8),
              ),
            ),
          ),
  );
}

class _StoreMessage extends StatelessWidget {
  const _StoreMessage({
    required this.icon,
    required this.title,
    required this.message,
    required this.button,
    required this.onPressed,
  });
  final IconData icon;
  final String title;
  final String message;
  final String button;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: const BoxDecoration(
              color: Color(0xFFE9F5FF),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 42, color: const Color(0xFF078AD8)),
          ),
          const SizedBox(height: 18),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 18),
          OutlinedButton(onPressed: onPressed, child: Text(button)),
        ],
      ),
    ),
  );
}
