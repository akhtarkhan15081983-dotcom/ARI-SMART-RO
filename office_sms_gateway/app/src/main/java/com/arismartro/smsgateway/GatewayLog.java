package com.arismartro.smsgateway;

import android.content.Context;

final class GatewayLog {
    static void record(Context context, String message) {
        context.getSharedPreferences("gateway_status", Context.MODE_PRIVATE).edit()
            .putString("last_event", System.currentTimeMillis() + " — " + message).apply();
    }
}
