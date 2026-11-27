
import os
import json
import time
import requests
import schedule
from dotenv import load_dotenv

load_dotenv(override=True)

API_KEY = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARQUIVO = "vagas_enviadas.json"
PONTUACAO_MINIMA = 50

TECNOLOGIAS = [
    "python", "javascript", "typescript",
    "react", "node.js", "next.js",
    "sql", "postgresql", "mysql",
    "aws", "git", "prisma", "mongodb"
]


# Busca vagas na API JSearch
def buscar_vagas():
    url = f"https://{API_HOST}/search-v2"

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }

    params = {
        "query": "Desenvolvedor Junior Brasil",
        "country": "br",
        "num_pages": 1
    }

    try:
        resposta = requests.get(
            url, headers=headers, params=params, timeout=30
        )
        resposta.raise_for_status()
        return resposta.json()["data"]["jobs"]

    except (requests.exceptions.RequestException,
            KeyError, TypeError, ValueError):
        print("Erro ao buscar vagas.")
        return []


# Calcula a compatibilidade da vaga
def avaliar_vaga(vaga):
    titulo = (vaga.get("job_title") or "").lower()
    descricao = (vaga.get("job_description") or "").lower()
    cidade = (vaga.get("job_city") or "").lower()
    remoto = vaga.get("job_is_remote")

    pontos = 0

    if any(nivel in titulo for nivel in [
        "senior", "sênior", "pleno", "especialista"
    ]):
        return 0, []

    if not remoto and cidade != "pelotas":
        return 0, []

    encontradas = [
        tech for tech in TECNOLOGIAS
        if tech in descricao
    ]

    pontos += min(len(encontradas) * 10, 50)

    if any(nivel in titulo for nivel in [
        "junior", "júnior", "estágio", "estagio", "trainee"
    ]):
        pontos += 30

    if remoto or cidade == "pelotas":
        pontos += 20

    return pontos, encontradas


# Envia mensagem ao Telegram
def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    dados = {
        "chat_id": CHAT_ID,
        "text": mensagem
    }

    try:
        resposta = requests.post(url, json=dados, timeout=15)
        resposta.raise_for_status()
        print("Mensagem enviada com sucesso!")
        return True

    except requests.exceptions.RequestException:
        print("Erro ao enviar mensagem ao Telegram.")
        return False


# Carrega o historico de vagas enviadas
def carregar_historico():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    return []


# Salva o historico no arquivo JSON
def salvar_historico(historico):
    with open(ARQUIVO, "w", encoding="utf-8") as arquivo:
        json.dump(historico, arquivo, indent=4)


# Funcao principal
def main():
    print("\nIniciando busca de vagas...")

    vagas = buscar_vagas()
    historico = carregar_historico()
    aprovadas = []

    print(f"Vagas encontradas: {len(vagas)}")

    for vaga in vagas:
        vaga_id = vaga.get("job_id")

        if not vaga_id or vaga_id in historico:
            continue

        pontos, tecnologias = avaliar_vaga(vaga)

        if pontos >= PONTUACAO_MINIMA:
            aprovadas.append((vaga, pontos, tecnologias))

    aprovadas.sort(key=lambda item: item[1], reverse=True)

    print(f"Novas vagas aprovadas: {len(aprovadas)}")

    for vaga, pontos, tecnologias in aprovadas[:5]:
        vaga_id = vaga.get("job_id")

        if vaga_id in historico:
            continue

        mensagem = (
            f"🚀 Nova oportunidade!\n\n"
            f"💼 Cargo: {vaga.get('job_title')}\n"
            f"🏢 Empresa: {vaga.get('employer_name')}\n"
            f"📍 Cidade: {vaga.get('job_city')}\n"
            f"🏠 Remoto: {'Sim' if vaga.get('job_is_remote') else 'Não'}\n\n"
            f"🎯 Compatibilidade: {pontos}%\n"
            f"💻 Tecnologias: {', '.join(tecnologias) or 'Não identificadas'}\n\n"
            f"🔗 {vaga.get('job_apply_link')}"
        )

        if enviar_telegram(mensagem):
            historico.append(vaga_id)
            salvar_historico(historico)

    print("Busca finalizada!")


if __name__ == "__main__":
    main()

    schedule.every(12).hours.do(main)

    print("JobRadar ativo!")
    print("Pressione CTRL+C para encerrar.")

    while True:
        schedule.run_pending()
        time.sleep(1)
