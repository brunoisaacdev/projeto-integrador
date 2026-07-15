import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_cliente_usuario'),
    ]

    operations = [
        migrations.AddField(
            model_name='profissional',
            name='foto',
            field=models.FileField(blank=True, upload_to='profissionais/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])], verbose_name='Foto'),
        ),
    ]
