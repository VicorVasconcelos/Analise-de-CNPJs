// Frontend helper script (vanilla JS)
document.addEventListener('DOMContentLoaded', function () {
	const statusEl = document.getElementById('health-status');
	const btn = document.getElementById('check-health');

	async function checkHealth() {
		statusEl.textContent = 'Verificando...';
		try {
			const res = await fetch('/health');
			if (!res.ok) throw new Error('Resposta não OK: ' + res.status);
			const data = await res.json();
			statusEl.textContent = `Status: ${data.status} — DB: ${data.db_path}`;
		} catch (err) {
			statusEl.textContent = 'Erro ao checar saúde: ' + err.message;
		}
	}

	if (btn) btn.addEventListener('click', checkHealth);
	// check once on load
	checkHealth();
});
