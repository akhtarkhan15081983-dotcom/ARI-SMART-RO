import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class LiveLocationService {

  final storage = const FlutterSecureStorage();

  Timer? _timer;

  bool _running = false;

  

  void startTracking() {

    if(_running) return;

    _running = true;

    _timer = Timer.periodic(
      const Duration(seconds:10),
      (_) async {

        await sendCurrentLocation();

      },
    );

  }

  void stopTracking(){

    _timer?.cancel();

    _running=false;

  }

  Future<void> sendCurrentLocation() async{

    try{

      Position position =
          await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      final response = await http.post(

        Uri.parse(
          "${ApiService.baseUrl}/employees/live-location/",
        ),

        headers: await ApiService.authHeaders(),

        body: jsonEncode({

          "live_latitude":position.latitude,

          "live_longitude":position.longitude,

        }),

      );

      print("LIVE LOCATION : ${response.statusCode}");

      print(response.body);

      if (response.statusCode == 401) {
        stopTracking();
      }
      
    }catch(e){

      print(e);

    }

  }

}