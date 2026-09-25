import 'package:flutter/material.dart';

/// 전체 공개 폼 — 제목과 한 줄 설명.
///
/// 🔴 **공개와 제목을 한 번에 보낸다.** 나눠 보내면 그 사이에 끊겼을 때
/// **이름 없는 영상이 남에게 보인다.** 그래서 「공개하기」 하나가 둘을 다
/// 싣고, 제목이 비면 눌리지 않는다.
class PublishForm extends StatefulWidget {
  const PublishForm({
    super.key,
    required this.onSave,
    required this.onCancel,
    this.onPaper = false,
  });

  /// `(제목, 한 줄 설명)`.
  final void Function(String title, String what) onSave;
  final VoidCallback onCancel;

  /// 밝은 판 위인가 — 🔴 **글자와 밑줄이 통째로 뒤집힌다.** 안 뒤집으면
  /// 흰 글자가 밝은 판에 얹혀 **입력한 것이 안 보인다.**
  final bool onPaper;

  @override
  State<PublishForm> createState() => _PublishFormState();
}

class _PublishFormState extends State<PublishForm> {
  final _title = TextEditingController();
  final _what = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _what.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final canSave = _title.text.trim().isNotEmpty;
    final ink = widget.onPaper ? _kOnPaper : _kOn;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ink.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            key: const Key('publish-title'),
            controller: _title,
            maxLength: 40,
            style: TextStyle(color: ink, fontSize: 14),
            decoration: _dec(ink, '제목', '무엇을 보는 장면인가요'),
            onChanged: (_) => setState(() {}),
          ),
          TextField(
            key: const Key('publish-what'),
            controller: _what,
            maxLength: 60,
            style: TextStyle(color: ink, fontSize: 14),
            decoration: _dec(ink, '한 줄 설명', '없어도 됩니다'),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  key: const Key('publish-save'),
                  onPressed: canSave
                      ? () => widget.onSave(
                            _title.text.trim(),
                            _what.text.trim(),
                          )
                      : null,
                  child: const Text('공개하기'),
                ),
              ),
              const SizedBox(width: 8),
              TextButton(
                key: const Key('publish-cancel'),
                onPressed: widget.onCancel,
                style: TextButton.styleFrom(foregroundColor: ink),
                child: const Text('취소'),
              ),
            ],
          ),
          const SizedBox(height: 6),
          /* 🔴 **공개는 되돌릴 수 있지만 그 사이에 남이 본다.** 무엇이
             일어나는지 누르기 전에 말한다. */
          Text(
            '영상 모음에서 다른 사람에게도 보입니다 — 언제든 다시 내릴 수 있습니다.',
            style: TextStyle(
              color: ink.withValues(alpha: 0.55),
              fontSize: 11,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  InputDecoration _dec(Color ink, String label, String hint) => InputDecoration(
        labelText: label,
        hintText: hint,
        isDense: true,
        labelStyle: TextStyle(color: ink.withValues(alpha: 0.7), fontSize: 13),
        hintStyle: TextStyle(color: ink.withValues(alpha: 0.35), fontSize: 13),
        counterStyle: TextStyle(color: ink.withValues(alpha: 0.4)),
        enabledBorder: UnderlineInputBorder(
          borderSide: BorderSide(color: ink.withValues(alpha: 0.25)),
        ),
      );
}

const Color _kOn = Color(0xFFFFFFFF);
const Color _kOnPaper = Color(0xFF14161A);
