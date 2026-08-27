from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="AndyConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, default="", max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="andy_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="AndyKnowledge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("namespace", models.CharField(default="ari-smart-ro", max_length=80)),
                ("source_path", models.CharField(blank=True, default="", max_length=500)),
                ("title", models.CharField(max_length=240)),
                ("content", models.TextField()),
                ("content_hash", models.CharField(db_index=True, max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="AndyMemory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=160)),
                ("value", models.TextField()),
                ("source", models.CharField(default="USER_CONFIRMED", max_length=32)),
                ("confidence", models.FloatField(default=1.0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="andy_memories", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AndyMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("USER", "User"), ("ASSISTANT", "Assistant"), ("SYSTEM", "System")], max_length=16)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="andy.andyconversation")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="AndyFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.SmallIntegerField(choices=[(1, "Bad"), (0, "Neutral"), (2, "Good")])),
                ("correction", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback", to="andy.andymessage")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="andy_feedback", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(model_name="andyknowledge", index=models.Index(fields=["namespace", "is_active"], name="andy_andykn_namespa_7cb6c4_idx")),
        migrations.AddIndex(model_name="andymemory", index=models.Index(fields=["user", "key", "is_active"], name="andy_andymem_user_id_d4580f_idx")),
    ]
