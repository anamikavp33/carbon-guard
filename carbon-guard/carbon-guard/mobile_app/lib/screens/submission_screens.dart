import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../activities.dart';
import '../api/models.dart';
import '../state/session.dart';
import '../utils/format.dart';
import '../widgets/common.dart';

/// Shown right after uploading: waits for the automatic checks, then shows the outcome.
class SubmissionResultScreen extends StatefulWidget {
  const SubmissionResultScreen({super.key, required this.id});

  final String id;

  @override
  State<SubmissionResultScreen> createState() => _SubmissionResultScreenState();
}

class _SubmissionResultScreenState extends State<SubmissionResultScreen> {
  String _status = 'processing';
  String? _error;
  Timer? _timer;
  int _tries = 0;

  @override
  void initState() {
    super.initState();
    _poll();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final s = await context.read<Session>().api.submissionStatus(widget.id);
      if (!mounted) return;
      setState(() {
        _status = s;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
    _tries++;
    // Ask again every 2 seconds while processing, for up to about 2 minutes.
    if (mounted && _status == 'processing' && _tries < 60) {
      _timer = Timer(const Duration(seconds: 2), _poll);
    }
  }

  @override
  Widget build(BuildContext context) {
    final info = infoFor(_status);
    final theme = Theme.of(context);
    final processing = _status == 'processing';
    return Scaffold(
      appBar: AppBar(title: const Text('Submitted'), automaticallyImplyLeading: false),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Icon(Icons.check_circle, size: 72, color: theme.colorScheme.primary),
            const SizedBox(height: 12),
            Text('Thank you! Your activity was received.', textAlign: TextAlign.center, style: theme.textTheme.titleLarge),
            const SizedBox(height: 24),
            if (processing && _tries < 60)
              const Column(children: [
                CircularProgressIndicator(),
                SizedBox(height: 12),
                Text('Checking your photo and location...', textAlign: TextAlign.center),
              ])
            else ...[
              Center(child: StatusChip(_status)),
              const SizedBox(height: 8),
              Text(processing ? 'The checks are taking longer than usual. You can see the result later in My submissions.' : info.meaning,
                  textAlign: TextAlign.center),
            ],
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(_error!, textAlign: TextAlign.center, style: TextStyle(color: theme.colorScheme.error)),
              ),
            const SizedBox(height: 32),
            FilledButton(
              onPressed: () => Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => SubmissionDetailScreen(id: widget.id))),
              child: const Text('View details'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Back to home')),
          ]),
        ),
      ),
    );
  }
}

/// "My submissions" tab: newest first, pull to refresh, "Load more" at the end.
class SubmissionsTab extends StatefulWidget {
  const SubmissionsTab({super.key});

  @override
  State<SubmissionsTab> createState() => _SubmissionsTabState();
}

class _SubmissionsTabState extends State<SubmissionsTab> {
  final _items = <SubmissionSummary>[];
  int _total = 0;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(() => _load(reset: true)); // after the first frame setup

  }

  Future<void> _load({bool reset = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await context.read<Session>().api.mySubmissions(skip: reset ? 0 : _items.length);
      if (!mounted) return;
      setState(() {
        if (reset) _items.clear();
        _items.addAll(page.items);
        _total = page.total;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_items.isEmpty && _loading) return const Center(child: CircularProgressIndicator());
    if (_items.isEmpty && _error != null) return ErrorRetry(message: _error!, onRetry: () => _load(reset: true));
    final api = context.read<Session>().api;
    return RefreshIndicator(
      onRefresh: () => _load(reset: true),
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _items.length + 2,
        itemBuilder: (context, i) {
          if (i == 0) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(4, 4, 4, 8),
              child: Text('My submissions ($_total)', style: Theme.of(context).textTheme.titleLarge),
            );
          }
          if (i == _items.length + 1) {
            if (_items.isEmpty) {
              return const EmptyHint(icon: Icons.eco_outlined, text: 'No submissions yet.\nRecord your first activity from the Home tab.');
            }
            if (_items.length < _total) {
              return Padding(
                padding: const EdgeInsets.all(8),
                child: OutlinedButton(onPressed: _loading ? null : () => _load(), child: Text(_loading ? 'Loading...' : 'Load more')),
              );
            }
            return const SizedBox(height: 24);
          }
          final s = _items[i - 1];
          final a = activityByKey(s.activityType);
          return Card(
            child: ListTile(
              leading: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(api.fileUrl(s.imageUrl), width: 56, height: 56, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Icon(a.icon, size: 40)),
              ),
              title: Text(a.label),
              subtitle: Text(formatDate(s.createdAt)),
              trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                StatusChip(s.status),
                if (s.greenCreditsAwarded > 0) Text('+${formatNumber(s.greenCreditsAwarded)} credits', style: const TextStyle(fontSize: 12)),
              ]),
              onTap: () async {
                await Navigator.of(context).push(MaterialPageRoute(builder: (_) => SubmissionDetailScreen(id: s.id)));
                _load(reset: true);
              },
            ),
          );
        },
      ),
    );
  }
}

