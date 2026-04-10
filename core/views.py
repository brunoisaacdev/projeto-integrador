from django.shortcuts import redirect, render
from django.http import HttpResponse

nomeLoja = "LigaSport"
chamados = [{'descricao': 'Não consigo acessar minha conta', 'status': 'Aberto'},
            {'descricao': 'Produto com defeito', 'status': 'Fechado'},
            {'descricao': 'Dúvida sobre o produto', 'status': 'Em andamento'}]

def sobre(request):
    return render(request, 'core/sobre.html', {'nome_loja': nomeLoja})

def home(request):
    return render(request, 'core/home.html', {'nome_loja': nomeLoja})

def abrir_chamado(request):
    if request.method == 'POST':
        descricao =  request.POST.get('descricao')
        print( descricao )
        chamados.append(
            {
                'descricao': descricao,
                'status': 'Aberto'
            }
        )
        return redirect('abrir_chamado')

    elif request.method == 'GET':
        return render(request, 'core/abrir_chamado.html', {'chamados': chamados})