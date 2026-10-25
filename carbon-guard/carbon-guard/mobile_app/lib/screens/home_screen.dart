import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../activities.dart';
import '../state/session.dart';
import '../utils/format.dart';
import '../widgets/common.dart';
import 'new_submission_screen.dart';
import 'profile_screens.dart';
import 'submission_screens.dart';

/// Bottom navigation: Home, My submissions, Profile.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    // Tabs are rebuilt when selected, so they always show fresh data.
    final body = switch (_tab) {
      0 => HomeTab(onShowSubmissions: () => setState(() => _tab = 1)),
      1 => const SubmissionsTab(),
      _ => const ProfileTab(),
    };
    return Scaffold(
      body: SafeArea(child: body),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.list_alt_outlined), selectedIcon: Icon(Icons.list_alt), label: 'My submissions'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

class HomeTab extends StatefulWidget {
  const HomeTab({super.key, required this.onShowSubmissions});

  final VoidCallback onShowSubmissions;

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    try {
      await context.read<Session>().refreshProfile();
      if (mounted) setState(() => _error = null);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _newSubmission(Activity a) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NewSubmissionScreen(activity: a)));
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final p = context.watch<Session>().profile;
    final theme = Theme.of(context);
    if (p == null) {
      return _error != null ? ErrorRetry(message: _error!, onRetry: _refresh) : const Center(child: CircularProgressIndicator());
    }
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Hello, ${p.name.split(' ').first}', style: theme.textTheme.headlineSmall),
        const SizedBox(height: 4),
        const Text('Thank you for helping the environment.'),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('Could not refresh: $_error', style: TextStyle(color: theme.colorScheme.error)),
          ),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(
            child: _StatCard(
              icon: Icons.workspace_premium,
              label: 'Green Credits',
              value: formatNumber(p.greenCreditsTotal),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _StatCard(
              icon: Icons.shield_outlined,
              label: 'Trust Score',
              value: formatNumber(p.trustScore, digits: 1),
              progress: p.trustScore / 100,
            ),
          ),
        ]),
        const SizedBox(height: 12),
        Card(
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: widget.onShowSubmissions,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
                _Count('Submitted', p.counts.total),
                _Count('Verified', p.counts.verified),
                _Count('Waiting', p.counts.waiting),
                _Count('Rejected', p.counts.rejected),
              ]),
            ),
          ),
        ),
        if (p.totalCo2Estimate > 0)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              'Estimated impact of your verified activities: ${formatNumber(p.totalCo2Estimate)} kg CO2 per year '
              '(a project estimate, not a certified measurement).',
              style: theme.textTheme.bodySmall,
            ),
          ),
        const SizedBox(height: 20),
        Text('Record a new activity', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final a in activities)
          Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: theme.colorScheme.primaryContainer,
                child: Icon(a.icon, color: theme.colorScheme.primary),
              ),
              title: Text(a.label),
              subtitle: Text('Quantity in ${a.unit}'),
              trailing: const Icon(Icons.add_a_photo_outlined),
              onTap: () => _newSubmission(a),
            ),
          ),
      ]),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.icon, required this.label, required this.value, this.progress});

  final IconData icon;
  final String label, value;
  final double? progress;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: theme.colorScheme.primary),
          const SizedBox(height: 8),
          Text(value, style: theme.textTheme.headlineMedium?.copyWith(color: theme.colorScheme.primary)),
          Text(label),
          if (progress != null) ...[
            const SizedBox(height: 8),
            LinearProgressIndicator(value: progress!.clamp(0, 1).toDouble(), minHeight: 6, borderRadius: BorderRadius.circular(3)),
          ],
        ]),
      ),
    );
  }
}

class _Count extends StatelessWidget {
  const _Count(this.label, this.value);

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Text('$value', style: Theme.of(context).textTheme.titleLarge),
      Text(label, style: Theme.of(context).textTheme.bodySmall),
    ]);
  }
}
