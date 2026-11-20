"""Configuração do robô. Tudo o que é segredo ou muda por ambiente vem do arquivo
.env (que fica fora do repositório). Nenhuma chave ou senha é escrita no código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(RAIZ / ".env")
except ImportError:  # python-dotenv é opcional: sem ele, valem as variáveis de ambiente
    pass


def _numero(nome: str, padrao: float) -> float:
    try:
        return float(os.getenv(nome, padrao))
    except ValueError:
        return padrao


@dataclass
class Config:
    # Pastas de trabalho (o robô cria as que faltarem)
    base: Path = RAIZ
    # IA
    limiar_confianca: float = _numero("ZELA_LIMIAR_CONFIANCA", 0.50)
    tamanho_minimo_relato: int = 15
    # Previsão do tempo (Open-Meteo: API pública, gratuita e sem chave)
    clima_ativo: bool = os.getenv("ZELA_CLIMA", "1") != "0"
    clima_url: str = os.getenv("ZELA_CLIMA_URL", "https://api.open-meteo.com/v1/forecast")
    clima_latitude: float = _numero("ZELA_LATITUDE", -23.55)
    clima_longitude: float = _numero("ZELA_LONGITUDE", -46.63)
    clima_chuva_forte_mm: float = _numero("ZELA_CHUVA_FORTE_MM", 20)
    clima_timeout: float = _numero("ZELA_CLIMA_TIMEOUT", 5)
    clima_tentativas: int = 3
    clima_espera: float = _numero("ZELA_CLIMA_ESPERA", 1.0)  # segundos; dobra a cada tentativa
    # E-mail: "arquivo" grava .eml em saida/ (padrão, não precisa de senha); "smtp" envia
    email_modo: str = os.getenv("ZELA_EMAIL_MODO", "arquivo").lower()
    smtp_host: str = os.getenv("ZELA_SMTP_HOST", "smtp.gmail.com")
    smtp_porta: int = int(_numero("ZELA_SMTP_PORTA", 587))
    smtp_usuario: str = os.getenv("ZELA_SMTP_USUARIO", "")
    smtp_senha: str = os.getenv("ZELA_SMTP_SENHA", "")
    # Em testes com SMTP real, todos os e-mails vão para este endereço (os órgãos são fictícios)
    email_destino_teste: str = os.getenv("ZELA_EMAIL_DESTINO_TESTE", "")
    smtp_tentativas: int = 3
    smtp_espera: float = 2.0
    # Agendamento
    intervalo_minutos: int = int(_numero("ZELA_INTERVALO_MIN", 15))
    # Observabilidade
    disco_minimo_mb: int = 100

    @property
    def entrada(self) -> Path: return self.base / "entrada"
    @property
    def processados(self) -> Path: return self.base / "processados"
    @property
    def quarentena(self) -> Path: return self.base / "quarentena"
    @property
    def saida(self) -> Path: return self.base / "saida"
    @property
    def logs(self) -> Path: return self.base / "logs"
    @property
    def estado_db(self) -> Path: return self.base / "saida" / "estado.db"
    @property
    def modelo(self) -> Path: return self.base / "modelos" / "triagem.joblib"
    @property
    def trava(self) -> Path: return self.base / "saida" / "robo.lock"
    # Dados que acompanham o repositório (não mudam com `base`)
    treino: Path = RAIZ / "dados" / "treino.csv"
    exemplos: Path = RAIZ / "dados" / "exemplos"

    def criar_pastas(self) -> None:
        for pasta in (self.entrada, self.processados, self.quarentena, self.saida,
                      self.logs, self.modelo.parent):
            pasta.mkdir(parents=True, exist_ok=True)
