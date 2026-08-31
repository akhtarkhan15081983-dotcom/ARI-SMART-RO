package com.arismartro.smsgateway;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private EditText url, device, key;
    private TextView status;
    private SecureStore store;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        store = new SecureStore(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 64, 48, 32);
        TextView title = new TextView(this); title.setText("ARI Office SMS Gateway"); title.setTextSize(25); title.setTextColor(0xFF075A96); root.addView(title);
        TextView note = new TextView(this); note.setText("Dedicated office device only. Credentials are encrypted with Android Keystore."); note.setPadding(0, 12, 0, 30); root.addView(note);
        url = field("Backend API URL", store.get("base_url")); root.addView(url);
        device = field("Gateway Device ID", store.get("device_id")); root.addView(device);
        key = field("Gateway Secret Key", store.get("gateway_key")); key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); root.addView(key);
        Button save = new Button(this); save.setText("SAVE SECURE CONFIGURATION"); save.setOnClickListener(this::save); root.addView(save);
        Button permission = new Button(this); permission.setText("ALLOW INCOMING SMS"); permission.setOnClickListener(v -> requestSmsPermissions()); root.addView(permission);
        status = new TextView(this); status.setPadding(0, 28, 0, 0); refreshStatus(); root.addView(status);
        setContentView(root);
        if (!hasSmsPermissions()) requestSmsPermissions();
    }

    @Override protected void onResume() {
        super.onResume();
        if (status != null) refreshStatus();
        if (hasSmsPermissions()) {
            InboxRecovery.scanAsync(this);
            new Handler(Looper.getMainLooper()).postDelayed(this::refreshStatus, 2500);
        }
    }

    private boolean hasSmsPermissions() {
        return checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED
            && checkSelfPermission(Manifest.permission.READ_SMS) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestSmsPermissions() {
        requestPermissions(new String[]{Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS}, 10);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == 10 && hasSmsPermissions()) InboxRecovery.scanAsync(this);
    }

    private void refreshStatus() {
        status.setText("Last event: " + getSharedPreferences("gateway_status", MODE_PRIVATE).getString("last_event", "None"));
    }

    private EditText field(String hint, String value) {
        EditText field = new EditText(this); field.setHint(hint); field.setText(value); field.setSingleLine(true); field.setPadding(8, 18, 8, 18); return field;
    }

    private void save(View ignored) {
        try {
            GatewayClient.validateUrl(url.getText().toString().trim());
            if (device.getText().toString().trim().isEmpty() || key.getText().toString().trim().isEmpty()) throw new IllegalArgumentException("Device ID and key are required.");
            store.put("base_url", url.getText().toString().trim());
            store.put("device_id", device.getText().toString().trim());
            store.put("gateway_key", key.getText().toString().trim());
            Toast.makeText(this, "Gateway configuration saved securely.", Toast.LENGTH_LONG).show();
        } catch (Exception error) { Toast.makeText(this, error.getMessage(), Toast.LENGTH_LONG).show(); }
    }
}
