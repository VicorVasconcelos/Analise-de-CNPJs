# 🚀 COMO INICIAR O SISTEMA CNPJ

## Passos Simples para Usar o Sistema

### 1. Abrir Terminal
- Pressione `Win + R`
- Digite `cmd` e pressione Enter
- Navegue para a pasta: `cd "C:\Users\victor.vasconcelos\Documents\Dashboard"`

### 2. Iniciar o Servidor Flask
```bash
python app.py
```

### 3. Aguardar Inicialização
Você verá esta mensagem quando estiver pronto:
```
🚀 INICIANDO SERVIDOR FLASK - SISTEMA CNPJ
============================================================
✅ Servidor configurado com sucesso!
🌐 INICIANDO SERVIDOR NA PORTA 5000...
 * Running on http://127.0.0.1:5000
```

### 4. Abrir a Interface
- Abra o arquivo `index.html` no navegador
- Ou navegue para: `http://localhost:5000` (se configurar rota estática)

## ⚠️ Problemas Comuns

### "ModuleNotFoundError"
Execute no terminal:
```bash
pip install flask flask-cors pandas requests
```

### "Porta 5000 já está em uso"
- Feche outros programas que possam usar a porta 5000
- Ou modifique a porta no arquivo `app.py`

### Interface mostra "Servidor Flask Offline"
- Verifique se o comando `python app.py` está rodando
- Recarregue a página (F5) após iniciar o servidor

## 🎯 Uso do Sistema

1. **Filtros**: Selecione UF, CNAE, município, etc.
2. **Buscar**: Clique no botão "Buscar" para ver resultados
3. **Exportar**: Clique em "Exportar CSV" para baixar dados filtrados

---
**Dica**: Mantenha o terminal aberto com `python app.py` rodando enquanto usa o sistema!