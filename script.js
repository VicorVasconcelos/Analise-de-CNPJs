// Configuração da API
const API_BASE_URL = 'http://localhost:5000';

// Estado da aplicação
let currentPage = 1;
let currentFilters = {};
let totalResults = 0;
let resultsPerPage = 50;

// Elementos DOM
const statusCard = document.getElementById('statusCard');
const statsGrid = document.getElementById('statsGrid');
const filtersForm = document.getElementById('filtersForm');
const resultsSection = document.getElementById('resultsSection');
const resultsTable = document.getElementById('resultsTable');
const resultsBody = document.getElementById('resultsBody');
const resultsCount = document.getElementById('resultsCount');
const pagination = document.getElementById('pagination');
const loadingOverlay = document.getElementById('loadingOverlay');
const searchBtn = document.getElementById('searchBtn');
const exportBtn = document.getElementById('exportBtn');
const clearFiltersBtn = document.getElementById('clearFilters');

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Função principal de inicialização
async function initializeApp() {
    try {
        const apiConnected = await checkAPIStatus();
        
        if (apiConnected) {
            await loadStats();
            await loadFilters();
            setupEventListeners();
        } else {
            // API offline - configurar interface limitada
            setupOfflineInterface();
        }
    } catch (error) {
        console.error('Erro na inicialização:', error);
        setupOfflineInterface();
    }
}

// Configurar interface quando API está offline
function setupOfflineInterface() {
    // Desabilitar formulário de filtros
    const filterInputs = filtersForm.querySelectorAll('input, select, button');
    filterInputs.forEach(input => {
        input.disabled = true;
    });
    
    // Mostrar estatísticas offline
    statsGrid.innerHTML = `
        <div class="stat-card">
            <i class="fas fa-server" style="color: #e74c3c;"></i>
            <div class="stat-value">Offline</div>
            <div class="stat-label">Servidor Flask</div>
        </div>
        <div class="stat-card">
            <i class="fas fa-exclamation-triangle" style="color: #f39c12;"></i>
            <div class="stat-value">Indisponível</div>
            <div class="stat-label">Dados</div>
        </div>
        <div class="stat-card">
            <i class="fas fa-info-circle" style="color: #3498db;"></i>
            <div class="stat-value">python app.py</div>
            <div class="stat-label">Execute no Terminal</div>
        </div>
        <div class="stat-card">
            <i class="fas fa-refresh" style="color: #9b59b6;"></i>
            <div class="stat-value">F5</div>
            <div class="stat-label">Recarregar Página</div>
        </div>
    `;
    
    // Adicionar botão de reconexão
    const reconnectBtn = document.createElement('button');
    reconnectBtn.innerHTML = '<i class="fas fa-refresh"></i> Tentar Reconectar';
    reconnectBtn.className = 'btn btn-primary';
    reconnectBtn.style.margin = '20px auto';
    reconnectBtn.style.display = 'block';
    reconnectBtn.onclick = () => location.reload();
    
    statusCard.appendChild(reconnectBtn);
}

// Verificar status da API
async function checkAPIStatus() {
    try {
        showLoading('Verificando status da API...');
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'healthy') {
            statusCard.innerHTML = `
                <div class="status-card healthy">
                    <i class="fas fa-check-circle" style="color: #27ae60; font-size: 2em;"></i>
                    <h3>Sistema Operacional</h3>
                    <p>API funcionando corretamente</p>
                    <p><strong>${formatNumber(data.total_empresas)}</strong> empresas na base</p>
                </div>
            `;
            return true;
        } else {
            throw new Error('API não está saudável');
        }
    } catch (error) {
        console.error('Erro na verificação da API:', error);
        statusCard.innerHTML = `
            <div class="status-card error">
                <i class="fas fa-exclamation-triangle" style="color: #e74c3c; font-size: 2em;"></i>
                <h3>Servidor Flask Offline</h3>
                <p><strong>Erro:</strong> ${error.message}</p>
                <p><strong>Solução:</strong></p>
                <ol style="text-align: left; margin: 10px 0;">
                    <li>Abra um terminal na pasta do projeto</li>
                    <li>Execute: <code>python app.py</code></li>
                    <li>Aguarde a mensagem "Running on http://127.0.0.1:5000"</li>
                    <li>Recarregue esta página</li>
                </ol>
            </div>
        `;
        return false;
    } finally {
        hideLoading();
    }
}

