package com.arismartro.smsgateway;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.telephony.SmsMessage;
import android.provider.Telephony;

public class SmsReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (!"android.provider.Telephony.SMS_RECEIVED".equals(intent.getAction())) return;
        GatewayLog.record(context, "Incoming SMS broadcast received");
        SmsMessage[] messages = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (messages == null || messages.length == 0) {
            GatewayLog.record(context, "Incoming SMS could not be decoded");
            return;
        }
        String sender = "";
        StringBuilder body = new StringBuilder();
        for (SmsMessage sms : messages) {
            if (sms == null) continue;
            if (sender.isEmpty()) sender = sms.getOriginatingAddress();
            body.append(sms.getMessageBody());
        }
        if (!body.toString().trim().toUpperCase().startsWith("ARI VERIFY ")) {
            GatewayLog.record(context, "Non-ARI SMS ignored securely");
            return;
        }
        PendingResult pending = goAsync();
        final String finalSender = sender;
        final String finalBody = body.toString();
        new Thread(() -> {
            try {
                GatewayClient.forward(context.getApplicationContext(), finalSender, finalBody);
                GatewayLog.record(context, "Verification SMS forwarded successfully");
            } catch (Exception error) {
                GatewayLog.record(context, "Forward failed: " + error.getMessage());
            } finally { pending.finish(); }
        }).start();
    }
}
