import sqlite3, time
DB='data/cnpj_database.db'
conn=sqlite3.connect(DB)
cur=conn.cursor()
print('DB:',DB)
# fast-path count
q1='SELECT COUNT(*) FROM estabelecimentos_completos'
print('\nRunning q1 (fast-path count):', q1)
start=time.time(); cur.execute(q1); print('count=',cur.fetchone()[0], 'time=%.3fs' % (time.time()-start))
# join-path count
q2='''SELECT COUNT(*) FROM estabelecimentos_completos est LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico'''
print('\nRunning q2 (join-path count):')
start=time.time(); cur.execute(q2); print('count=',cur.fetchone()[0], 'time=%.3fs' % (time.time()-start))
# fast-path data select
q3='''SELECT SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj_formatado FROM estabelecimentos_completos est LIMIT 50 OFFSET 0'''
print('\nRunning q3 (fast-path data select LIMIT 50):')
start=time.time(); cur.execute(q3); rows=cur.fetchall(); print('rows=',len(rows),'time=%.3fs' % (time.time()-start))
# join-path data select
q4='''SELECT SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 1, 2) || '.' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 3, 3) || '.' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 6, 3) || '/' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 9, 4) || '-' || SUBSTR(est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv, 13, 2) as cnpj_formatado FROM estabelecimentos_completos est LEFT JOIN empresas_completas e ON est.cnpj_basico = e.cnpj_basico LEFT JOIN simples s ON est.cnpj_basico = s.cnpj_basico LIMIT 50 OFFSET 0'''
print('\nRunning q4 (join-path data select LIMIT 50):')
start=time.time(); cur.execute(q4); rows=cur.fetchall(); print('rows=',len(rows),'time=%.3fs' % (time.time()-start))
conn.close()
