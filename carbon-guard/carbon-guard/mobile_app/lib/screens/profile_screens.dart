import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/models.dart';
import '../state/session.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import 'submission_screens.dart';

class ProfileTab extends StatelessWidget {
  const ProfileTab({super.key});

  Future<void> _logout(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Log out?'),
        content: const Text('You will need your email and password to log in again.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Log out')),
        ],
      ),
    );
    if (ok == true && context.mounted) await context.read<Session>().logout();
  }

  void _open(BuildContext context, Widget screen) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));

  @override
  Widget build(BuildContext context) {
    final p = context.watch<Session>().profile;
    final theme = Theme.of(context);
    return ListView(padding: const EdgeInsets.all(16), children: [
      Center(
        child: CircleAvatar(
          radius: 36,
          backgroundColor: theme.colorScheme.primaryContainer,
          child: Text(p == null || p.name.isEmpty ? '?' : p.name[0].toUpperCase(),
              style: theme.textTheme.headlineMedium?.copyWith(color: theme.colorScheme.primary)),
        ),
      ),
      const SizedBox(height: 8),
      if (p != null) ...[
        Text(p.name, textAlign: TextAlign.center, style: theme.textTheme.titleLarge),
        Text(p.email, textAlign: TextAlign.center),
        Text('Member since ${formatDate(p.createdAt).split(',').first}', textAlign: TextAlign.center, style: theme.textTheme.bodySmall),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              InfoRow('Trust Score', '${formatNumber(p.trustScore, digits: 1)} / 100'),
              InfoRow('Green Credits', formatNumber(p.greenCreditsTotal)),
              InfoRow('Verified activities', '${p.counts.verified}'),
            ]),
          ),
        ),
      ],
      Card(
        child: Column(children: [
          ListTile(
            leading: const Icon(Icons.shield_outlined),
            title: const Text('Trust Score history'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _open(context, const TrustHistoryScreen()),
          ),
          ListTile(
            leading: const Icon(Icons.workspace_premium_outlined),
            title: const Text('Green Credit history'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _open(context, const CreditHistoryScreen()),
          ),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('How credits and scores work'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _open(context, const RulesScreen()),
          ),
        ]),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(onPressed: () => _logout(context), icon: const Icon(Icons.logout), label: const Text('Log out')),
    ]);
  }
}

/// Loads data once with a spinner and an error/retry state.
class _Loader<T> extends StatefulWidget {
  const _Loader({required this.load, required this.builder});

  final Future<T> Function(Session) load;
  final Widget Function(BuildContext, T) builder;

  @override
  State<_Loader<T>> createState() => _LoaderState<T>();
}

class _LoaderState<T> extends State<_Loader<T>> {
  late Future<T> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.load(context.read<Session>());
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snap.hasError) {
          return ErrorRetry(
            message: '${snap.error}',
            onRetry: () => setState(() => _future = widget.load(context.read<Session>())),
          );
        }
        return widget.builder(context, snap.data as T);
      },
    );
  }
}

class TrustHistoryScreen extends StatelessWidget {
  const TrustHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Trust Score history')),
      body: _Loader<TrustHistory>(
        load: (s) => s.api.trustHistory(),
        builder: (context, h) => ListView(padding: const EdgeInsets.all(12), children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${formatNumber(h.trustScore, digits: 1)} / ${formatNumber(h.trustMax, digits: 0)}',
                    style: Theme.of(context).textTheme.headlineMedium),
                const Text('Your Trust Score changes only when an administrator approves or rejects one of your '
                    'submissions. Missing evidence or server problems never lower it.'),
              ]),
            ),
          ),
          if (h.events.isEmpty) const EmptyHint(icon: Icons.history, text: 'No changes yet.'),
          for (final e in h.events.reversed)
            Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: e.scoreDelta >= 0 ? Colors.green.shade50 : Colors.red.shade50,
                  child: Text('${e.scoreDelta >= 0 ? '+' : ''}${formatNumber(e.scoreDelta, digits: 0)}',
                      style: TextStyle(color: e.scoreDelta >= 0 ? Colors.green.shade800 : Colors.red.shade800, fontSize: 13)),
                ),
                title: Text(e.reason),
                subtitle: Text('${formatDate(e.createdAt)} · score ${formatNumber(e.scoreAfter, digits: 1)}'),
                onTap: e.submissionId == null
                    ? null
                    : () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => SubmissionDetailScreen(id: e.submissionId!))),
              ),
            ),
        ]),
      ),
    );
  }
}

class CreditHistoryScreen extends StatelessWidget {
  const CreditHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Green Credit history')),
      body: _Loader<CreditHistory>(
        load: (s) => s.api.creditHistory(),
        builder: (context, h) => ListView(padding: const EdgeInsets.all(12), children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(formatNumber(h.total), style: Theme.of(context).textTheme.headlineMedium),
                const Text('Green Credits are reward points of this project. They are not official carbon credits.'),
              ]),
            ),
          ),
          if (h.transactions.isEmpty) const EmptyHint(icon: Icons.workspace_premium_outlined, text: 'No credits yet.'),
          for (final t in h.transactions)
            Card(
              child: ListTile(
                leading: const Icon(Icons.add_circle, color: Colors.green),
                title: Text('+${formatNumber(t.amount)} credits'),
                subtitle: Text(formatDate(t.createdAt)),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context)
                    .push(MaterialPageRoute(builder: (_) => SubmissionDetailScreen(id: t.submissionId))),
              ),
            ),
        ]),
      ),
    );
  }
}

class RulesScreen extends StatelessWidget {
  const RulesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('How it works')),
      body: _Loader<RulesInfo>(
        load: (s) => s.api.rules(),
        builder: (context, r) {
          final theme = Theme.of(context);
          return ListView(padding: const EdgeInsets.all(16), children: [
            Text('Green Credits', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text('You receive credits only after an administrator approves your submission:'),
            for (final a in r.activities)
              InfoRow(humanize(a.activityType), '${formatNumber(a.creditsPerUnit)} per ${a.scaleUnit.split(' ').first}'),
            const SizedBox(height: 16),
            Text('Trust Score', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Starts at ${formatNumber(r.trustInitial, digits: 0)} and stays between '
                '${formatNumber(r.trustMin, digits: 0)} and ${formatNumber(r.trustMax, digits: 0)}.'),
            for (final e in r.trustRules.entries)
              InfoRow(humanize(e.key), '${e.value >= 0 ? '+' : ''}${formatNumber(e.value, digits: 0)}'),
            const SizedBox(height: 16),
            Text('How evidence is checked', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            const Text('Your photo, GPS location and details are checked for plausibility and duplicates. '
                'Flags only ask an administrator to look closer.'),
            InfoRow('AI photo check', r.aiModelAvailable ? 'Active' : 'Not available on this server'),
            InfoRow('Satellite imagery', r.satelliteConfigured ? 'Active' : 'Not configured on this server'),
            const SizedBox(height: 16),
            Text(r.disclaimer, style: theme.textTheme.bodySmall),
          ]);
        },
      ),
    );
  }
}