// Carregar estatísticas
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        statsGrid.innerHTML = `
            <div class="stat-card">
                <i class="fas fa-building"></i>
                <div class="stat-value">${formatNumber(data.tabelas.empresas || 0)}</div>
                <div class="stat-label">Empresas</div>
            </div>
            <div class="stat-card">
                <i class="fas fa-industry"></i>
                <div class="stat-value">${formatNumber(data.tabelas.cnaes || 0)}</div>
                <div class="stat-label">CNAEs Disponíveis</div>
            </div>
            <div class="stat-card">
                <i class="fas fa-map-marker-alt"></i>
                <div class="stat-value">${data.top_ufs && data.top_ufs.length}</div>
                <div class="stat-label">Estados (UFs)</div>
            </div>
            <div class="stat-card">
                <i class="fas fa-chart-pie"></i>
                <div class="stat-value">${data.top_naturezas[0]?.natureza?.slice(0, 15) || 'N/A'}...</div>
                <div class="stat-label">Principal Natureza<br><small>(${formatNumber(data.top_naturezas[0]?.total || 0)} empresas)</small></div>   
            </div>
        `;
    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
        statsGrid.innerHTML = `
            <div class="stat-card">
                <i class="fas fa-exclamation-triangle"></i>
                <div class="stat-value">Erro</div>
                <div class="stat-label">Não foi possível carregar estatísticas</div>
            </div>
        `;
    }
}

