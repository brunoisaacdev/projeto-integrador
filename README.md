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

## Recuperacao de senha por e-mail

O fluxo de recuperacao esta em:

```text
http://127.0.0.1:8000/senha/esqueci/
```

Em desenvolvimento, se nenhuma configuracao SMTP for informada, o Django mostra o e-mail de recuperacao no terminal do `runserver`.

Para enviar e-mails de verdade, adicione ao `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seu-provedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-usuario-smtp
EMAIL_HOST_PASSWORD=sua-senha-smtp
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=Premium Barbearia <no-reply@seudominio.com>
```

Observacao: este projeto usa o Supabase como banco Postgres, mas o login e a senha sao do Django. O e-mail nativo de recuperacao do Supabase Auth so funciona para usuarios cadastrados no Supabase Auth (`auth.users`). Para este projeto, use SMTP no Django ou migre a autenticacao inteira para Supabase Auth.
