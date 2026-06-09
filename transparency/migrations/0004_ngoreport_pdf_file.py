from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transparency', '0003_ngoreport'),
    ]

    operations = [
        migrations.AddField(
            model_name='ngoreport',
            name='pdf_file',
            field=models.FileField(blank=True, null=True, upload_to='ngo_reports/%Y/%m/'),
        ),
    ]
