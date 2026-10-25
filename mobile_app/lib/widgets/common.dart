import 'package:flutter/material.dart';

import '../utils/format.dart';

/// Colour, label and plain-language meaning of each submission status.
class StatusInfo {
  const StatusInfo(this.label, this.color, this.icon, this.meaning);

  final String label, meaning;
  final Color color;
  final IconData icon;
}

const statusInfo = <String, StatusInfo>{
  'processing': StatusInfo('Checking', Color(0xFF5F6F67), Icons.hourglass_top,
      'Automatic checks are running. This usually takes a few seconds.'),
  'pending': StatusInfo('Awaiting approval', Color(0xFF2F5D8A), Icons.schedule,
      'The automatic checks look good. An administrator will approve or reject it.'),
  'manual_review': StatusInfo('In review', Color(0xFF8A5A00), Icons.manage_search,
      'An administrator will look at this carefully. This is normal and is not an accusation.'),
  'verified': StatusInfo('Verified', Color(0xFF1F7A4D), Icons.verified,
      'Approved by an administrator. Green Credits were added to your balance.'),
  'rejected': StatusInfo('Rejected', Color(0xFFB53A2D), Icons.cancel,
      'Not accepted. See the notes below for the reason.'),
};

StatusInfo infoFor(String status) =>
    statusInfo[status] ?? StatusInfo(humanize(status), Colors.grey, Icons.help_outline, '');

class StatusChip extends StatelessWidget {
  const StatusChip(this.status, {super.key});

  final String status;

  @override
  Widget build(BuildContext context) {
    final info = infoFor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: info.color.withAlpha(30),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(info.icon, size: 14, color: info.color),
        const SizedBox(width: 4),
        Text(info.label, style: TextStyle(color: info.color, fontWeight: FontWeight.w600, fontSize: 12)),
      ]),
    );
  }
}

/// A message with a "Try again" button, used when loading fails.
class ErrorRetry extends StatelessWidget {
  const ErrorRetry({super.key, required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.cloud_off, size: 48, color: Theme.of(context).colorScheme.error),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          FilledButton.tonal(onPressed: onRetry, child: const Text('Try again')),
        ]),
      ),
    );
  }
}

/// A grey hint shown when a list is empty.
class EmptyHint extends StatelessWidget {
  const EmptyHint({super.key, required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(children: [
        Icon(icon, size: 48, color: Colors.grey),
        const SizedBox(height: 8),
        Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
      ]),
    );
  }
}

/// Label on the left, value on the right.
class InfoRow extends StatelessWidget {
  const InfoRow(this.label, this.value, {super.key});

  final String label;
  final String? value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(flex: 2, child: Text(label, style: TextStyle(color: Colors.grey.shade700))),
        const SizedBox(width: 8),
        Expanded(flex: 3, child: Text(value == null || value!.isEmpty ? '-' : value!, textAlign: TextAlign.right)),
      ]),
    );
  }
}

void showMessage(BuildContext context, String text) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
}
