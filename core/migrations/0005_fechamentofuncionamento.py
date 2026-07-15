from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_horariofuncionamento'),
    ]

    operations = [
        migrations.CreateModel(
            name='FechamentoFuncionamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(unique=True, verbose_name='Data')),
                ('motivo', models.CharField(blank=True, default='Feriado', max_length=120, verbose_name='Motivo')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Fechamento de funcionamento',
                'verbose_name_plural': 'Fechamentos de funcionamento',
                'ordering': ['data'],
            },
        ),
    ]
