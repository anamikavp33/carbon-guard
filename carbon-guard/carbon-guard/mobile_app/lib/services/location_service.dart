import 'package:geolocator/geolocator.dart';

/// The phone's current position.
class LocationResult {
  const LocationResult(this.latitude, this.longitude, this.accuracyM, this.isMocked);

  final double latitude, longitude;
  final double accuracyM;
  final bool isMocked; // Android: the position came from a mock-location app
}

/// A location problem with a message for the user.
class LocationProblem implements Exception {
  LocationProblem(this.message, {this.canOpenSettings = false});

  final String message;
  final bool canOpenSettings;

  @override
  String toString() => message;
}

/// Asks for permission if needed, then reads the GPS position (up to 30 seconds).
Future<LocationResult> getCurrentLocation() async {
  if (!await Geolocator.isLocationServiceEnabled()) {
    throw LocationProblem('Location (GPS) is turned off. Turn it on in the quick settings and try again.');
  }
  var permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
  }
  if (permission == LocationPermission.denied) {
    throw LocationProblem('Location permission is needed to record where the activity took place.');
  }
  if (permission == LocationPermission.deniedForever) {
    throw LocationProblem(
      'Location permission is blocked. Open the app settings and allow location.',
      canOpenSettings: true,
    );
  }
  try {
    final p = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 30),
      ),
    );
    return LocationResult(p.latitude, p.longitude, p.accuracy, p.isMocked);
  } catch (_) {
    throw LocationProblem('Could not get a GPS fix. Move outdoors or near a window and try again.');
  }
}

Future<void> openLocationSettings() => Geolocator.openAppSettings();
