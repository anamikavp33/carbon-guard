# Carbon Guard mobile app (owner: Amritha)

Flutter app for Android. Users register, log in, record an activity (photo + GPS + quantity + description),
follow its verification status and see their Green Credits and Trust Score. It talks only to the
backend API in [`../API_CONTRACT.md`](../API_CONTRACT.md); it never connects to MongoDB.

> **Status (honest):** the Dart code and tests are written but have **not been compiled or run yet**,
> because Flutter is not installed on the development PC used so far. The first person with Flutter must
> run `flutter analyze` and `flutter test` and fix anything they report. See "First run checklist" below.

## Screens

| Screen | File |
|---|---|
| Splash, onboarding (first start only) | `lib/screens/onboarding_screen.dart` |
| Login, register | `lib/screens/auth_screens.dart` |
| Home: credits, Trust Score, counts, choose activity | `lib/screens/home_screen.dart` |
| New submission: camera/gallery, GPS, quantity, description | `lib/screens/new_submission_screen.dart` |
| Submission received (waits for the checks), My submissions, detail | `lib/screens/submission_screens.dart` |
| Profile, Trust Score history, Green Credit history, rules, logout | `lib/screens/profile_screens.dart` |

Other files: `lib/api/` (HTTP calls and JSON models), `lib/state/session.dart` (login state; token in
encrypted storage), `lib/services/location_service.dart` (GPS + permissions), `lib/config.dart` (backend address).

## Setup (Windows)

1. Install Flutter (stable) and Android Studio: see `../SETUP_GUIDE.md`, section "Mobile app". Check with `flutter doctor`.
2. Create the Android project files and permissions (once):
   ```powershell
   cd carbon-guard\mobile_app
   powershell -ExecutionPolicy Bypass -File setup_android.ps1
   ```
   It runs `flutter create` (only adds missing files; your Dart code is kept), `flutter pub get`, and adds the
   INTERNET + location permissions and `usesCleartextTraffic` (needed for the `http://` development backend)
   to `android/app/src/main/AndroidManifest.xml`.
3. Start the backend so other devices can reach it: `uvicorn main:app --host 0.0.0.0 --port 8000`
   (allow Python through Windows Firewall when asked, on *private* networks).
4. Run the app:
   ```bat
   rem Android emulator (10.0.2.2 = the PC running the emulator)
   flutter run
   rem Real phone on the same Wi-Fi: use the backend laptop's IPv4 address (ipconfig)
   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000
   ```
   There is no `.env` file in the app: the backend address is the only setting and it is passed with
   `--dart-define`. No secrets are ever built into the app.

## Tests

```bat
flutter test
```
`test/models_test.dart` parses the contract's real example responses, `test/api_client_test.dart` checks the
HTTP calls (including the multipart upload) with a fake server, `test/widgets_test.dart` checks validators,
formatting, the status chip and login form validation.

## First run checklist (whoever runs it first)

- [ ] `flutter analyze` shows no errors (warnings/infos are OK to note).
- [ ] `flutter test` passes.
- [ ] On the emulator: register → home shows 0 credits, Trust Score 50.
- [ ] New tree submission with the emulator camera; location permission prompt appears; set the emulator
      location in *Extended controls → Location*.
- [ ] "Checking..." then a status; the submission appears in My submissions with its photo.
- [ ] Approve it in the admin dashboard → pull to refresh on Home: credits and Trust Score go up.
- [ ] Turn off the backend → screens show a "Try again" message instead of crashing.
- [ ] Record the results in `../PROJECT_STATUS.md`.

## Common problems

| Problem | Fix |
|---|---|
| "Cannot reach the server" | Backend not running, wrong `API_BASE_URL`, phone on another network, or Windows Firewall blocking port 8000 |
| Works on emulator, not on phone | Use the laptop's IP (not 10.0.2.2) and start uvicorn with `--host 0.0.0.0` |
| `Cleartext HTTP traffic not permitted` | Run `setup_android.ps1` again (adds `usesCleartextTraffic`) |
| Location never arrives on emulator | Set a location in the emulator's Extended controls, or press "Refresh" |
| "Only JPEG, PNG or WEBP images are accepted" | Some phones save HEIC photos; switch the camera format to JPEG or use the in-app camera button |
| Gradle/SDK version errors | `flutter doctor`, update Android SDK; geolocator needs a recent compileSdk (Flutter's default is fine) |
