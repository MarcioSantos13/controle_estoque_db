#!/usr/bin/env python3
"""
CORRETOR AUTOMÁTICO DA ESTRUTURA DO BANCO DE DADOS
Autor: Sistema CEAD
Descrição: Corrige problemas na estrutura do banco de dados para importação
"""

import sqlite3
import os
import sys
from datetime import datetime
import shutil

class CorretorEstruturaBanco:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.problemas_encontrados = []
        self.correcoes_aplicadas = []
        
    def conectar(self):
        """Conecta ao banco de dados"""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Banco de dados não encontrado: {self.db_path}")
                return False
                
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"✅ Conectado ao banco: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def desconectar(self):
        """Desconecta do banco de dados"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            print("✅ Conexão fechada")
    
    def criar_backup(self):
        """Cria backup do banco antes das correções"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.replace('.db', f'_backup_{timestamp}.db')
            shutil.copy2(self.db_path, backup_path)
            print(f"📦 Backup criado: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ Erro ao criar backup: {e}")
            return None
    
    def diagnosticar_problemas(self):
        """Diagnostica problemas na estrutura do banco"""
        print("\n🔍 DIAGNOSTICANDO PROBLEMAS...")
        print("=" * 60)
        
        problemas = []
        
        # 1. Verificar se campos NOT NULL estão impedindo importação
        cursor = self.conn.cursor()
        
        # Obter estrutura da tabela bens
        cursor.execute("PRAGMA table_info(bens)")
        colunas_bens = cursor.fetchall()
        
        print("📋 ESTRUTURA ATUAL DA TABELA BENS:")
        for coluna in colunas_bens:
            print(f"   • {coluna[1]} ({coluna[2]}) - NULL: {not coluna[3]} - PK: {coluna[5]}")
            
            # Identificar problemas de campos NOT NULL desnecessários
            if coluna[3] == 0 and coluna[1] not in ['id', 'numero', 'nome']:  # NOT NULL
                problemas.append({
                    'tipo': 'NOT NULL desnecessário',
                    'coluna': coluna[1],
                    'descricao': f'Coluna {coluna[1]} está como NOT NULL mas deve aceitar valores nulos para importação'
                })
        
        # 2. Verificar dados existentes para ver se há problemas
        try:
            cursor.execute("SELECT COUNT(*) FROM bens WHERE localizacao = '' OR localizacao IS NULL")
            sem_localizacao = cursor.fetchone()[0]
            if sem_localizacao > 0:
                problemas.append({
                    'tipo': 'Dados inconsistentes',
                    'coluna': 'localizacao',
                    'descricao': f'{sem_localizacao} registros sem localização (campo NOT NULL)'
                })
        except Exception as e:
            problemas.append({
                'tipo': 'Erro na consulta',
                'coluna': 'localizacao',
                'descricao': f'Erro ao verificar localização: {e}'
            })
        
        # 3. Verificar se há registros com problemas de constraint
        try:
            cursor.execute("SELECT COUNT(*) FROM bens WHERE numero IS NULL OR numero = ''")
            sem_numero = cursor.fetchone()[0]
            if sem_numero > 0:
                problemas.append({
                    'tipo': 'Dados inválidos',
                    'coluna': 'numero',
                    'descricao': f'{sem_numero} registros sem número (campo obrigatório)'
                })
        except Exception as e:
            pass
        
        self.problemas_encontrados = problemas
        return problemas
    
    def corrigir_estrutura_bens(self):
        """Corrige a estrutura da tabela bens para permitir importação"""
        print("\n🔧 APLICANDO CORREÇÕES NA TABELA BENS...")
        print("=" * 60)
        
        correcoes = []
        cursor = self.conn.cursor()
        
        try:
            # CORREÇÃO 1: Criar tabela temporária com estrutura correta
            print("📝 Criando tabela temporária com estrutura corrigida...")
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bens_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    situacao TEXT DEFAULT 'Pendente',
                    localizacao TEXT,
                    responsavel TEXT,
                    data_ultima_vistoria DATE,
                    data_vistoria_atual DATE,
                    auditor TEXT,
                    observacoes TEXT,
                    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_localizacao DATETIME
                )
            ''')
            correcoes.append("Tabela temporária criada")
            
            # CORREÇÃO 2: Copiar dados da tabela antiga para a nova
            print("🔄 Copiando dados para a nova estrutura...")
            
            # Inserir dados existentes (tratando campos NOT NULL problemáticos)
            cursor.execute('''
                INSERT OR REPLACE INTO bens_temp 
                (id, numero, nome, situacao, localizacao, responsavel, 
                 data_ultima_vistoria, data_vistoria_atual, auditor, observacoes,
                 data_criacao, data_localizacao)
                SELECT 
                    id,
                    COALESCE(numero, 'TEMPORARY_' || id),
                    COALESCE(nome, 'Não informado'),
                    COALESCE(situacao, 'Pendente'),
                    NULLIF(localizacao, ''),
                    NULLIF(responsavel, ''),
                    NULLIF(data_ultima_vistoria, ''),
                    NULLIF(data_vistoria_atual, ''),
                    NULLIF(auditor, ''),
                    NULLIF(observacoes, ''),
                    COALESCE(data_criacao, CURRENT_TIMESTAMP),
                    data_localizacao
                FROM bens
            ''')
            
            registros_copiados = cursor.rowcount
            correcoes.append(f"{registros_copiados} registros copiados para nova estrutura")
            
            # CORREÇÃO 3: Renomear tabelas (swap)
            print("🔄 Realizando substituição das tabelas...")
            
            cursor.execute("DROP TABLE IF EXISTS bens_old")
            cursor.execute("ALTER TABLE bens RENAME TO bens_old")
            cursor.execute("ALTER TABLE bens_temp RENAME TO bens")
            
            correcoes.append("Tabelas renomeadas (bens_old ← bens ← bens_temp)")
            
            # CORREÇÃO 4: Recriar índices
            print("📑 Recriando índices...")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
            
            correcoes.append("Índices recriados")
            
            # CORREÇÃO 5: Atualizar sqlite_sequence
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'bens'")
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('bens', (SELECT MAX(id) FROM bens))")
            
            correcoes.append("Sequência atualizada")
            
            self.conn.commit()
            self.correcoes_aplicadas = correcoes
            return True
            
        except Exception as e:
            print(f"❌ Erro durante a correção: {e}")
            self.conn.rollback()
            return False
    
    def verificar_corrigir_usuarios(self):
        """Corrige problemas na tabela usuarios"""
        print("\n👥 VERIFICANDO TABELA USUARIOS...")
        
        try:
            cursor = self.conn.cursor()
            
            # Verificar se campos NOT NULL estão causando problemas
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas_usuarios = cursor.fetchall()
            
            problemas_usuarios = []
            for coluna in colunas_usuarios:
                if coluna[3] == 0 and coluna[1] in ['departamento', 'telefone', 'criado_por', 'data_atualizacao']:
                    problemas_usuarios.append(coluna[1])
            
            if problemas_usuarios:
                print(f"⚠️  Campos NOT NULL problemáticos em usuarios: {problemas_usuarios}")
                
                # Corrigir dados existentes
                cursor.execute('''
                    UPDATE usuarios SET 
                        departamento = COALESCE(NULLIF(departamento, ''), 'Não informado'),
                        telefone = COALESCE(NULLIF(telefone, ''), 'Não informado'),
                        criado_por = COALESCE(criado_por, 1),
                        data_atualizacao = COALESCE(data_atualizacao, CURRENT_TIMESTAMP)
                    WHERE departamento = '' OR telefone = '' OR criado_por IS NULL OR data_atualizacao IS NULL
                ''')
                
                registros_corrigidos = cursor.rowcount
                if registros_corrigidos > 0:
                    print(f"✅ {registros_corrigidos} registros de usuários corrigidos")
                    
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Erro ao corrigir tabela usuarios: {e}")
            return False
    
    def testar_importacao(self, arquivo_teste=None):
        """Testa se a importação funciona após correções"""
        print("\n🧪 TESTANDO IMPORTAÇÃO APÓS CORREÇÕES...")
        print("=" * 60)
        
        try:
            # Simular estrutura de dados para teste
            dados_teste = [
                {
                    'numero': 'TESTE_001',
                    'nome': 'Equipamento de Teste 1',
                    'situacao': 'OK',
                    'localizacao': 'Sala de Teste',
                    'responsavel': 'Tester',
                    'data_ultima_vistoria': '2024-10-01',
                    'data_vistoria_atual': '2024-10-29',
                    'auditor': 'Auditor Teste'
                },
                {
                    'numero': 'TESTE_002', 
                    'nome': 'Equipamento de Teste 2',
                    'situacao': 'Pendente',
                    'localizacao': None,  # Testando campo NULL
                    'responsavel': '',    # Testando campo vazio
                    'data_ultima_vistoria': None,
                    'data_vistoria_atual': None,
                    'auditor': None
                }
            ]
            
            cursor = self.conn.cursor()
            sucessos = 0
            erros = 0
            
            for dado in dados_teste:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO bens 
                        (numero, nome, situacao, localizacao, responsavel,
                         data_ultima_vistoria, data_vistoria_atual, auditor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        dado['numero'],
                        dado['nome'],
                        dado['situacao'],
                        dado['localizacao'],
                        dado['responsavel'],
                        dado['data_ultima_vistoria'],
                        dado['data_vistoria_atual'],
                        dado['auditor']
                    ))
                    sucessos += 1
                    print(f"✅ Teste {dado['numero']}: INSERIDO COM SUCESSO")
                    
                except Exception as e:
                    erros += 1
                    print(f"❌ Teste {dado['numero']}: FALHA - {e}")
            
            self.conn.commit()
            
            print(f"\n📊 RESULTADO DO TESTE:")
            print(f"   ✅ Sucessos: {sucessos}")
            print(f"   ❌ Erros: {erros}")
            
            return erros == 0
            
        except Exception as e:
            print(f"❌ Erro no teste de importação: {e}")
            return False
    
    def gerar_relatorio_final(self):
        """Gera relatório final das correções"""
        print("\n" + "=" * 80)
        print("📋 RELATÓRIO FINAL DAS CORREÇÕES APLICADAS")
        print("=" * 80)
        
        print(f"📁 Banco: {self.db_path}")
        print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        if self.problemas_encontrados:
            print(f"\n🔍 PROBLEMAS IDENTIFICADOS ({len(self.problemas_encontrados)}):")
            for problema in self.problemas_encontrados:
                print(f"   • {problema['tipo']} - {problema['coluna']}: {problema['descricao']}")
        
        if self.correcoes_aplicadas:
            print(f"\n🔧 CORREÇÕES APLICADAS ({len(self.correcoes_aplicadas)}):")
            for correcao in self.correcoes_aplicadas:
                print(f"   ✅ {correcao}")
        
        # Verificar estrutura final
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(bens)")
        colunas_finais = cursor.fetchall()
        
        print(f"\n🏗️  ESTRUTURA FINAL DA TABELA BENS:")
        for coluna in colunas_finais:
            null_status = "NOT NULL" if not coluna[3] else "NULL"
            pk_status = " 🔑" if coluna[5] == 1 else ""
            print(f"   • {coluna[1]} ({coluna[2]}) - {null_status}{pk_status}")
        
        print("\n🎯 STATUS: CORREÇÕES CONCLUÍDAS COM SUCESSO!")
        print("=" * 80)

def main():
    """Função principal do corretor"""
    print("🛠️  CORRETOR AUTOMÁTICO DE ESTRUTURA DO BANCO DE DADOS")
    print("=" * 60)
    
    # Configurar caminho do banco
    db_path = "relatorios/controle_patrimonial.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    # Criar corretor
    corretor = CorretorEstruturaBanco(db_path)
    
    # Conectar
    if not corretor.conectar():
        return
    
    try:
        # Criar backup antes de qualquer alteração
        backup_path = corretor.criar_backup()
        if not backup_path:
            confirmar = input("⚠️  Não foi possível criar backup. Continuar mesmo assim? (s/N): ")
            if confirmar.lower() != 's':
                return
        
        # Diagnosticar problemas
        problemas = corretor.diagnosticar_problemas()
        
        if not problemas:
            print("✅ Nenhum problema crítico encontrado!")
            return
        
        print(f"\n⚠️  ENCONTRADOS {len(problemas)} PROBLEMAS:")
        for i, problema in enumerate(problemas, 1):
            print(f"   {i}. {problema['tipo']}: {problema['descricao']}")
        
        # Confirmar correções
        print(f"\n🔧 O corretor aplicará as seguintes correções automáticas:")
        print("   1. Ajustar campos NOT NULL desnecessários")
        print("   2. Migrar dados para nova estrutura")
        print("   3. Manter todos os registros existentes")
        print("   4. Preservar índices e relações")
        
        confirmar = input("\n🎯 Deseja aplicar as correções? (s/N): ").strip().lower()
        if confirmar != 's':
            print("❌ Correções canceladas pelo usuário")
            return
        
        # Aplicar correções
        print("\n" + "🚀 INICIANDO CORREÇÕES..." + "=" * 50)
        
        sucesso_bens = corretor.corrigir_estrutura_bens()
        sucesso_usuarios = corretor.verificar_corrigir_usuarios()
        
        if sucesso_bens:
            # Testar importação
            teste_ok = corretor.testar_importacao()
            
            if teste_ok:
                print("\n🎉 TODAS AS CORREÇÕES FORAM APLICADAS COM SUCESSO!")
                corretor.gerar_relatorio_final()
                
                print(f"\n📦 Backup original salvo em: {backup_path}")
                print("💡 Agora tente importar seu arquivo Excel/CSV novamente!")
            else:
                print("❌ O teste de importação falhou após as correções")
        else:
            print("❌ Falha ao aplicar correções na tabela bens")
            
    except Exception as e:
        print(f"💥 Erro durante o processo: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        corretor.desconectar()

if __name__ == "__main__":
    main()