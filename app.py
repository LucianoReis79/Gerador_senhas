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
                    st.info("Sua senha será ativada em até 24 horas.")

                except Exception as e:

                    st.error(f"Erro ao enviar email: {e}")
