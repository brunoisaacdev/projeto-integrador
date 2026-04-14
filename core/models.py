from django.db import models

# Create your models here.
class Agenda(models.Model):
    descricao = models.CharField(max_length=100)
    dthr_evento = models.DateTimeField()
    responsavel = models.CharField(max_length=100)
    duracao = models.IntegerField(default=1)
    criado_em = models.DateTimeField(auto_now=True)