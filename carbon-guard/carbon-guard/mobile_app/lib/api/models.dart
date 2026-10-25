// Data classes for the backend's JSON responses. Field names follow API_CONTRACT.md exactly.

double _d(dynamic v) => (v as num).toDouble();
double? _dn(dynamic v) => v == null ? null : (v as num).toDouble();
DateTime _t(dynamic v) => DateTime.parse(v as String).toLocal();
DateTime? _tn(dynamic v) => v == null ? null : DateTime.parse(v as String).toLocal();
List<String> _strings(dynamic v) => v == null ? <String>[] : List<String>.from(v as List);

class SubmissionCounts {
  final int total, processing, pending, manualReview, verified, rejected;

  SubmissionCounts.fromJson(Map<String, dynamic> j)
      : total = j['total'] as int,
        processing = j['processing'] as int,
        pending = j['pending'] as int,
        manualReview = j['manual_review'] as int,
        verified = j['verified'] as int,
        rejected = j['rejected'] as int;

  /// Submissions an admin still has to look at.
  int get waiting => processing + pending + manualReview;
}

class UserProfile {
  final String id, name, email, role;
  final double trustScore, greenCreditsTotal, totalCo2Estimate;
  final bool isActive;
  final DateTime createdAt;
  final SubmissionCounts counts;

  UserProfile.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        name = j['name'] as String,
        email = j['email'] as String,
        role = j['role'] as String,
        trustScore = _d(j['trust_score']),
        greenCreditsTotal = _d(j['green_credits_total']),
        totalCo2Estimate = _d(j['total_co2_estimate']),
        isActive = j['is_active'] as bool,
        createdAt = _t(j['created_at']),
        counts = SubmissionCounts.fromJson(j['submission_counts'] as Map<String, dynamic>);
}

class ResultPage<T> {
  final List<T> items;
  final int total, skip, limit;

  ResultPage.fromJson(Map<String, dynamic> j, T Function(Map<String, dynamic>) item)
      : items = (j['items'] as List).map((e) => item(e as Map<String, dynamic>)).toList(),
        total = j['total'] as int,
        skip = j['skip'] as int,
        limit = j['limit'] as int;
}

class SubmissionSummary {
  final String id, activityType, status, imageUrl;
  final double? verificationScore;
  final List<String> flags;
  final double greenCreditsAwarded;
  final DateTime createdAt;

  SubmissionSummary.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        activityType = j['activity_type'] as String,
        status = j['status'] as String,
        imageUrl = j['image_url'] as String,
        verificationScore = _dn(j['verification_score']),
        flags = _strings(j['flags']),
        greenCreditsAwarded = _d(j['green_credits_awarded']),
        createdAt = _t(j['created_at']);
}

class AiVerification {
  final String status;
  final String? model, predictedClass;
  final double? confidence;
  final bool? matched;
  final List<String> warnings;

  AiVerification.fromJson(Map<String, dynamic> j)
      : status = j['status'] as String,
        model = j['model'] as String?,
        predictedClass = j['predicted_class'] as String?,
        confidence = _dn(j['confidence']),
        matched = j['matched'] as bool?,
        warnings = _strings(j['warnings']);
}

class LocationVerification {
  final bool gpsValid;
  final double? accuracyM;
  final bool? accuracyOk;
  final String? address;
  final String geocodingStatus;
  final List<String> notes;

  LocationVerification.fromJson(Map<String, dynamic> j)
      : gpsValid = j['gps_valid'] as bool,
        accuracyM = _dn(j['accuracy_m']),
        accuracyOk = j['accuracy_ok'] as bool?,
        address = j['address'] as String?,
        geocodingStatus = j['geocoding_status'] as String,
        notes = _strings(j['notes']);
}

class SatelliteVerification {
  final String status;
  final String? source, acquisitionDate, imageUrl;
  final double? ndviMean;
  final bool? supportsClaim;
  final List<String> notes;

  SatelliteVerification.fromJson(Map<String, dynamic> j)
      : status = j['status'] as String,
        source = j['source'] as String?,
        acquisitionDate = j['acquisition_date'] as String?,
        imageUrl = j['image_url'] as String?,
        ndviMean = _dn(j['ndvi_mean']),
        supportsClaim = j['supports_claim'] as bool?,
        notes = _strings(j['notes']);
}

class FraudCheck {
  final List<String> flags, reasons;

  FraudCheck.fromJson(Map<String, dynamic> j)
      : flags = _strings(j['flags']),
        reasons = _strings(j['reasons']);
}

