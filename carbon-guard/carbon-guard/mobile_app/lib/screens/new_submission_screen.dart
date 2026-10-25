import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../activities.dart';
import '../services/location_service.dart';
import '../state/session.dart';
import '../utils/format.dart';
import '../utils/validators.dart';
import '../widgets/common.dart';
import 'submission_screens.dart';

/// Photo + GPS + details form for one activity type.
class NewSubmissionScreen extends StatefulWidget {
  const NewSubmissionScreen({super.key, required this.activity});

  final Activity activity;

  @override
  State<NewSubmissionScreen> createState() => _NewSubmissionScreenState();
}

class _NewSubmissionScreenState extends State<NewSubmissionScreen> {
  final _form = GlobalKey<FormState>();
  final _quantity = TextEditingController();
  final _description = TextEditingController();
  final _picker = ImagePicker();

  Uint8List? _imageBytes;
  String _imageName = 'photo.jpg';
  LocationResult? _location;
  LocationProblem? _locationProblem;
  bool _locating = false;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future.microtask(_locate); // start looking for GPS as soon as the screen opens
  }

  @override
  void dispose() {
    _quantity.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _locate() async {
    setState(() {
      _locating = true;
      _locationProblem = null;
    });
    try {
      final loc = await getCurrentLocation();
      if (mounted) setState(() => _location = loc);
    } on LocationProblem catch (p) {
      if (mounted) setState(() => _locationProblem = p);
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _pick(ImageSource source) async {
    try {
      // Resize/compress on the phone: smaller uploads, still plenty of detail for checking.
      final file = await _picker.pickImage(source: source, maxWidth: 1920, maxHeight: 1920, imageQuality: 85);
      if (file == null) return; // user cancelled
      final bytes = await file.readAsBytes();
      if (bytes.length > 8 * 1024 * 1024) {
        if (mounted) showMessage(context, 'That photo is larger than 8 MB. Please choose another one.');
        return;
      }
      setState(() {
        _imageBytes = bytes;
        _imageName = file.name.isEmpty ? 'photo.jpg' : file.name;
      });
    } catch (e) {
      if (mounted) showMessage(context, 'Could not open the ${source == ImageSource.camera ? 'camera' : 'gallery'}: $e');
    }
  }

  Future<void> _submit() async {
    setState(() => _error = null);
    final formOk = _form.currentState!.validate();
    if (_imageBytes == null) {
      setState(() => _error = 'Please add a photo of the activity.');
      return;
    }
    if (_location == null) {
      setState(() => _error = 'Your location is needed. Tap "Get location" and allow access.');
      return;
    }
    if (!formOk) return;

    setState(() => _sending = true);
    try {
      final id = await context.read<Session>().api.createSubmission(
            activityType: widget.activity.key,
            latitude: _location!.latitude,
            longitude: _location!.longitude,
            gpsAccuracyM: _location!.accuracyM,
            gpsIsMocked: _location!.isMocked,
            scaleValue: double.parse(_quantity.text.trim()),
            description: _description.text,
            imageBytes: _imageBytes!,
            imageName: _imageName,
          );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => SubmissionResultScreen(id: id)));
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = widget.activity;
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(a.label)),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(padding: const EdgeInsets.all(16), children: [
            // ---- photo ----
            Text('1. Photo', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(a.photoTip),
            const SizedBox(height: 8),
            if (_imageBytes != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(_imageBytes!, height: 220, fit: BoxFit.cover),
              ),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: FilledButton.tonalIcon(
                  onPressed: _sending ? null : () => _pick(ImageSource.camera),
                  icon: const Icon(Icons.photo_camera),
                  label: Text(_imageBytes == null ? 'Take photo' : 'Retake'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _sending ? null : () => _pick(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library),
                  label: const Text('Gallery'),
                ),
              ),
            ]),
            const SizedBox(height: 20),

            // ---- location ----
            Text('2. Location', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: _locating
                    ? const Row(children: [
                        SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
                        SizedBox(width: 12),
                        Text('Getting your GPS location...'),
                      ])
                    : _location != null
                        ? Row(children: [
                            Icon(Icons.location_on, color: theme.colorScheme.primary),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text('${_location!.latitude.toStringAsFixed(5)}, '
                                  '${_location!.longitude.toStringAsFixed(5)}\n'
                                  'Accuracy about ${formatNumber(_location!.accuracyM, digits: 0)} m'),
                            ),
                            TextButton(onPressed: _locate, child: const Text('Refresh')),
                          ])
                        : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(_locationProblem?.message ?? 'Location not available yet.',
                                style: TextStyle(color: theme.colorScheme.error)),
                            const SizedBox(height: 8),
                            Wrap(spacing: 8, children: [
                              FilledButton.tonal(onPressed: _locate, child: const Text('Get location')),
                              if (_locationProblem?.canOpenSettings ?? false)
                                OutlinedButton(onPressed: openLocationSettings, child: const Text('Open settings')),
                            ]),
                          ]),
              ),
            ),
            Text('Please submit while you are at the activity site.', style: theme.textTheme.bodySmall),
            const SizedBox(height: 20),

            // ---- details ----
            Text('3. Details', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            TextFormField(
              controller: _quantity,
              decoration: InputDecoration(labelText: a.quantityLabel, suffixText: a.unit),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) => validateQuantity(v),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _description,
              decoration: const InputDecoration(labelText: 'Description (optional)', hintText: 'What did you do, and where?'),
              maxLength: 500,
              maxLines: 3,
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
              ),
            FilledButton.icon(
              onPressed: _sending ? null : _submit,
              icon: _sending
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.cloud_upload),
              label: Text(_sending ? 'Uploading...' : 'Submit for verification'),
            ),
            const SizedBox(height: 8),
            Text(
              'Your photo, location and details are checked automatically and then reviewed by an administrator.',
              style: theme.textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ]),
        ),
      ),
    );
  }
}
