import 'package:flutter/material.dart';

/// The three activity types. `key` values must match API_CONTRACT.md exactly.
class Activity {
  const Activity(this.key, this.label, this.icon, this.unit, this.quantityLabel, this.photoTip);

  final String key, label, unit, quantityLabel, photoTip;
  final IconData icon;
}

const activities = <Activity>[
  Activity('tree_plantation', 'Tree plantation', Icons.park, 'trees', 'Number of trees planted',
      'Photograph the planted saplings clearly, in daylight, with the surroundings visible.'),
  Activity('solar_panel', 'Solar panel installation', Icons.solar_power, 'kW', 'Installed capacity (kW)',
      'Photograph the installed panels so the whole array is visible.'),
  Activity('water_harvesting', 'Water harvesting', Icons.water_drop, 'm³', 'Storage capacity (m³)',
      'Photograph the tank or pit and its inlet. 1 m³ = 1000 litres.'),
];

Activity activityByKey(String key) =>
    activities.firstWhere((a) => a.key == key, orElse: () => Activity(key, key, Icons.eco, '', 'Quantity', ''));
