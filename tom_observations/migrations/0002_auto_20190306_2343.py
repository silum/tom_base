# Generated by Django 2.1.5 on 2019-03-06 23:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tom_observations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='observationrecord',
            name='scheduled_end',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='observationrecord',
            name='scheduled_start',
            field=models.DateTimeField(null=True),
        ),
    ]
