from django.db import migrations, models
import transparency.models


class Migration(migrations.Migration):

    dependencies = [
        ('transparency', '0003_ngoreport'),
    ]

    operations = [
        migrations.AddField(
            model_name='ngodocument',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to=transparency.models.ngo_document_upload_path),
        ),
        migrations.AddField(
            model_name='ngodocument',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='ngodocument',
            name='document_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
