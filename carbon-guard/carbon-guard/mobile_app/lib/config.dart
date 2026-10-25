/// Address of the Carbon Guard backend.
///
/// Choose it when you start the app, for example:
///   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000   (real phone on the same Wi-Fi)
///   flutter run                                                        (emulator: default below)
///
/// 10.0.2.2 is how the Android emulator reaches "localhost" on the computer it runs on.
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
