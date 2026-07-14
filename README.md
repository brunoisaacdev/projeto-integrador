Projeto Integrador

Aplicacao Django para agendamentos da barbearia.

## Como rodar

No PowerShell, dentro da pasta do projeto:

```powershell
.\venv\Scripts\python.exe manage.py runserver
```

Depois acesse:

```text
http://127.0.0.1:8000/
```

Login administrativo cadastrado no banco atual:

```text
E-mail: admin@example.com
Senha: admin123
```

## Se o ambiente precisar ser recriado

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

O projeto le as variaveis de banco do arquivo `.env`.
