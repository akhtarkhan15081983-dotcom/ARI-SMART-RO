package com.arismartro.smsgateway;

import android.content.Context;
import android.database.Cursor;
import android.net.Uri;
import java.util.concurrent.atomic.AtomicBoolean;

final class InboxRecovery {
    private static final AtomicBoolean RUNNING = new AtomicBoolean(false);

    static void scanAsync(Context context) {
        if (!RUNNING.compareAndSet(false, true)) return;
        Context app = context.getApplicationContext();
        new Thread(() -> {
            try { scan(app); }
            catch (Exception error) { GatewayLog.record(app, "Inbox check failed: " + error.getMessage()); }
            finally { RUNNING.set(false); }
        }).start();
    }

    private static void scan(Context context) throws Exception {
        String[] columns = {"_id", "address", "body", "date"};
        try (Cursor cursor = context.getContentResolver().query(
                Uri.parse("content://sms/inbox"), columns, null, null, "date DESC")) {
            if (cursor == null) throw new IllegalStateException("SMS inbox is unavailable");
            String lastId = context.getSharedPreferences("gateway_status", Context.MODE_PRIVATE)
                .getString("last_processed_sms_id", "");
            int visibleCount = 0;
            while (cursor.moveToNext()) {
                visibleCount++;
                String id = cursor.getString(0);
                String sender = cursor.getString(1);
                String body = cursor.getString(2);
                String normalized = body == null ? "" : body.trim().toUpperCase()
                    .replaceAll("\\s+", " ");
                if (id.equals(lastId) || !normalized.contains("ARI") ||
                    !normalized.contains("VERIFY")) continue;
                GatewayClient.forward(context, sender == null ? "" : sender, body);
                context.getSharedPreferences("gateway_status", Context.MODE_PRIVATE).edit()
                    .putString("last_processed_sms_id", id).apply();
                GatewayLog.record(context, "Verification SMS recovered and forwarded successfully");
                return;
            }
            GatewayLog.record(context, "Inbox checked (" + visibleCount +
                " visible) — no new ARI verification SMS");
        }
    }
}
