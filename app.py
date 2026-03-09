import streamlit as st
import hashlib
import smtplib
import secrets
import string
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

st.set_page_config(page_title="Cadastro de Senha", page_icon="🔐")

st.title("🔐 Cadastro de Senha do Sistema")

st.write(
    "Crie sua senha para acesso ao sistema. "
    "Após o cadastro, a senha será ativada em até 24 horas."
)

usuario = st.text_input("Usuário")

senha = st.text_input("Senha", type="password")

senha_confirmacao = st.text_input("Confirmar senha", type="password")


# -------- HASH --------
def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


# -------- GERADOR DE SENHA --------
def gerar_senha_segura(tamanho=12):

    caracteres = (
        string.ascii_letters +
        string.digits +
        "@#$%&*!"
    )

    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))


if st.button("Gerar senha segura automaticamente"):
    senha_gerada = gerar_senha_segura()
    st.code(senha_gerada)
    st.info("Copie a senha gerada e utilize no campo acima.")


# -------- FORÇA DA SENHA --------
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


if senha:

    score = avaliar_forca(senha)

    st.progress(score / 4)

    if score <= 1:
        st.error("Senha fraca")

    elif score == 2:
        st.warning("Senha média")

    else:
        st.success("Senha forte")


# -------- ENVIO DE EMAIL --------
def enviar_email(usuario, hash_senha):

    remetente = os.getenv("EMAIL_REMETENTE")
    senha_email = os.getenv("EMAIL_SENHA_APP")
    destinatario = os.getenv("EMAIL_DESTINO")

    assunto = "Novo cadastro de senha"

    corpo_html = f"""
    <h2>Novo cadastro de senha</h2>

    <p><b>Usuário:</b> {usuario}</p>

    <p><b>Hash da senha:</b></p>

    <p style="font-family:monospace">{hash_senha}</p>

    <hr>

    <p>Registrar este hash na base de dados do sistema.</p>
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


# -------- BOTÃO FINAL --------
if st.button("Cadastrar senha"):

    if not usuario:

        st.error("Informe o usuário")

    elif senha != senha_confirmacao:

        st.error("As senhas não coincidem")

    elif len(senha) < 8:

        st.error("A senha deve ter pelo menos 8 caracteres")

    else:

        hash_senha = gerar_hash(senha)

        try:

            enviar_email(usuario, hash_senha)

            st.success("Senha cadastrada com sucesso.")

            st.info(
                "Sua senha será ativada em até **24 horas**, "
                "após validação e registro no sistema."
                "Em caso de dúvidas, entre em contato com luciano.reis@saude.ba.gov.br."
            )

        except Exception as e:

            st.error(f"Erro ao enviar email: {e}")