/// Everything about one submission: photo, status, score, evidence and the reasons.
class SubmissionDetailScreen extends StatefulWidget {
  const SubmissionDetailScreen({super.key, required this.id});

  final String id;

  @override
  State<SubmissionDetailScreen> createState() => _SubmissionDetailScreenState();
}

class _SubmissionDetailScreenState extends State<SubmissionDetailScreen> {
  late Future<SubmissionDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<Session>().api.submission(widget.id);
  }

  void _reload() => setState(() => _future = context.read<Session>().api.submission(widget.id));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Submission'), actions: [
        IconButton(tooltip: 'Refresh', onPressed: _reload, icon: const Icon(Icons.refresh)),
      ]),
      body: FutureBuilder<SubmissionDetail>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (snap.hasError) return ErrorRetry(message: '${snap.error}', onRetry: _reload);
          return _DetailBody(s: snap.data!);
        },
      ),
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({required this.s});

  final SubmissionDetail s;

  String _yesNo(bool? v) => v == null ? 'Unknown' : (v ? 'Yes' : 'No');

  @override
  Widget build(BuildContext context) {
    final api = context.read<Session>().api;
    final theme = Theme.of(context);
    final a = activityByKey(s.activityType);
    final info = infoFor(s.status);
    Widget section(String title, List<Widget> children) => Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              ...children,
            ]),
          ),
        );

    return ListView(padding: const EdgeInsets.all(12), children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.network(api.fileUrl(s.imageUrl), height: 240, fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => const SizedBox(height: 120, child: Center(child: Text('Photo could not be loaded')))),
      ),
      const SizedBox(height: 12),
      section(a.label, [
        StatusChip(s.status),
        const SizedBox(height: 6),
        Text(info.meaning),
        if (s.reviewNotes != null) ...[
          const SizedBox(height: 8),
          Text('Note from the reviewer: ${s.reviewNotes}', style: const TextStyle(fontStyle: FontStyle.italic)),
        ],
        const Divider(),
        InfoRow('Quantity', '${formatNumber(s.scaleValue)} ${a.unit}'),
        InfoRow('Submitted', formatDate(s.createdAt)),
        if (s.reviewedAt != null) InfoRow('Reviewed', formatDate(s.reviewedAt!)),
        InfoRow('Description', s.description),
        InfoRow('Green Credits', s.greenCreditsAwarded > 0 ? '+${formatNumber(s.greenCreditsAwarded)}' : '0'),
        if (s.co2Estimate != null) InfoRow('Estimated CO2', '${formatNumber(s.co2Estimate)} kg/year (estimate)'),
      ]),
      if (s.status != 'processing')
        section('Verification score: ${formatNumber(s.verificationScore, digits: 1)} / 100', [
          for (final r in s.decisionReasons)
            Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('• $r')),
          Text('The score helps the reviewer. An administrator makes the final decision.', style: theme.textTheme.bodySmall),
        ]),
      if (s.fraud != null && s.fraud!.flags.isNotEmpty)
        section('Flagged for review', [
          const Text('These points need a human check. They are not an accusation.'),
          const SizedBox(height: 6),
          for (final r in s.fraud!.reasons) Text('• $r'),
        ]),
      section('Location', [
        InfoRow('Coordinates', '${s.lat.toStringAsFixed(5)}, ${s.lng.toStringAsFixed(5)}'),
        InfoRow('GPS accuracy', s.accuracyM == null ? 'not reported' : '${formatNumber(s.accuracyM, digits: 0)} m'),
        if (s.location != null) InfoRow('Address', s.location!.address),
        if (s.location != null) for (final n in s.location!.notes) Text(n, style: theme.textTheme.bodySmall),
      ]),
      if (s.ai != null)
        section('Photo check (AI)', [
          InfoRow('Status', humanize(s.ai!.status)),
          if (s.ai!.predictedClass != null) InfoRow('Recognised as', humanize(s.ai!.predictedClass!)),
          if (s.ai!.confidence != null) InfoRow('Confidence', '${formatNumber(s.ai!.confidence! * 100, digits: 0)}%'),
          InfoRow('Matches your activity', _yesNo(s.ai!.matched)),
          for (final w in s.ai!.warnings) Text(w, style: theme.textTheme.bodySmall),
        ]),
      if (s.satellite != null)
        section('Satellite evidence', [
          InfoRow('Status', humanize(s.satellite!.status)),
          if (s.satellite!.acquisitionDate != null) InfoRow('Image date', s.satellite!.acquisitionDate),
          if (s.satellite!.imageUrl != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Image.network(api.fileUrl(s.satellite!.imageUrl!), height: 180, fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const SizedBox.shrink()),
            ),
          for (final n in s.satellite!.notes) Text(n, style: theme.textTheme.bodySmall),
        ]),
      const SizedBox(height: 24),
    ]);
  }
}
