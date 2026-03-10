import streamlit as st
import hashlib
import smtplib
import secrets
import string
import re
import os
import time
import csv
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_validator import validate_email, EmailNotValidError

st.set_page_config(page_title="Cadastro de Senha", page_icon="🔐")

ARQUIVO_CONTROLE = "solicitacoes_senha.csv"

if "ultimo_envio" not in st.session_state:
    st.session_state["ultimo_envio"] = 0


# ---------- LIMPAR FORMULÁRIO ----------

def limpar_formulario():

    for campo in [
        "nome",
        "email",
        "cpf",
        "telefone",
        "senha",
        "senha_confirmacao"
    ]:

        if campo in st.session_state:
            del st.session_state[campo]


# ---------- FUNÇÕES ----------

def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def gerar_senha_segura(tamanho=12):

    caracteres = string.ascii_letters + string.digits + "@#$%&*!"

    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))


def validar_email(email):

    try:

        resultado = validate_email(email)

        return resultado.email

    except EmailNotValidError:

        return None


def validar_cpf(cpf):

    cpf = re.sub(r'[^0-9]', '', cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito = (soma * 10 % 11) % 10

    if digito != int(cpf[9]):
        return False

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito = (soma * 10 % 11) % 10

    return digito == int(cpf[10])


def avaliar_forca(senha):

    score = 0

    if len(senha) >= 8:
        score += 1

    if re.search("[A-Z]", senha):
        score += 1

    if re.search("[0-9]", senha):
        score += 1

    if re.search("[@#$%&*!]", senha):
        score += 1

    return score


# ---------- CONTROLE DUPLICIDADE ----------

def verificar_solicitacao_recente(email, cpf):

    if not os.path.exists(ARQUIVO_CONTROLE):
        return False

    limite = datetime.now() - timedelta(hours=24)

    with open(ARQUIVO_CONTROLE, newline="", encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            data = datetime.strptime(row["data"], "%Y-%m-%d %H:%M:%S")

            if data > limite:

                if row["email"] == email or row["cpf"] == cpf:
                    return True

    return False


def registrar_solicitacao(email, cpf):

    arquivo_existe = os.path.exists(ARQUIVO_CONTROLE)

    with open(ARQUIVO_CONTROLE, "a", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        if not arquivo_existe:
            writer.writerow(["email", "cpf", "data"])

        writer.writerow([email, cpf, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])


# ---------- ENVIO EMAIL ----------

def enviar_email(nome, email, cpf, telefone, hash_senha):

    remetente = os.getenv("EMAIL_REMETENTE")
    senha_email = os.getenv("EMAIL_SENHA_APP")
    destinatario = os.getenv("EMAIL_DESTINO")

    assunto = f"Novo cadastro de senha - {email}"

    linha_excel = f"{email},{hash_senha}"

    corpo_html = f"""
    <h2>Novo cadastro de senha</h2>

    Nome: {nome}<br>
    Email: {email}<br>
    CPF: {cpf}<br>
    Telefone: {telefone}<br><br>

    Hash da senha:<br>
    {hash_senha}

    <hr>

    Linha pronta para Excel:<br>
    {linha_excel}
    """

    msg = MIMEMultipart()

    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto

    msg.attach(MIMEText(corpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:

        servidor.login(remetente, senha_email)

        servidor.sendmail(remetente, destinatario, msg.as_string())


# ---------- INTERFACE ----------

st.title("🔐 Cadastro de Senha do Sistema")

st.write(
    "Preencha os dados abaixo para cadastrar sua senha. "
    "A senha será ativada em até 24 horas."
)

nome = st.text_input("Nome completo", key="nome")

email_usuario = st.text_input("E-mail", key="email")

cpf = st.text_input("CPF", key="cpf")

telefone = st.text_input("Telefone", key="telefone")

senha = st.text_input("Senha", type="password", key="senha")

senha_confirmacao = st.text_input("Confirmar senha", type="password", key="senha_confirmacao")


if st.button("Gerar senha segura"):

    senha_gerada = gerar_senha_segura()

    st.code(senha_gerada)

    st.info("Copie a senha gerada.")


if senha:

    score = avaliar_forca(senha)

    st.progress(score / 4)

    if score <= 1:
        st.error("Senha fraca")

    elif score == 2:
        st.warning("Senha média")

    else:
        st.success("Senha forte")


# ---------- VALIDAÇÕES ----------

erros = []

email_normalizado = validar_email(email_usuario)

if not nome:
    erros.append("Nome não informado")

if not email_usuario:
    erros.append("E-mail não informado")

elif email_normalizado is None:
    erros.append("E-mail inválido")

if not cpf:
    erros.append("CPF não informado")

elif not validar_cpf(cpf):
    erros.append("CPF inválido")

if not telefone:
    erros.append("Telefone não informado")

if not senha:
    erros.append("Senha não informada")

elif len(senha) < 8:
    erros.append("A senha deve ter pelo menos 8 caracteres")

if senha != senha_confirmacao:
    erros.append("As senhas não coincidem")


if erros:

    st.warning("Corrija os seguintes problemas:")

    for e in erros:
        st.write("•", e)

else:

    if st.button("Cadastrar senha"):

        if verificar_solicitacao_recente(email_normalizado, cpf):

            st.error("Já existe uma solicitação recente para este usuário. Aguarde 24 horas.")

        else:

            agora = time.time()

            if agora - st.session_state["ultimo_envio"] < 120:

                st.error("Aguarde 2 minutos antes de enviar outra solicitação.")

            else:

                hash_senha = gerar_hash(senha)

                try:

                    enviar_email(nome, email_normalizado, cpf, telefone, hash_senha)

                    registrar_solicitacao(email_normalizado, cpf)

                    st.session_state["ultimo_envio"] = agora

                    st.success("Senha cadastrada com sucesso.")

                    st.info(
                        "Sua senha será ativada em até **24 horas**, "
                        "após validação e registro no sistema."
                    )

                    limpar_formulario()

                    st.rerun()

                except Exception as e:

                    st.error(f"Erro ao enviar email: {e}")
