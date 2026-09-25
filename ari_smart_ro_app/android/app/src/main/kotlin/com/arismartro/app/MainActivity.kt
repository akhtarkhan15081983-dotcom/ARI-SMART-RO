package com.arismartro.app

import android.app.ActivityManager
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.PowerManager
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream

class MainActivity : FlutterActivity() {
    private val downloadsChannel = "com.arismartro.app/downloads"
    private val deviceCapabilitiesChannel = "com.arismartro.app/device_capabilities"
    private val referralChannelName = "com.arismartro.app/referral"
    private val smsGatewayChannelName = "com.arismartro.app/sms_gateway"
    private var referralChannel: MethodChannel? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        referralChannel = MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            referralChannelName,
        ).also { channel ->
            channel.setMethodCallHandler { call, result ->
                if (call.method == "getInitialReferralCode") {
                    result.success(referralCode(intent))
                } else {
                    result.notImplemented()
                }
            }
        }

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            smsGatewayChannelName,
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "configure" -> {
                    val gatewayId = call.argument<String>("gatewayId").orEmpty()
                    val gatewayKey = call.argument<String>("gatewayKey").orEmpty()
                    val baseUrl = call.argument<String>("baseUrl").orEmpty().trimEnd('/')
                    if (gatewayId.isBlank() || gatewayKey.isBlank() || baseUrl.isBlank()) {
                        result.error("INVALID_GATEWAY", "Gateway ID, key and API URL are required.", null)
                        return@setMethodCallHandler
                    }
                    getSharedPreferences(SmsVerificationReceiver.PREFS_NAME, MODE_PRIVATE)
                        .edit()
                        .putString(SmsVerificationReceiver.KEY_GATEWAY_ID, gatewayId)
                        .putString(SmsVerificationReceiver.KEY_GATEWAY_KEY, gatewayKey)
                        .putString(SmsVerificationReceiver.KEY_BASE_URL, baseUrl)
                        .apply()
                    result.success(true)
                }
                "clear" -> {
                    getSharedPreferences(SmsVerificationReceiver.PREFS_NAME, MODE_PRIVATE)
                        .edit()
                        .clear()
                        .apply()
                    result.success(true)
                }
                "isConfigured" -> {
                    val prefs = getSharedPreferences(SmsVerificationReceiver.PREFS_NAME, MODE_PRIVATE)
                    result.success(
                        !prefs.getString(SmsVerificationReceiver.KEY_GATEWAY_ID, "").isNullOrBlank() &&
                            !prefs.getString(SmsVerificationReceiver.KEY_GATEWAY_KEY, "").isNullOrBlank()
                    )
                }
                else -> result.notImplemented()
            }
        }

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            deviceCapabilitiesChannel,
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "isLowMemoryDevice" -> {
                    val activityManager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
                    val lowMemory = activityManager.isLowRamDevice || activityManager.memoryClass <= 256
                    result.success(lowMemory)
                }
                "getDeviceHealth" -> {
                    val activityManager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
                    val memoryInfo = ActivityManager.MemoryInfo()
                    activityManager.getMemoryInfo(memoryInfo)
                    val locationManager = getSystemService(LOCATION_SERVICE) as LocationManager
                    val powerManager = getSystemService(POWER_SERVICE) as PowerManager
                    val packageInfo = packageManager.getPackageInfo(packageName, 0)
                    val fineLocation = checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                    val backgroundLocation = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        checkSelfPermission(android.Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED
                    } else {
                        fineLocation
                    }
                    val notificationGranted = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
                    } else {
                        true
                    }
                    val versionCode = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                        packageInfo.longVersionCode.toString()
                    } else {
                        @Suppress("DEPRECATION")
                        packageInfo.versionCode.toString()
                    }
                    result.success(
                        mapOf(
                            "platform" to "ANDROID",
                            "app_version" to (packageInfo.versionName ?: ""),
                            "app_build" to versionCode,
                            "os_version" to Build.VERSION.RELEASE,
                            "android_sdk" to Build.VERSION.SDK_INT,
                            "manufacturer" to Build.MANUFACTURER,
                            "model" to Build.MODEL,
                            "low_memory_device" to (activityManager.isLowRamDevice || activityManager.memoryClass <= 256),
                            "memory_class_mb" to activityManager.memoryClass,
                            "total_memory_mb" to (memoryInfo.totalMem / (1024L * 1024L)).toInt(),
                            "location_service_enabled" to (
                                locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) ||
                                locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
                            ),
                            "location_permission" to if (fineLocation) "GRANTED" else "DENIED",
                            "background_location_granted" to backgroundLocation,
                            "notification_permission_granted" to notificationGranted,
                            "battery_optimization_ignored" to powerManager.isIgnoringBatteryOptimizations(packageName),
                        )
                    )
                }
                else -> result.notImplemented()
            }
        }

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            downloadsChannel,
        ).setMethodCallHandler { call, result ->
            if (call.method != "saveFile") {
                result.notImplemented()
                return@setMethodCallHandler
            }
            val filename = call.argument<String>("filename")
            val mimeType = call.argument<String>("mimeType")
            val bytes = call.argument<ByteArray>("bytes")
            if (filename.isNullOrBlank() || mimeType.isNullOrBlank() || bytes == null) {
                result.error("INVALID_FILE", "Filename, MIME type and bytes are required.", null)
                return@setMethodCallHandler
            }
            try {
                result.success(saveToDownloads(filename, mimeType, bytes))
            } catch (error: Exception) {
                result.error("SAVE_FAILED", error.message ?: "Unable to save report.", null)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        referralCode(intent)?.let { code ->
            referralChannel?.invokeMethod("openReferral", code)
        }
    }

    private fun referralCode(sourceIntent: Intent?): String? {
        val uri = sourceIntent?.data ?: return null
        if (uri.scheme != "arismartro" || uri.host != "referral") return null
        return uri.getQueryParameter("code")?.trim()?.uppercase()?.takeIf { it.isNotBlank() }
    }

    private fun saveToDownloads(filename: String, mimeType: String, bytes: ByteArray): String {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, filename)
                put(MediaStore.Downloads.MIME_TYPE, mimeType)
                put(MediaStore.Downloads.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/ARI Smart RO Reports")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val resolver = contentResolver
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: throw IllegalStateException("Downloads file could not be created.")
            try {
                resolver.openOutputStream(uri)?.use { it.write(bytes) }
                    ?: throw IllegalStateException("Downloads file could not be opened.")
                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
            } catch (error: Exception) {
                resolver.delete(uri, null, null)
                throw error
            }
            return "Downloads/ARI Smart RO Reports/$filename"
        }

        val root = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
            ?: throw IllegalStateException("Downloads directory is unavailable.")
        val directory = File(root, "ARI Smart RO Reports").apply { mkdirs() }
        FileOutputStream(File(directory, filename)).use { it.write(bytes) }
        return File(directory, filename).absolutePath
    }
}
