# Generated migration for WebRTC call improvements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('message', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='call',
            name='ringing_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='call',
            name='webrtc_offer',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='call',
            name='webrtc_answer',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='call',
            name='ice_candidates',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='call',
            name='is_answered',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='call',
            name='is_missed',
            field=models.BooleanField(default=False),
        ),
    ]
