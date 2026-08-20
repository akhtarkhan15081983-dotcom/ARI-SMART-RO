import 'package:flutter/material.dart';
import '../../services/andy_service.dart';

class AndyChatScreen extends StatefulWidget {
  const AndyChatScreen({super.key});
  @override
  State<AndyChatScreen> createState() => _AndyChatScreenState();
}

class _ChatItem {
  final bool user;
  final String text;
  final int? messageId;
  const _ChatItem(this.user, this.text, {this.messageId});
}

class _AndyChatScreenState extends State<AndyChatScreen> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  final _service = AndyService();
  final List<_ChatItem> _messages = [
    const _ChatItem(false, 'Namaste. Main ANDY hoon — ARI SMART RO ka private, self-hosted AI assistant. Aap mujhse project, customers, jobs aur programming ke baare mein pooch sakte hain.'),
  ];
  int? _conversationId;
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _sending) return;
    _controller.clear();
    setState(() { _messages.add(_ChatItem(true, text)); _sending = true; });
    _jumpBottom();
    try {
      final reply = await _service.chat(text, conversationId: _conversationId);
      if (!mounted) return;
      setState(() {
        _conversationId = reply.conversationId;
        _messages.add(_ChatItem(false, reply.answer, messageId: reply.messageId));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _messages.add(_ChatItem(false, 'ANDY local model se connect nahi ho pa raha. Local model server check karein.\n$e')));
    } finally {
      if (mounted) setState(() => _sending = false);
      _jumpBottom();
    }
  }

  void _jumpBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.animateTo(_scroll.position.maxScrollExtent, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    });
  }

  Future<void> _rate(int messageId, int rating) async {
    try {
      await _service.feedback(messageId, rating);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Feedback saved. ANDY can learn from reviewed feedback.')));
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not save feedback.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ANDY • Private AI')),
      body: Column(children: [
        Expanded(child: ListView.builder(
          controller: _scroll,
          padding: const EdgeInsets.all(12),
          itemCount: _messages.length,
          itemBuilder: (_, index) {
            final item = _messages[index];
            return Align(
              alignment: item.user ? Alignment.centerRight : Alignment.centerLeft,
              child: Container(
                constraints: const BoxConstraints(maxWidth: 520),
                margin: const EdgeInsets.symmetric(vertical: 5),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: item.user ? Theme.of(context).colorScheme.primaryContainer : Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(item.text),
                  if (!item.user && item.messageId != null) ...[
                    const SizedBox(height: 6),
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      IconButton(icon: const Icon(Icons.thumb_up_alt_outlined, size: 18), tooltip: 'Helpful', onPressed: () => _rate(item.messageId!, 2)),
                      IconButton(icon: const Icon(Icons.thumb_down_alt_outlined, size: 18), tooltip: 'Needs improvement', onPressed: () => _rate(item.messageId!, 1)),
                    ]),
                  ],
                ]),
              ),
            );
          },
        )),
        if (_sending) const LinearProgressIndicator(),
        SafeArea(top: false, child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
          child: Row(children: [
            Expanded(child: TextField(controller: _controller, minLines: 1, maxLines: 5, textInputAction: TextInputAction.newline, decoration: const InputDecoration(hintText: 'Ask ANDY...', border: OutlineInputBorder()))),
            const SizedBox(width: 8),
            IconButton.filled(onPressed: _sending ? null : _send, icon: const Icon(Icons.send)),
          ]),
        )),
      ]),
    );
  }
}