// Carregar opções de filtros
async function loadFilters() {
    try {
        const response = await fetch(`${API_BASE_URL}/filters`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Helper to safely read value/label from various backend shapes
        function readValue(o, keys) {
            for (const k of keys) if (o && o[k] !== undefined) return o[k];
            return '';
        }

        // Carregar UFs (suporta {value,label} ou {uf,count})
        const ufSelect = document.getElementById('uf');
        if (ufSelect) {
            ufSelect.innerHTML = '<option value="">Todos os estados</option>';
            const ufsArr = data.ufs || [];
            ufsArr.forEach(uf => {
                const option = document.createElement('option');
                const val = readValue(uf, ['value', 'uf']);
                const label = readValue(uf, ['label', 'uf']);
                option.value = val || label || '';
                option.textContent = label || val || '';
                ufSelect.appendChild(option);
            });
        }
        
        // Carregar CNAEs
        const cnaeSelect = document.getElementById('cnae');
        if (cnaeSelect) {
            cnaeSelect.innerHTML = '<option value="">Todos os CNAEs</option>';
            data.cnaes.forEach(cnae => {
                const option = document.createElement('option');
                option.value = cnae.value;
                option.textContent = cnae.label;
                cnaeSelect.appendChild(option);
            });
        }
        
        // Carregar Naturezas Jurídicas
        // Carregar Naturezas Jurídicas (vários formatos: data.naturezas OR data.naturezas_juridicas)
        const naturezaSelect = document.getElementById('natureza_juridica');
        if (naturezaSelect) {
            naturezaSelect.innerHTML = '<option value="">Todas as naturezas</option>';
            const natArr = data.naturezas || data.naturezas_juridicas || [];
            natArr.forEach(natureza => {
                const option = document.createElement('option');
                // suporte a {value,label} ou {codigo,descricao}
                const val = readValue(natureza, ['value', 'codigo']);
                const label = readValue(natureza, ['label', 'descricao']);
                option.value = val || label || '';
                option.textContent = label || val || '';
                naturezaSelect.appendChild(option);
            });
        }
        
        // Carregar Portes de Empresa
        const porteSelect = document.getElementById('porte');
        if (porteSelect) {
            porteSelect.innerHTML = '<option value="">Todos os portes</option>';
            const porteArr = data.portes || [];
            porteArr.forEach(porte => {
                const option = document.createElement('option');
                const val = readValue(porte, ['value']);
                const label = readValue(porte, ['label']);
                option.value = val || label || '';
                option.textContent = label || val || '';
                porteSelect.appendChild(option);
            });
        }
        
        // Carregar Situações Cadastrais
        const situacaoSelect = document.getElementById('situacao_cadastral');
        if (situacaoSelect) {
            situacaoSelect.innerHTML = '<option value="">Todas as situações</option>';
            const situArr = data.situacoes_cadastrais || [];
            situArr.forEach(situacao => {
                const option = document.createElement('option');
                const val = readValue(situacao, ['value']);
                const label = readValue(situacao, ['label']);
                option.value = val || label || '';
                option.textContent = label || val || '';
                situacaoSelect.appendChild(option);
            });
        }
        
        // Carregar Opções Simples Nacional
        const simplesSelect = document.getElementById('opcao_simples');
        if (simplesSelect) {
            simplesSelect.innerHTML = '<option value="">Todas as opções</option>';
            const simplesArr = data.simples_opcoes || [];
            simplesArr.forEach(opcao => {
                const option = document.createElement('option');
                const val = readValue(opcao, ['value']);
                const label = readValue(opcao, ['label']);
                option.value = val || label || '';
                option.textContent = label || val || '';
                simplesSelect.appendChild(option);
            });
        }
        
    } catch (error) {
        console.error('Erro ao carregar filtros:', error);
        
        // Opções padrão quando API está offline
        const porteSelect = document.getElementById('porte');
        if (porteSelect) porteSelect.innerHTML = '<option value="">Servidor offline - Inicie o Flask</option>';
        
        const simplesSelect = document.getElementById('opcao_simples');
        if (simplesSelect) simplesSelect.innerHTML = '<option value="">Servidor offline - Inicie o Flask</option>';
    }
}

// Configurar event listeners
function setupEventListeners() {
    filtersForm.addEventListener('submit', handleSearch);
    clearFiltersBtn.addEventListener('click', clearFilters);
    exportBtn.addEventListener('click', handleExport);
}

// Manipular busca
async function handleSearch(event) {
    event.preventDefault();
    
    try {
        showLoading('Buscando resultados...');
        
        // Coletar filtros do formulário
        const formData = new FormData(filtersForm);
        currentFilters = {};
        

        
        // Razão Social
        if (formData.get('razao_social')) {
            currentFilters.razao_social = formData.get('razao_social');
        }
        
        // UF
        if (formData.get('uf')) {
            currentFilters.uf = formData.get('uf');
        }
        
        // CNAE
        if (formData.get('cnae')) {
            currentFilters.cnae = formData.get('cnae');
        }
        
        // Natureza Jurídica
        if (formData.get('natureza_juridica')) {
            currentFilters.natureza_juridica = formData.get('natureza_juridica');
        }
        
        // Porte da Empresa
        if (formData.get('porte')) {
            currentFilters.porte = formData.get('porte');
        }
        
        // Situação Cadastral
        if (formData.get('situacao_cadastral')) {
            currentFilters.situacao_cadastral = formData.get('situacao_cadastral');
        }
        
        // Opção Simples Nacional
        if (formData.get('opcao_simples')) {
            currentFilters.opcao_simples = formData.get('opcao_simples');
        }
        

        
        // Resetar página
        currentPage = 1;
        
        // Fazer busca
        await performSearch();
        
    } catch (error) {
        console.error('Erro na busca:', error);
        showError('Erro ao realizar busca');
    } finally {
        hideLoading();
    }
}

// Realizar busca na API
async function performSearch() {
    try {
        const queryParams = {
            ...currentFilters,
            page: currentPage,
            per_page: resultsPerPage
        };
        
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(queryParams)
        });
        
        if (!response.ok) {
            throw new Error(`Erro na API: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Atualizar estado - usar formato correto da API
        totalResults = data.pagination ? data.pagination.total : data.total;
        
        // Exibir resultados
        displayResults(data.data);
        updatePagination();
        showResultsSection();
        
    } catch (error) {
        console.error('Erro na busca:', error);
        showError('Erro ao buscar dados');
    }
}

// Exibir resultados na tabela
function displayResults(results) {
    if (!results || results.length === 0) {
        resultsBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px; color: #7f8c8d;">
                    <i class="fas fa-search" style="font-size: 2em; margin-bottom: 10px;"></i><br>
                    Nenhum resultado encontrado com os filtros aplicados.
                </td>
            </tr>
        `;
        resultsCount.textContent = 'Nenhum resultado';
        return;
    }
    
    resultsBody.innerHTML = results.map(row => `
        <tr>
            <td>${row.cnpj_formatado || '-'}</td>
            <td>${row.razao_social || '-'}</td>
            <td>${row.nome_fantasia || '-'}</td>
            <td>${row.situacao || '-'}</td>
            <td>${row.uf || '-'}</td>
            <td>${row.municipio || '-'}</td>
            <td>${row.porte || '-'}</td>
            <td>${row.natureza_juridica || '-'}</td>
        </tr>
    `).join('');
    
    const startResult = (currentPage - 1) * resultsPerPage + 1;
    const endResult = Math.min(currentPage * resultsPerPage, totalResults);
    resultsCount.textContent = `${formatNumber(startResult)}-${formatNumber(endResult)} de ${formatNumber(totalResults)} resultados`;
}

// Atualizar paginação
function updatePagination() {
    const totalPages = Math.ceil(totalResults / resultsPerPage);
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // Botão anterior
    paginationHTML += `
        <button onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
            <i class="fas fa-chevron-left"></i> Anterior
        </button>
    `;
    
    // Páginas
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHTML += `<button onclick="goToPage(1)">1</button>`;
        if (startPage > 2) {
            paginationHTML += `<span>...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button onclick="goToPage(${i})" ${i === currentPage ? 'class="active"' : ''}>
                ${i}
            </button>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span>...</span>`;
        }
        paginationHTML += `<button onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }
    
    // Botão próximo
    paginationHTML += `
        <button onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
            Próximo <i class="fas fa-chevron-right"></i>
        </button>
    `;
    
    pagination.innerHTML = paginationHTML;
}

// Ir para página específica
async function goToPage(page) {
    if (page < 1 || page > Math.ceil(totalResults / resultsPerPage) || page === currentPage) {
        return;
    }
    
    currentPage = page;
    showLoading('Carregando página...');
    
    try {
        await performSearch();
    } finally {
        hideLoading();
    }
}

// Manipular exportação
async function handleExport() {
    try {
        showLoading('Gerando arquivo CSV...');
        
        const response = await fetch(`${API_BASE_URL}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(currentFilters)
        });
        
        if (!response.ok) {
            throw new Error(`Erro na exportação: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success && data.filename) {
            // Download do arquivo
            const downloadUrl = `${API_BASE_URL}/download/${data.filename}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = data.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showSuccess(`Arquivo ${data.filename} exportado com sucesso! (${formatNumber(data.total_records)} registros)`);
        } else {
            throw new Error('Erro ao gerar arquivo de exportação');
        }
        
    } catch (error) {
        console.error('Erro na exportação:', error);
        showError('Erro ao exportar dados');
    } finally {
        hideLoading();
    }
}

