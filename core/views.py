from django.shortcuts import redirect, render
from django.http import HttpResponse
from core.models import Agenda

nomeLoja = "LigaSport"

def sobre(request):
    return render(request, 'core/sobre.html', {'nome_loja': nomeLoja})

def home(request):
    return render(request, 'core/home.html', {'nome_loja': nomeLoja})

def listar_eventos(request):
    if request.method == 'POST':
        descricao =  request.POST.get('descricao')
        print( descricao )

        Agenda.objects.create( descricao = descricao, dthr_evento = '2026-01-01 11:11:11')
        return redirect('listar_eventos')

    elif request.method == 'GET':
        listaEventos = Agenda.objects.all()
        return render(request, 'core/evento.html', {'eventos': listaEventos})