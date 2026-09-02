# google_mlkit_text_recognition references optional script-specific recognizers.
# ARI SMART RO uses the default Latin recognizer; these optional classes are
# intentionally not bundled. Suppress R8 missing-class warnings for them.
-dontwarn com.google.mlkit.vision.text.chinese.**
-dontwarn com.google.mlkit.vision.text.devanagari.**
-dontwarn com.google.mlkit.vision.text.japanese.**
-dontwarn com.google.mlkit.vision.text.korean.**
