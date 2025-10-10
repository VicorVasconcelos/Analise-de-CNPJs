CREATE INDEX IF NOT EXISTS idx_est_cnpj_basico ON estabelecimentos_completos(cnpj_basico);
CREATE INDEX IF NOT EXISTS idx_emp_cnpj_basico ON empresas_completas(cnpj_basico);
CREATE INDEX IF NOT EXISTS idx_est_uf ON estabelecimentos_completos(uf);
CREATE INDEX IF NOT EXISTS idx_est_cnae ON estabelecimentos_completos(cnae_fiscal_principal);
CREATE INDEX IF NOT EXISTS idx_est_municipio ON estabelecimentos_completos(municipio);
CREATE INDEX IF NOT EXISTS idx_emp_porte ON empresas_completas(porte);
CREATE INDEX IF NOT EXISTS idx_simples_cnpj ON simples(cnpj_basico);
CREATE INDEX IF NOT EXISTS idx_emp_natureza ON empresas_completas(natureza_juridica);
