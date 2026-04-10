# 📘 Aula 09 — Django (SENAC 2026)

Repositório da **Aula 09** da disciplina no SENAC - Programação com Python (2026), com foco em introdução ao desenvolvimento web utilizando **Django**.

```bash
git clone git@github.com:rmichel-dev/aula-09.git
```

---

## 🚀 Objetivo

Este projeto foi desenvolvido em aula com o objetivo de apresentar os fundamentos do ecossistema Django, incluindo:

- Criação de ambiente virtual
- Estrutura de projetos Django
- Criação de apps
- Execução do servidor local

---

## 💻 Sistema Operacional

Este guia foi preparado para **Windows (PowerShell)**.

---

## ⚙️ Pré-requisitos

Antes de iniciar, verifique se o Python está instalado:

```powershell
python --version
```

Caso encontre restrições no PowerShell, execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

> ⚠️ O Windows Defender pode bloquear scripts dependendo da configuração de segurança ("Controle Inteligente de Aplicativos").

---

## 🧪 1. Criar Ambiente Virtual

```powershell
python -m venv venv
```

Será criada a pasta `venv`, isolando as dependências do projeto.

---

## ▶️ 2. Ativar Ambiente Virtual

No **PowerShell**:

```powershell
.\venv\Scripts\activate
```

Se ativado corretamente, aparecerá:

```
(venv)
```

### ❗ Possíveis problemas

Se houver erro de execução de script:

- Use o **Prompt de Comando (CMD)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
- Ou ajuste a política de execução (passo anterior)

---

## 📦 3. Instalar o Django

```powershell
pip install django
```

Verifique a instalação:

```powershell
django-admin --version
```

---

## 🏗️ 4. Criar Projeto Django

```powershell
django-admin startproject setup .
```

> O `.` evita a criação de uma pasta adicional, mantendo a estrutura mais limpa.

---

## 📁 5. Criar App Principal

```powershell
python manage.py startapp core
```

---

## 🌐 6. Executar o Servidor

```powershell
python manage.py runserver
```

Acesse no navegador:

```
http://127.0.0.1:8000/
```

---

## 🛑 Encerrar o Servidor

```
Ctrl + C
```

---

## 🔚 Sair do Ambiente Virtual

```powershell
deactivate
```

---

## 🔄 Gerar Migrações

```powershell
python manage.py makemigrations
```

## 🧱 Aplicar Migrações

```powershell
python manage.py migrate
```

---

## 👤 Criar Superusuário

```powershell
python manage.py createsuperuser
```

Esse usuário permitirá acesso ao painel administrativo do Django.

---

# 📝 Instruções para Criar um Formulário

Siga os passos abaixo para implementar um formulário no projeto:

## 1. Criar o formulário
- Crie o arquivo `.html` do formulário na pasta apropriada do projeto.

## 2. Definir a lógica
- No arquivo `views.py` do app em que você está trabalhando, implemente a lógica necessária para processar o formulário.

## 3. Definir a rota
- Configure a rota no arquivo `setup/urls.py`, garantindo que o formulário esteja acessível pela URL correta.