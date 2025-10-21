"""Application module moved into src package."""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import pandas as pd
import io
import time
import os
from datetime import datetime
import sys
import os

# Import do módulo de database: quando o pacote `src` é usado como pacote, preferimos
# import relativo; quando o arquivo é executado diretamente como script (python src/app.py)
# a importação relativa falha. Tentamos o relativo e recuamos para um import absoluto.
try:
    from .database import CNPJDatabase
except Exception:
    try:
        # Tentativa de import absoluto via pacote nomeado
        from src.database import CNPJDatabase
    except Exception:
        # Último recurso: ajustar sys.path para permitir import a partir da raiz do repositório
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from src.database import CNPJDatabase
import threading
from functools import wraps
import json
import logging
import traceback

# (content copied from root app.py; kept identical for now)

class CNPJApp:
    """
    Backend Flask para o Sistema de Análise de Dados CNPJ
    Provides APIs for filtering and exporting CNPJ data
    """

    def __init__(self, db_path="data/cnpj_database.db"):
        # Registrar a pasta web como pasta estática para servir index.html, JS, CSS diretamente
        web_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web'))
        self.app = Flask(__name__, static_folder=web_dir, static_url_path='')
        CORS(self.app)  # Permitir requisições do frontend
        # Configurar logging para gravar erros no arquivo server.err
        log_handler = logging.FileHandler('server.err', encoding='utf-8')
        log_handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        log_handler.setFormatter(formatter)
        # Adiciona também ao logger do Flask
        self.app.logger.addHandler(log_handler)
        logging.getLogger().addHandler(log_handler)
        self.db_path = db_path
        self.db = CNPJDatabase(db_path)

        # Configurar rotas
        self.setup_routes()

    def setup_routes(self):
        app = self.app

        @app.route('/')
        def index():
            # Serve o index.html da pasta web (via static_folder)
            try:
                return self.app.send_static_file('index.html')
            except Exception:
                self.app.logger.exception('Erro ao enviar index.html')
            return jsonify({'message': 'CNPJ Analyzer backend. Frontend não encontrado.'}), 200

        @app.route('/favicon.ico')
        def favicon():
            try:
                return self.app.send_static_file('favicon.ico')
            except Exception:
                return ('', 204)

        @app.route('/health')
        def health():
            ok = False
            try:
                ok = os.path.exists(self.db_path)
            except Exception:
                ok = False
            return jsonify({'status': 'ok' if ok else 'no-db', 'db_path': self.db_path}), 200

        @app.errorhandler(Exception)
        def handle_exception(e):
            # Log full traceback and return 500 json
            tb = traceback.format_exc()
            self.app.logger.error(tb)
            return jsonify({'error': 'internal_server_error'}), 500


def create_app(db_path="data/cnpj_database.db"):
    """Factory helper para criar a aplicação Flask (útil para testes e WSGI)."""
    return CNPJApp(db_path).app


if __name__ == "__main__":
    # Permitir execução direta: python src\app.py
    db_path = os.environ.get("CNPJ_DB", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cnpj_database.db"))
    app_obj = CNPJApp(db_path=db_path)
    # Rodar servidor de desenvolvimento (pode ser substituído por um WSGI em produção)
    app_obj.app.run(host="0.0.0.0", port=5000)