// Limpar filtros
function clearFilters() {
    filtersForm.reset();
    document.getElementById('uf').selectedIndex = -1;
    document.getElementById('cnae').selectedIndex = -1;
    document.getElementById('situacao_cadastral').selectedIndex = -1;
    currentFilters = {};
    hideResultsSection();
}

// Exibir seção de resultados
function showResultsSection() {
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Ocultar seção de resultados
function hideResultsSection() {
    resultsSection.style.display = 'none';
}

// Utilitários de UI
function showLoading(message = 'Carregando...') {
    loadingOverlay.querySelector('p').textContent = message;
    loadingOverlay.style.display = 'flex';
    searchBtn.disabled = true;
    exportBtn.disabled = true;
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
    searchBtn.disabled = false;
    exportBtn.disabled = false;
}

function showError(message) {
    // Implementação simples de notificação de erro
    alert('Erro: ' + message);
}

function showSuccess(message) {
    // Implementação simples de notificação de sucesso
    alert('Sucesso: ' + message);
}

// Utilitários de formatação
function formatNumber(num) {
    return new Intl.NumberFormat('pt-BR').format(num);
}

function formatCNPJ(cnpj) {
    if (!cnpj || cnpj.length !== 14) return cnpj;
    return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
}

function getSituacaoText(codigo) {
    const situacoes = {
        '01': 'Nula',
        '02': 'Ativa',
        '03': 'Suspensa',
        '04': 'Inapta',
        '08': 'Baixada'
    };
    return situacoes[codigo] || codigo || '-';
}

function getPorteText(codigo) {
    const portes = {
        '00': 'Não informado',
        '01': 'Micro empresa',
        '03': 'Empresa de pequeno porte',
        '05': 'Demais'
    };
    return portes[codigo] || codigo || '-';
}

// Exposer função goToPage globalmente para uso nos botões de paginação
window.goToPage = goToPage;