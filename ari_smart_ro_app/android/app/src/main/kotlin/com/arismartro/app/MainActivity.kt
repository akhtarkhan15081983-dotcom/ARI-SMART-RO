package com.arismartro.app

import android.content.ContentValues
import android.content.Intent
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
    private val referralChannelName = "com.arismartro.app/referral"
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