class SubmissionDetail {
  final String id, activityType, status, imageUrl;
  final double lat, lng;
  final double? accuracyM;
  final String? description;
  final double scaleValue;
  final AiVerification? ai;
  final LocationVerification? location;
  final SatelliteVerification? satellite;
  final FraudCheck? fraud;
  final double? verificationScore;
  final Map<String, double> scoreComponents;
  final List<String> decisionReasons;
  final double? co2Estimate;
  final double greenCreditsAwarded;
  final String? reviewNotes;
  final DateTime? reviewedAt;
  final DateTime createdAt, updatedAt;

  SubmissionDetail.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        activityType = j['activity_type'] as String,
        status = j['status'] as String,
        imageUrl = j['image_url'] as String,
        lat = _d(j['gps']['lat']),
        lng = _d(j['gps']['lng']),
        accuracyM = _dn(j['gps']['accuracy_m']),
        description = j['description'] as String?,
        scaleValue = _d(j['scale_value']),
        ai = j['ai_verification'] == null
            ? null
            : AiVerification.fromJson(j['ai_verification'] as Map<String, dynamic>),
        location = j['location_verification'] == null
            ? null
            : LocationVerification.fromJson(j['location_verification'] as Map<String, dynamic>),
        satellite = j['satellite_verification'] == null
            ? null
            : SatelliteVerification.fromJson(j['satellite_verification'] as Map<String, dynamic>),
        fraud = j['fraud_check'] == null ? null : FraudCheck.fromJson(j['fraud_check'] as Map<String, dynamic>),
        verificationScore = _dn(j['verification_score']),
        scoreComponents = ((j['score_components'] ?? {}) as Map<String, dynamic>)
            .map((k, v) => MapEntry(k, _d(v))),
        decisionReasons = _strings(j['decision_reasons']),
        co2Estimate = _dn((j['environmental_impact'] as Map<String, dynamic>)['co2_estimate']),
        greenCreditsAwarded = _d(j['green_credits_awarded']),
        reviewNotes = j['review_notes'] as String?,
        reviewedAt = _tn(j['reviewed_at']),
        createdAt = _t(j['created_at']),
        updatedAt = _t(j['updated_at']);
}

class TrustEvent {
  final String id, eventType, reason;
  final String? submissionId;
  final double scoreDelta, scoreAfter;
  final DateTime createdAt;

  TrustEvent.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        submissionId = j['submission_id'] as String?,
        eventType = j['event_type'] as String,
        reason = j['reason'] as String,
        scoreDelta = _d(j['score_delta']),
        scoreAfter = _d(j['score_after']),
        createdAt = _t(j['created_at']);
}

class TrustHistory {
  final double trustScore, trustMin, trustMax;
  final List<TrustEvent> events;

  TrustHistory.fromJson(Map<String, dynamic> j)
      : trustScore = _d(j['trust_score']),
        trustMin = _d(j['trust_min']),
        trustMax = _d(j['trust_max']),
        events = (j['events'] as List).map((e) => TrustEvent.fromJson(e as Map<String, dynamic>)).toList();
}

class CreditTransaction {
  final String id, submissionId, type;
  final double amount;
  final DateTime createdAt;

  CreditTransaction.fromJson(Map<String, dynamic> j)
      : id = j['id'] as String,
        submissionId = j['submission_id'] as String,
        type = j['type'] as String,
        amount = _d(j['amount']),
        createdAt = _t(j['created_at']);
}

class CreditHistory {
  final double total;
  final List<CreditTransaction> transactions;

  CreditHistory.fromJson(Map<String, dynamic> j)
      : total = _d(j['green_credits_total']),
        transactions =
            (j['transactions'] as List).map((e) => CreditTransaction.fromJson(e as Map<String, dynamic>)).toList();
}

class ActivityRule {
  final String activityType, scaleUnit;
  final double creditsPerUnit, maxScale;

  ActivityRule.fromJson(Map<String, dynamic> j)
      : activityType = j['activity_type'] as String,
        scaleUnit = j['scale_unit'] as String,
        creditsPerUnit = _d(j['credits_per_unit']),
        maxScale = _d(j['max_scale']);
}

class RulesInfo {
  final List<ActivityRule> activities;
  final double trustInitial, trustMin, trustMax;
  final Map<String, double> trustRules;
  final bool aiModelAvailable, satelliteConfigured;
  final String disclaimer;

  RulesInfo.fromJson(Map<String, dynamic> j)
      : activities =
            (j['activity_types'] as List).map((e) => ActivityRule.fromJson(e as Map<String, dynamic>)).toList(),
        trustInitial = _d(j['trust']['initial']),
        trustMin = _d(j['trust']['min']),
        trustMax = _d(j['trust']['max']),
        trustRules = (j['trust']['rules'] as Map<String, dynamic>).map((k, v) => MapEntry(k, _d(v))),
        aiModelAvailable = j['evidence']['ai_model_available'] as bool,
        satelliteConfigured = j['evidence']['satellite_configured'] as bool,
        disclaimer = j['disclaimer'] as String;
}
