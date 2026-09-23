import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../services/inventory_workflow_service.dart';
import '../../utils/search_utils.dart';

class RoStockWorkflowScreen extends StatefulWidget {
  const RoStockWorkflowScreen({super.key});
  @override
  State<RoStockWorkflowScreen> createState() => _RoStockWorkflowScreenState();
}

class _RoStockWorkflowScreenState extends State<RoStockWorkflowScreen> {
  final _service = InventoryWorkflowService();
  final _searchController = TextEditingController();
  List<Map<String, dynamic>> _assets = const [], _models = const [], _customers = const [];
  Map<String, dynamic> _summary = const {}, _audit = const {};
  bool _loading = true, _busy = false;
  String? _error;
  String _query = '', _status = 'ALL';

  @override
  void initState() { super.initState(); _load(); }
  @override
  void dispose() { _searchController.dispose(); super.dispose(); }

  String _clean(Object e) => e.toString().replaceFirst('Exception: ', '');
  void _show(String text) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text))); }
  String _date(DateTime v) => '${v.year}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    if (mounted) setState(() { _loading = true; _error = null; });
    try {
      final v = await Future.wait([
        _service.roAssets(), _service.roModels(), _service.customers(),
        _service.roSummary(), _service.getRoStockAudit(),
      ]);
      if (!mounted) return;
      setState(() {
        _assets = v[0] as List<Map<String, dynamic>>;
        _models = v[1] as List<Map<String, dynamic>>;
        _customers = v[2] as List<Map<String, dynamic>>;
        _summary = v[3] as Map<String, dynamic>;
        _audit = v[4] as Map<String, dynamic>;
      });
    } catch (e) {
      if (mounted) setState(() => _error = _clean(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    if (_busy) return;
    setState(() => _busy = true);
    try { await action(); _show(success); await _load(); }
    catch (e) { _show(_clean(e)); }
    finally { if (mounted) setState(() => _busy = false); }
  }

  List<Map<String, dynamic>> get _visible => _assets.where((r) {
    if (_status != 'ALL' && r['status']?.toString() != _status) return false;
    return matchesAllSearchTerms(_query, [
      r['asset_id']?.toString() ?? '', r['serial_number']?.toString() ?? '',
      r['ro_model_name']?.toString() ?? '', r['customer_name']?.toString() ?? '',
      r['reserved_customer_name']?.toString() ?? '', r['deployment_type']?.toString() ?? '',
      r['status']?.toString() ?? '', r['qc_status']?.toString() ?? '',
    ]);
  }).toList();

  Future<void> _receiveStock() async {
    if (_models.isEmpty) { _show('Add an RO model first.'); return; }
    int? modelId = (_models.first['id'] as num?)?.toInt();
    final serials = TextEditingController(), invoice = TextEditingController(), price = TextEditingController(text: '0');
    var purchaseDate = DateTime.now();
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(builder: (_, setD) => AlertDialog(
      title: const Text('Receive complete RO stock'),
      content: SizedBox(width: 560, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        DropdownButtonFormField<int>(initialValue: modelId, isExpanded: true, decoration: const InputDecoration(labelText: 'RO model *'),
          items: _models.map((m) => DropdownMenuItem<int>(value: (m['id'] as num).toInt(), child: Text(m['model_name']?.toString() ?? 'RO'))).toList(), onChanged: (v) => modelId = v),
        TextField(controller: invoice, decoration: const InputDecoration(labelText: 'Purchase invoice')),
        TextField(controller: price, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Purchase price per RO')),
        ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.calendar_month_outlined), title: const Text('Purchase date'), subtitle: Text(_date(purchaseDate)), onTap: () async {
          final p = await showDatePicker(context: c, firstDate: DateTime(2020), lastDate: DateTime.now(), initialDate: purchaseDate);
          if (p != null) setD(() => purchaseDate = p);
        }),
        TextField(controller: serials, minLines: 6, maxLines: 12, decoration: const InputDecoration(labelText: 'RO serial numbers *', hintText: 'One serial per line\nARI50-001\nARI50-002', helperText: '50 RO aaye hain to 50 serial numbers ek saath paste karein.')),
        const SizedBox(height: 8), const Text('Each unit gets a Digital RO Passport and starts as QC Pending.'),
      ]))),
      actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('CANCEL')), FilledButton.icon(onPressed: () => Navigator.pop(c, true), icon: const Icon(Icons.inventory_2_outlined), label: const Text('RECEIVE STOCK'))],
    ))) ?? false;
    final list = serials.text.replaceAll(',', '\n').split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toSet().toList();
    final p = double.tryParse(price.text.trim());
    if (ok && modelId != null && list.isNotEmpty && p != null) {
      await _run(() async { await _service.receiveRoStock(roModelId: modelId!, serialNumbers: list, purchaseInvoice: invoice.text.trim(), purchaseDate: _date(purchaseDate), purchasePrice: p); }, '${list.length} RO unit(s) received. Complete QC before sale/rent.');
    }
    serials.dispose(); invoice.dispose(); price.dispose();
  }

  String _qcLabel(String k) => const {
    'pump_run':'Pump running test passed', 'leakage_test':'Leakage test passed',
    'smps':'SMPS/electrical test passed', 'membrane':'Membrane/flow test passed',
    'body_damage':'Body/physical condition passed',
  }[k] ?? k;

  Future<void> _qc(Map<String, dynamic> asset) async {
    final checks = <String,bool>{'pump_run':false,'leakage_test':false,'smps':false,'membrane':false,'body_damage':false};
    var passed = true, cleaned = asset['status'] == 'RETURNED', sanitized = asset['status'] == 'RETURNED';
    final notes = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(builder: (_, setD) => AlertDialog(
      title: Text('QC • ${asset['asset_id']}'),
      content: SizedBox(width: 520, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        DropdownButtonFormField<bool>(initialValue: passed, decoration: const InputDecoration(labelText: 'QC Result'), items: const [DropdownMenuItem(value:true,child:Text('PASS')),DropdownMenuItem(value:false,child:Text('FAIL'))], onChanged:(v)=>setD(()=>passed=v??true)),
        if (passed) ...checks.keys.map((k) => CheckboxListTile(contentPadding: EdgeInsets.zero, value: checks[k], title: Text(_qcLabel(k)), onChanged:(v)=>setD(()=>checks[k]=v??false))),
        if (asset['status']=='RETURNED') ...[
          CheckboxListTile(contentPadding: EdgeInsets.zero, value: cleaned, title: const Text('Cleaning completed'), onChanged:(v)=>setD(()=>cleaned=v??false)),
          CheckboxListTile(contentPadding: EdgeInsets.zero, value: sanitized, title: const Text('Sanitization completed'), onChanged:(v)=>setD(()=>sanitized=v??false)),
        ],
        TextField(controller: notes, maxLines: 2, decoration: const InputDecoration(labelText:'QC notes')),
      ]))),
      actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('CANCEL')),FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('SAVE QC'))],
    ))) ?? false;
    if (ok) await _run(() => _service.qcRo(assetId:(asset['id'] as num).toInt(),passed:passed,checklist:checks,notes:notes.text.trim(),cleaned:cleaned,sanitized:sanitized), passed ? 'QC passed. BOM verification still applies.' : 'QC failed. RO remains blocked.');
    notes.dispose();
  }

  Future<int?> _chooseCustomer(String title) async {
    if (_customers.isEmpty) { _show('No active customer found.'); return null; }
    int? selected = (_customers.first['id'] as num?)?.toInt();
    final ok = await showDialog<bool>(context: context, builder:(c)=>StatefulBuilder(builder:(_,setD)=>AlertDialog(
      title:Text(title), content:DropdownButtonFormField<int>(initialValue:selected,isExpanded:true,items:_customers.map((x)=>DropdownMenuItem<int>(value:(x['id'] as num).toInt(),child:Text('${x['name'] ?? 'Customer'} • ${x['phone'] ?? ''}'))).toList(),onChanged:(v)=>selected=v),
      actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('CANCEL')),FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('CONFIRM'))],
    ))) ?? false;
    return ok ? selected : null;
  }

  Future<void> _reserve(Map<String,dynamic> a) async { final c=await _chooseCustomer('Reserve RO for customer'); if(c!=null) await _run(()=>_service.reserveRo(assetId:(a['id'] as num).toInt(),customerId:c),'RO reserved for 24 hours.'); }
  Future<void> _releaseReservation(Map<String,dynamic> a) => _run(()=>_service.releaseRoReservation((a['id'] as num).toInt()),'RO reservation released.');
  Future<void> _allocate(Map<String,dynamic> a,String type) async { final c=await _chooseCustomer(type=='SALE'?'Sell this RO':'Give this RO on rent'); if(c!=null) await _run(()=>_service.allocateRo(assetId:(a['id'] as num).toInt(),customerId:c,deploymentType:type),type=='SALE'?'RO allocated for customer sale.':'RO allocated on rent.'); }
  Future<void> _returnRental(Map<String,dynamic> a) => _run(()=>_service.returnRentalRo((a['id'] as num).toInt()),'Rental RO returned. Complete QC + cleaning + sanitization.');
  Future<void> _restock(Map<String,dynamic> a) => _run(()=>_service.restockRo((a['id'] as num).toInt(),remarks:'Return QC passed; cleaned and sanitized.'),'RO returned to available warehouse stock.');

  Future<String?> _scan(String title) => Navigator.push<String>(context,MaterialPageRoute(builder:(_)=>_RoCodeScanner(title:title)));

  Future<void> _stockAudit() async {
    Map<String,dynamic> audit = _audit;
    if (audit.isEmpty || audit['status']!='OPEN') {
      final yes = await showDialog<bool>(context: context,builder:(c)=>AlertDialog(title:const Text('Start physical RO stock audit?'),content:const Text('Snapshot warehouse stock and scan every physical RO QR/serial.'),actions:[TextButton(onPressed:()=>Navigator.pop(c,false),child:const Text('CANCEL')),FilledButton(onPressed:()=>Navigator.pop(c,true),child:const Text('START AUDIT'))])) ?? false;
      if(!yes)return;
      try { audit=await _service.startRoStockAudit(notes:'Physical warehouse reconciliation'); await _load(); } catch(e){_show(_clean(e));return;}
    }
    final raw=audit['audit_id']??audit['id']; final id=raw is num?raw.toInt():int.tryParse(raw?.toString()??'');
    if(id==null){_show('Unable to resolve active audit.');return;}
    if(!mounted)return;
    await showModalBottomSheet<void>(context:context,isScrollControlled:true,builder:(sheet)=>Padding(padding:const EdgeInsets.all(20),child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[
      Text('Stock Audit ${audit['reference'] ?? ''}',style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900)),
      const SizedBox(height:6),Text('Expected ${audit['expected'] ?? _audit['expected'] ?? '—'} • Found ${_audit['found'] ?? 0} • Missing ${_audit['missing'] ?? '—'}'),const SizedBox(height:14),
      FilledButton.icon(onPressed:()async{final code=await _scan('Scan physical RO');if(code==null)return;try{await _service.scanRoStockAudit(auditId:id,code:code);_show('RO verified in physical stock.');await _load();}catch(e){_show(_clean(e));}},icon:const Icon(Icons.qr_code_scanner_rounded),label:const Text('SCAN NEXT RO')),
      const SizedBox(height:8),OutlinedButton.icon(onPressed:()async{try{final r=await _service.completeRoStockAudit(id);if(!mounted)return;Navigator.pop(sheet);_show('Audit completed • Missing ${r['missing_count'] ?? 0} RO unit(s).');await _load();}catch(e){_show(_clean(e));}},icon:const Icon(Icons.fact_check_outlined),label:const Text('COMPLETE AUDIT')),
    ])));
  }

  Widget _sum(String title,String key,IconData icon)=>Card(child:Padding(padding:const EdgeInsets.all(12),child:Row(children:[Icon(icon),const SizedBox(width:8),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,mainAxisAlignment:MainAxisAlignment.center,children:[Text('${_summary[key] ?? 0}',style:const TextStyle(fontSize:21,fontWeight:FontWeight.w900)),Text(title,maxLines:1)]))])));
  Widget _chip(String text,IconData icon)=>Chip(avatar:Icon(icon,size:16),label:Text(text));

  Widget _assetCard(Map<String,dynamic> a) {
    final status=(a['status']??'').toString(), deployment=(a['deployment_type']??'').toString(), qc=(a['qc_status']??'PENDING').toString();
    final ready=a['release_ready']==true,bom=a['bom_verified']==true,reserved=a['reservation_active']==true;
    final s=Map<String,dynamic>.from(a['component_summary'] as Map? ?? const {});
    return Card(child:Padding(padding:const EdgeInsets.all(14),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Row(children:[CircleAvatar(child:Icon(ready?Icons.verified_rounded:Icons.water_drop_outlined)),const SizedBox(width:10),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(a['ro_model_name']?.toString()??'RO',style:const TextStyle(fontWeight:FontWeight.w900,fontSize:17)),Text('${a['asset_id']} • ${a['serial_number']}'),Text('$status${deployment.isEmpty?'':' • $deployment'}')])),Chip(label:Text(ready?'READY':qc))]),
      const SizedBox(height:8),Wrap(spacing:7,runSpacing:7,children:[_chip('QC $qc',qc=='PASSED'?Icons.check_circle_outline:Icons.science_outlined),_chip(bom?'BOM verified':'BOM pending',Icons.schema_outlined),_chip('Scan pending ${s['scan_pending'] ?? 0}',Icons.qr_code_scanner_rounded),if(reserved)_chip('Reserved • ${a['reserved_customer_name'] ?? ''}',Icons.lock_clock_outlined)]),
      if((a['customer_name']??'').toString().isNotEmpty)Padding(padding:const EdgeInsets.only(top:8),child:Text('Customer: ${a['customer_name']}',style:const TextStyle(fontWeight:FontWeight.w700))),
      const SizedBox(height:8),Wrap(spacing:8,runSpacing:8,children:[
        if(status=='WAREHOUSE'&&qc!='PASSED')OutlinedButton.icon(onPressed:_busy?null:()=>_qc(a),icon:const Icon(Icons.science_outlined),label:const Text('QC')),
        if(status=='RETURNED')OutlinedButton.icon(onPressed:_busy?null:()=>_qc(a),icon:const Icon(Icons.cleaning_services_outlined),label:const Text('RETURN QC')),
        if(status=='WAREHOUSE'&&ready&&!reserved)OutlinedButton.icon(onPressed:_busy?null:()=>_reserve(a),icon:const Icon(Icons.lock_clock_outlined),label:const Text('RESERVE')),
        if(status=='WAREHOUSE'&&reserved)OutlinedButton.icon(onPressed:_busy?null:()=>_releaseReservation(a),icon:const Icon(Icons.lock_open_outlined),label:const Text('RELEASE')),
        if(status=='WAREHOUSE'&&qc=='PASSED'&&bom)FilledButton.tonal(onPressed:_busy?null:()=>_allocate(a,'SALE'),child:const Text('SELL')),
        if(status=='WAREHOUSE'&&qc=='PASSED'&&bom)FilledButton(onPressed:_busy?null:()=>_allocate(a,'RENT'),child:const Text('RENT')),
        if(deployment=='RENT'&&{'ASSIGNED','INSTALLED','SERVICE','REPAIR'}.contains(status))OutlinedButton.icon(onPressed:_busy?null:()=>_returnRental(a),icon:const Icon(Icons.keyboard_return_outlined),label:const Text('RETURN')),
        if(status=='RETURNED'&&qc=='PASSED'&&a['cleaned_at']!=null&&a['sanitized_at']!=null&&bom)FilledButton.icon(onPressed:_busy?null:()=>_restock(a),icon:const Icon(Icons.warehouse_outlined),label:const Text('RESTOCK')),
      ])
    ])));
  }

  @override
  Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('RO Stock • Sale • Rent'),actions:[IconButton(tooltip:'Physical Stock Audit',onPressed:_busy?null:_stockAudit,icon:const Icon(Icons.fact_check_outlined)),IconButton(onPressed:_load,icon:const Icon(Icons.refresh_rounded))]),
    floatingActionButton:FloatingActionButton.extended(onPressed:_busy?null:_receiveStock,icon:const Icon(Icons.add_box_outlined),label:const Text('RECEIVE RO')),
    body:_loading?const Center(child:CircularProgressIndicator()):_error!=null?Center(child:Padding(padding:const EdgeInsets.all(24),child:Column(mainAxisSize:MainAxisSize.min,children:[Text(_error!,textAlign:TextAlign.center),const SizedBox(height:12),FilledButton(onPressed:_load,child:const Text('RETRY'))])):RefreshIndicator(onRefresh:_load,child:ListView(padding:const EdgeInsets.fromLTRB(16,16,16,96),children:[
      const Text('Complete RO Inventory',style:TextStyle(fontSize:22,fontWeight:FontWeight.w900)),const SizedBox(height:4),Text('Physical serial → QC → BOM verification → reservation → Sale/Rent → Installation → Return/QC/Restock.',style:TextStyle(color:Colors.blueGrey.shade700)),const SizedBox(height:14),
      GridView.count(shrinkWrap:true,physics:const NeverScrollableScrollPhysics(),crossAxisCount:2,childAspectRatio:2.15,mainAxisSpacing:8,crossAxisSpacing:8,children:[_sum('Release Ready','release_ready',Icons.verified_outlined),_sum('QC Pending','qc_pending',Icons.science_outlined),_sum('BOM Pending','bom_pending',Icons.schema_outlined),_sum('Installed','installed',Icons.home_repair_service_outlined)]),const SizedBox(height:12),
      if(_audit['status']=='OPEN')Card(child:ListTile(leading:const Icon(Icons.fact_check_outlined),title:Text('Physical Audit ${_audit['reference'] ?? ''}'),subtitle:Text('Found ${_audit['found'] ?? 0} of ${_audit['expected'] ?? 0} • Missing ${_audit['missing'] ?? 0}'),trailing:const Icon(Icons.chevron_right),onTap:_stockAudit)),
      TextField(controller:_searchController,onChanged:(v)=>setState(()=>_query=v),decoration:InputDecoration(hintText:'Search model, asset ID, serial, customer...',prefixIcon:const Icon(Icons.search),suffixIcon:_query.isEmpty?null:IconButton(onPressed:(){_searchController.clear();setState(()=>_query='');},icon:const Icon(Icons.clear)))),const SizedBox(height:10),
      DropdownButtonFormField<String>(initialValue:_status,decoration:const InputDecoration(labelText:'RO status'),items:const [DropdownMenuItem(value:'ALL',child:Text('All RO units')),DropdownMenuItem(value:'WAREHOUSE',child:Text('Warehouse')),DropdownMenuItem(value:'ASSIGNED',child:Text('Assigned')),DropdownMenuItem(value:'INSTALLED',child:Text('Installed')),DropdownMenuItem(value:'RETURNED',child:Text('Returned / QC pending')),DropdownMenuItem(value:'REPAIR',child:Text('Repair')),DropdownMenuItem(value:'SCRAP',child:Text('Scrap'))],onChanged:(v)=>setState(()=>_status=v??'ALL')),const SizedBox(height:10),
      Text('${_visible.length} of ${_assets.length} physical RO units',style:const TextStyle(fontWeight:FontWeight.w800)),const SizedBox(height:8),if(_visible.isEmpty)const Card(child:Padding(padding:EdgeInsets.all(24),child:Center(child:Text('No RO units match this filter.')))),..._visible.map(_assetCard),
    ]))
  );
}

class _RoCodeScanner extends StatefulWidget { const _RoCodeScanner({required this.title}); final String title; @override State<_RoCodeScanner> createState()=>_RoCodeScannerState(); }
class _RoCodeScannerState extends State<_RoCodeScanner> {
  final _controller=MobileScannerController(); bool _handled=false;
  @override void dispose(){_controller.dispose();super.dispose();}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:Text(widget.title)),body:Stack(children:[MobileScanner(controller:_controller,onDetect:(capture){if(_handled)return;final value=capture.barcodes.firstOrNull?.rawValue?.trim();if(value==null||value.isEmpty)return;_handled=true;Navigator.pop(context,value);}),Center(child:Container(width:250,height:250,decoration:BoxDecoration(border:Border.all(color:Colors.white,width:3),borderRadius:BorderRadius.circular(20)))),const Positioned(left:24,right:24,bottom:42,child:Card(child:Padding(padding:EdgeInsets.all(14),child:Text('Scan the permanent ARI RO QR or machine serial label.',textAlign:TextAlign.center))))]));
}
