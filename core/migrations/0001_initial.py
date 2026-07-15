import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120, verbose_name='Nome completo')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='E-mail')),
                ('telefone', models.CharField(max_length=20, verbose_name='Telefone')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Cliente',
                'verbose_name_plural': 'Clientes',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Servico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120, verbose_name='Nome do serviço')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
                ('preco', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Preço (R$)')),
                ('duracao_minutos', models.PositiveIntegerField(default=30, verbose_name='Duração (minutos)')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Serviço',
                'verbose_name_plural': 'Serviços',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Profissional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120, verbose_name='Nome')),
                ('especialidade', models.CharField(blank=True, max_length=120, verbose_name='Especialidade')),
                ('telefone', models.CharField(blank=True, max_length=20, verbose_name='Telefone')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='E-mail')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('servicos', models.ManyToManyField(blank=True, related_name='profissionais', to='core.servico')),
            ],
            options={
                'verbose_name': 'Profissional',
                'verbose_name_plural': 'Profissionais',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='Agendamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateTimeField(verbose_name='Início')),
                ('status', models.CharField(choices=[('agendado', 'Agendado'), ('concluido', 'Concluído'), ('cancelado', 'Cancelado')], default='agendado', max_length=20)),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('cancelado_em', models.DateTimeField(blank=True, null=True, verbose_name='Cancelado em')),
                ('motivo_cancelamento', models.CharField(blank=True, max_length=255, verbose_name='Motivo do cancelamento')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='agendamentos', to='core.cliente')),
                ('profissional', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='agendamentos', to='core.profissional')),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='agendamentos', to='core.servico')),
            ],
            options={
                'verbose_name': 'Agendamento',
                'verbose_name_plural': 'Agendamentos',
                'ordering': ['-inicio'],
            },
        ),
    ]
