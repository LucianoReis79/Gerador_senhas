import streamlit as st
import hashlib
import smtplib
import secrets
import string
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import time
import csv
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError


st.set_page_config(page_title="Cadastro de Senha", page_icon="🔐")

ARQUIVO_CONTROLE = "solicitacoes_senha.csv"

# ---------- CONTROLE ANTI-SPAM ----------
if "ultimo_envio" not in st.session_state:
    st.session_state["ultimo_envio"] = 0


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


def enviar_email(nome, email, cpf, telefone, hash_senha):

    remetente = os.getenv("EMAIL_REMETENTE")
    senha_email = os.getenv("EMAIL_SENHA_APP")
    destinatario = os.getenv("EMAIL_DESTINO")

    assunto = f"Novo cadastro de senha - {email}"

    linha_excel = f"{email},{hash_senha}"

    corpo_html = f"""
    <h2>Novo cadastro de senha</h2>

    <b>Nome:</b> {nome}<br>
    <b>Email:</b> {email}<br>
    <b>CPF:</b> {cpf}<br>
    <b>Telefone:</b> {telefone}<br><br>

    <b>Hash da senha:</b>

    <p style="font-family:monospace">{hash_senha}</p>

    <hr>

    <b>Linha pronta para Excel:</b>

    <p style="font-family:monospace">{linha_excel}</p>
    """

    msg = MIMEMultipart()

    msg["From"] = remetente
    msg["To"] = destinatario
    msg["Subject"] = assunto

    msg.attach(MIMEText(corpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:

        servidor.login(remetente, senha_email)

        servidor.sendmail(
            remetente,
            destinatario,
            msg.as_string()
        )


# ---------- INTERFACE ----------

st.title("🔐 Cadastro de Senha do Sistema")

st.write(
    "Preencha os dados abaixo para cadastrar sua senha. "
    "A senha será ativada em até 24 horas."
)

nome = st.text_input("Nome completo")

email_usuario = st.text_input("E-mail")

cpf = st.text_input("CPF (somente números ou formatado)")

telefone = st.text_input("Telefone")

senha = st.text_input("Senha", type="password")

senha_confirmacao = st.text_input("Confirmar senha", type="password")

bot_check = st.text_input("Deixe este campo vazio", label_visibility="collapsed")

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


email_normalizado = validar_email(email_usuario)

cpf_valido = validar_cpf(cpf) if cpf else False

senha_ok = senha and senha_confirmacao and senha == senha_confirmacao

campos_ok = all([nome, email_usuario, cpf, telefone, senha, senha_confirmacao])

formulario_valido = all([
    campos_ok,
    email_normalizado is not None,
    cpf_valido,
    senha_ok
])


if formulario_valido:

    if st.button("Cadastrar senha"):

        if bot_check:
            st.error("Solicitação inválida.")
            st.stop()

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

                except Exception as e:

                    st.error(f"Erro ao enviar email: {e}")

else:

    st.warning("Preencha corretamente todos os campos para habilitar o cadastro.")
