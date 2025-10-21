"""Application module moved into src package."""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import pandas as pd
import io
import time
import os
from datetime import datetime
from .database import CNPJDatabase
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
        self.app = Flask(__name__)
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
        # Keep routes implementation from original app.py
        pass
