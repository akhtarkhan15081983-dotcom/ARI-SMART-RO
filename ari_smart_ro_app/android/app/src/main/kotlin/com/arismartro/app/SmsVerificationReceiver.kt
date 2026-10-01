package com.arismartro.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

class SmsVerificationReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) return

        val sender = messages.firstOrNull()?.displayOriginatingAddress.orEmpty()
        val body = messages.joinToString(separator = "") { it.messageBody.orEmpty() }.trim()
        if (!body.uppercase().startsWith("ARI VERIFY ")) return

        val preferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val gatewayId = preferences.getString(KEY_GATEWAY_ID, null).orEmpty()
        val gatewayKey = preferences.getString(KEY_GATEWAY_KEY, null).orEmpty()
        val baseUrl = preferences.getString(KEY_BASE_URL, null).orEmpty().trimEnd('/')
        if (gatewayId.isBlank() || gatewayKey.isBlank() || baseUrl.isBlank()) return

        val pending = goAsync()
        Thread {
            try {
                submitSms(
                    baseUrl = baseUrl,
                    gatewayId = gatewayId,
                    gatewayKey = gatewayKey,
                    sender = sender,
                    body = body,
                )
            } finally {
                pending.finish()
            }
        }.start()
    }

    private fun submitSms(
        baseUrl: String,
        gatewayId: String,
        gatewayKey: String,
        sender: String,
        body: String,
    ) {
        val connection = (URL("$baseUrl/auth/sms-gateway/ingest/").openConnection() as HttpURLConnection)
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 15000
            connection.readTimeout = 15000
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("X-ARI-Gateway-ID", gatewayId)
            connection.setRequestProperty("X-ARI-Gateway-Key", gatewayKey)
            connection.setRequestProperty("X-ARI-Nonce", UUID.randomUUID().toString().replace("-", ""))
            connection.setRequestProperty("X-ARI-Timestamp", (System.currentTimeMillis() / 1000L).toString())

            val payload = JSONObject()
                .put("sender_phone", sender)
                .put("message", body)
                .toString()
            connection.outputStream.use { output ->
                output.write(payload.toByteArray(Charsets.UTF_8))
            }
            connection.responseCode
        } catch (_: Exception) {
            // The customer app keeps polling. A temporarily failed submit can be
            // retried by sending the verification SMS again from the same SIM.
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        const val PREFS_NAME = "ari_sms_gateway"
        const val KEY_GATEWAY_ID = "gateway_id"
        const val KEY_GATEWAY_KEY = "gateway_key"
        const val KEY_BASE_URL = "base_url"
    }
}
