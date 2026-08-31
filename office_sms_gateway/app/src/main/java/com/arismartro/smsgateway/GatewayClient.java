package com.arismartro.smsgateway;

import android.content.Context;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

final class GatewayClient {
    static void forward(Context context, String sender, String message) throws Exception {
        SecureStore store = new SecureStore(context);
        String baseUrl = store.get("base_url");
        String deviceId = store.get("device_id");
        String key = store.get("gateway_key");
        if (baseUrl.isEmpty() || deviceId.isEmpty() || key.isEmpty()) throw new IllegalStateException("Gateway is not configured.");
        validateUrl(baseUrl);
        URL url = new URL(trimSlash(baseUrl) + "/auth/sms-gateway/ingest/");
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(15000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json");
        connection.setRequestProperty("X-ARI-Gateway-ID", deviceId);
        connection.setRequestProperty("X-ARI-Gateway-Key", key);
        connection.setRequestProperty("X-ARI-Nonce", UUID.randomUUID().toString().replace("-", ""));
        connection.setRequestProperty("X-ARI-Timestamp", String.valueOf(System.currentTimeMillis() / 1000));
        String json = "{\"sender_phone\":\"" + escape(sender) + "\",\"message\":\"" + escape(message) + "\"}";
        try (OutputStream output = connection.getOutputStream()) { output.write(json.getBytes(StandardCharsets.UTF_8)); }
        int status = connection.getResponseCode();
        connection.disconnect();
        if (status < 200 || status >= 300) throw new IllegalStateException("Backend rejected SMS: HTTP " + status);
    }

    static void validateUrl(String value) {
        if (value.startsWith("https://")) return;
        if (value.matches("http://(10\\.|192\\.168\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.).+")) return;
        throw new IllegalArgumentException("Use HTTPS, or a private LAN URL during pilot testing.");
    }

    private static String trimSlash(String value) { return value.endsWith("/") ? value.substring(0, value.length() - 1) : value; }
    private static String escape(String value) { return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", ""); }
}
