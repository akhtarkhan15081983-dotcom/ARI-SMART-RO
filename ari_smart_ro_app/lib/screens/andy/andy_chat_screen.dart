import 'dart:io';
import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
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

enum _AndyAvatarState {
  idle,
  listening,
  thinking,
  confirming,
  speaking,
  completed,
}

class _AndyChatScreenState extends State<AndyChatScreen> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  final _service = AndyService();
  final _recorder = AudioRecorder();
  final _player = AudioPlayer();
  final List<_ChatItem> _messages = [
    const _ChatItem(
      false,
      'Namaste. Main ANDY hoon — ARI SMART RO ka private, self-hosted AI assistant. Type karein ya microphone dabakar Hindi, English ya Hinglish mein boliye.',
    ),
  ];

  int? _conversationId;
  int? _pendingActionId;
  String? _pendingActionSummary;
  bool _sending = false;
  bool _recording = false;
  bool _transcribing = false;
  bool _speaking = false;
  bool _resolvingAction = false;
  _AndyAvatarState _avatarState = _AndyAvatarState.idle;

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    _recorder.dispose();
    _player.dispose();
    super.dispose();
  }

  void _setAvatar(_AndyAvatarState state) {
    if (mounted) setState(() => _avatarState = state);
  }

  Future<String?> _sendText(String text, {bool autoSpeak = false}) async {
    text = text.trim();
    if (text.isEmpty || _sending || _resolvingAction) return null;
    _controller.clear();
    setState(() {
      _messages.add(_ChatItem(true, text));
      _sending = true;
      _avatarState = _AndyAvatarState.thinking;
    });
    _jumpBottom();
    String? answer;
    try {
      final reply = await _service.chat(text, conversationId: _conversationId);
      if (!mounted) return null;
      answer = reply.answer;
      setState(() {
        _conversationId = reply.conversationId;
        _messages.add(
          _ChatItem(false, reply.answer, messageId: reply.messageId),
        );
        if (reply.requiresConfirmation && reply.pendingActionId != null) {
          _pendingActionId = reply.pendingActionId;
          _pendingActionSummary = reply.actionSummary;
          _avatarState = _AndyAvatarState.confirming;
        } else {
          _pendingActionId = null;
          _pendingActionSummary = null;
          _avatarState = _AndyAvatarState.completed;
        }
      });
    } catch (e) {
      if (!mounted) return null;
      setState(() {
        _messages.add(
          _ChatItem(false, 'ANDY local model se connect nahi ho pa raha.\n$e'),
        );
        _avatarState = _AndyAvatarState.idle;
      });
    } finally {
      if (mounted) setState(() => _sending = false);
      _jumpBottom();
    }
    if (autoSpeak &&
        answer != null &&
        answer.isNotEmpty &&
        _pendingActionId == null) {
      await _speak(answer);
    }
    return answer;
  }

  Future<void> _send() async => _sendText(_controller.text);

  Future<void> _resolvePendingAction(bool confirm) async {
    final actionId = _pendingActionId;
    if (actionId == null || _resolvingAction) return;
    setState(() {
      _resolvingAction = true;
      _avatarState = _AndyAvatarState.thinking;
    });
    try {
      final result = await _service.confirmAction(actionId, confirm);
      if (!mounted) return;
      setState(() {
        _messages.add(_ChatItem(false, result.answer));
        _pendingActionId = null;
        _pendingActionSummary = null;
        _avatarState = _AndyAvatarState.completed;
      });
      _jumpBottom();
      if (result.answer.isNotEmpty) await _speak(result.answer);
    } catch (e) {
      if (!mounted) return;
      setState(() => _avatarState = _AndyAvatarState.confirming);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('ANDY action failed: $e')));
    } finally {
      if (mounted) setState(() => _resolvingAction = false);
    }
  }

  Future<void> _speak(String text) async {
    if (_speaking) {
      await _player.stop();
      if (mounted) {
        setState(() {
          _speaking = false;
          _avatarState = _pendingActionId != null
              ? _AndyAvatarState.confirming
              : _AndyAvatarState.completed;
        });
      }
      return;
    }
    try {
      if (mounted) {
        setState(() {
          _speaking = true;
          _avatarState = _AndyAvatarState.speaking;
        });
      }
      final bytes = await _service.speak(text);
      final directory = await getTemporaryDirectory();
      final file = File(
        '${directory.path}/andy_speech_${DateTime.now().millisecondsSinceEpoch}.wav',
      );
      await file.writeAsBytes(bytes, flush: true);
      await _player.setFilePath(file.path);
      await _player.play();
    } catch (e) {
      if (mounted)
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('ANDY voice failed: $e')));
    } finally {
      if (mounted) {
        setState(() {
          _speaking = false;
          _avatarState = _pendingActionId != null
              ? _AndyAvatarState.confirming
              : _AndyAvatarState.completed;
        });
      }
    }
  }

  Future<void> _toggleRecording() async {
    if (_sending || _transcribing || _resolvingAction) return;
    if (_recording) {
      final path = await _recorder.stop();
      if (mounted) {
        setState(() {
          _recording = false;
          _transcribing = true;
          _avatarState = _AndyAvatarState.thinking;
        });
      }
      if (path == null) {
        if (mounted) {
          setState(() {
            _transcribing = false;
            _avatarState = _AndyAvatarState.idle;
          });
        }
        return;
      }
      try {
        final transcription = await _service.transcribe(path);
        if (!mounted) return;
        setState(() => _transcribing = false);
        await _sendText(transcription.text, autoSpeak: true);
      } catch (e) {
        if (!mounted) return;
        setState(() {
          _transcribing = false;
          _avatarState = _AndyAvatarState.idle;
        });
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Voice recognition failed: $e')));
      }
      return;
    }

    if (!await _recorder.hasPermission()) {
      if (mounted)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Microphone permission is required for ANDY voice.'),
          ),
        );
      return;
    }
    final directory = await getTemporaryDirectory();
    final path =
        '${directory.path}/andy_${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 64000,
        sampleRate: 16000,
      ),
      path: path,
    );
    if (mounted) {
      setState(() {
        _recording = true;
        _avatarState = _AndyAvatarState.listening;
      });
    }
  }

  void _jumpBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<String?> _askForCorrection() async {
    final correctionController = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Teach ANDY'),
        content: TextField(
          controller: correctionController,
          autofocus: true,
          minLines: 3,
          maxLines: 7,
          maxLength: 2000,
          decoration: const InputDecoration(
            labelText: 'Sahi jawab',
            hintText: 'ANDY ko kya jawab dena chahiye tha?',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final value = correctionController.text.trim();
              if (value.length >= 5) Navigator.pop(dialogContext, value);
            },
            child: const Text('Submit for review'),
          ),
        ],
      ),
    );
    correctionController.dispose();
    return result;
  }

  Future<void> _rate(int messageId, int rating) async {
    var correction = '';
    if (rating == 1) {
      final submitted = await _askForCorrection();
      if (submitted == null || submitted.isEmpty) return;
      correction = submitted;
    }

    try {
      await _service.feedback(messageId, rating, correction: correction);
      if (!mounted) return;
      final message = rating == 1
          ? 'Correction admin review ke liye submit ho gayi.'
          : 'Feedback saved.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not save feedback.')),
        );
      }
    }
  }

  String get _stateLabel {
    switch (_avatarState) {
      case _AndyAvatarState.listening:
        return 'LISTENING';
      case _AndyAvatarState.thinking:
        return 'THINKING';
      case _AndyAvatarState.confirming:
        return 'CONFIRMING';
      case _AndyAvatarState.speaking:
        return 'SPEAKING';
      case _AndyAvatarState.completed:
        return 'READY';
      case _AndyAvatarState.idle:
        return 'ONLINE';
    }
  }

  IconData get _stateIcon {
    switch (_avatarState) {
      case _AndyAvatarState.listening:
        return Icons.hearing;
      case _AndyAvatarState.thinking:
        return Icons.psychology_alt_outlined;
      case _AndyAvatarState.confirming:
        return Icons.verified_user_outlined;
      case _AndyAvatarState.speaking:
        return Icons.graphic_eq;
      case _AndyAvatarState.completed:
        return Icons.check_circle_outline;
      case _AndyAvatarState.idle:
        return Icons.smart_toy_outlined;
    }
  }

  Widget _buildAvatarPanel(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            width: 68,
            height: 68,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: scheme.primaryContainer,
              border: Border.all(
                color: scheme.primary,
                width:
                    _avatarState == _AndyAvatarState.speaking ||
                        _avatarState == _AndyAvatarState.listening
                    ? 3
                    : 1,
              ),
            ),
            child: Icon(_stateIcon, size: 34, color: scheme.onPrimaryContainer),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'ANDY',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 2),
                const Text('ARI SMART RO • AI Assistant'),
                const SizedBox(height: 7),
                Row(
                  children: [
                    Icon(_stateIcon, size: 16, color: scheme.primary),
                    const SizedBox(width: 5),
                    Text(
                      _stateLabel,
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: scheme.primary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfirmationCard(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 6, 12, 4),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.secondaryContainer,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: scheme.secondary),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.verified_user_outlined,
                color: scheme.onSecondaryContainer,
              ),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Action confirmation required',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _pendingActionSummary?.replaceAll('_', ' ') ??
                'Please confirm this ANDY action.',
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _resolvingAction
                      ? null
                      : () => _resolvePendingAction(false),
                  icon: const Icon(Icons.close),
                  label: const Text('Cancel'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _resolvingAction
                      ? null
                      : () => _resolvePendingAction(true),
                  icon: const Icon(Icons.check),
                  label: const Text('Confirm'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final busy = _sending || _transcribing || _resolvingAction;
    return Scaffold(
      appBar: AppBar(title: const Text('ANDY • Private AI')),
      body: Column(
        children: [
          _buildAvatarPanel(context),
          Expanded(
            child: ListView.builder(
              controller: _scroll,
              padding: const EdgeInsets.all(12),
              itemCount: _messages.length,
              itemBuilder: (_, index) {
                final item = _messages[index];
                return Align(
                  alignment: item.user
                      ? Alignment.centerRight
                      : Alignment.centerLeft,
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 520),
                    margin: const EdgeInsets.symmetric(vertical: 5),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: item.user
                          ? Theme.of(context).colorScheme.primaryContainer
                          : Theme.of(
                              context,
                            ).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(item.text),
                        if (!item.user && item.messageId != null) ...[
                          const SizedBox(height: 6),
                          Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: Icon(
                                  _speaking
                                      ? Icons.stop_circle_outlined
                                      : Icons.volume_up_outlined,
                                  size: 19,
                                ),
                                tooltip: _speaking
                                    ? 'Stop ANDY voice'
                                    : 'Hear ANDY',
                                onPressed: () => _speak(item.text),
                              ),
                              IconButton(
                                icon: const Icon(
                                  Icons.thumb_up_alt_outlined,
                                  size: 18,
                                ),
                                tooltip: 'Helpful',
                                onPressed: () => _rate(item.messageId!, 2),
                              ),
                              IconButton(
                                icon: const Icon(
                                  Icons.thumb_down_alt_outlined,
                                  size: 18,
                                ),
                                tooltip: 'Needs improvement',
                                onPressed: () => _rate(item.messageId!, 1),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          if (_pendingActionId != null) _buildConfirmationCard(context),
          if (busy) const LinearProgressIndicator(),
          if (_recording)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Listening… tap the red microphone to send',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          if (_transcribing)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('ANDY is understanding your voice…'),
            ),
          if (_speaking)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text('ANDY is speaking…'),
            ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 5,
                      textInputAction: TextInputAction.newline,
                      decoration: const InputDecoration(
                        hintText: 'Ask ANDY...',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    onPressed: busy ? null : _toggleRecording,
                    style: _recording
                        ? IconButton.styleFrom(
                            backgroundColor: Theme.of(
                              context,
                            ).colorScheme.error,
                          )
                        : null,
                    icon: Icon(_recording ? Icons.stop : Icons.mic),
                    tooltip: _recording
                        ? 'Stop and send voice'
                        : 'Talk to ANDY',
                  ),
                  const SizedBox(width: 6),
                  IconButton.filled(
                    onPressed: busy || _recording ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
