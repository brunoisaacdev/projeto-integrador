import datetime
from django.db import migrations, models


def criar_horarios_padrao(apps, schema_editor):
    HorarioFuncionamento = apps.get_model("core", "HorarioFuncionamento")
    for dia_semana in range(7):
        HorarioFuncionamento.objects.get_or_create(
            dia_semana=dia_semana,
            defaults={
                "aberto": True,
                "hora_abertura": datetime.time(9, 0),
                "hora_fechamento": datetime.time(19, 0),
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_profissional_foto'),
    ]

    operations = [
        migrations.CreateModel(
            name='HorarioFuncionamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia_semana', models.PositiveSmallIntegerField(choices=[(0, 'Segunda-feira'), (1, 'Terça-feira'), (2, 'Quarta-feira'), (3, 'Quinta-feira'), (4, 'Sexta-feira'), (5, 'Sábado'), (6, 'Domingo')], unique=True, verbose_name='Dia da semana')),
                ('aberto', models.BooleanField(default=True, verbose_name='Atende neste dia')),
                ('hora_abertura', models.TimeField(default=datetime.time(9, 0), verbose_name='Abertura')),
                ('hora_fechamento', models.TimeField(default=datetime.time(19, 0), verbose_name='Fechamento')),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Horário de funcionamento',
                'verbose_name_plural': 'Horários de funcionamento',
                'ordering': ['dia_semana'],
            },
        ),
        migrations.RunPython(criar_horarios_padrao, migrations.RunPython.noop),
    ]
